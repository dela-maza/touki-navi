# touki-navi refactor notes

## Current Focus

Reference resolution around `Article`, `Sentence`, `Reference`, `Token`, `ArticleIndex`, and `ArticleElementIndex` has been partially redesigned.

This memo is a compressed checkpoint so we can safely move to Toc work and return here later.

## Latest Reference Rules From Examples

This section supersedes older reference-resolution notes below when they conflict.

### Current Shape

- `{...}` is for legal reference location marks.
- `<...>` is reserved for meaningful non-location marks, such as qualifiers (`ただし書`, `本文`) or future definition hints. These must not become `Token`.
- HTML output must never leave raw `<...>` marks unprocessed, because they can break HTML.
- `Token` is intentionally minimal:

```python
locator_key: str
locator_value: str
```

- `Reference` is intentionally a light wrapper around one `{...}` mark and one `TokenGroup`.
- `SentenceReferenceGroup` is the intended manager for all `Reference` objects in one `Sentence`.
- A single `Reference` alone cannot know how `this_loc`, `last_ref`, or active reference chains should move.

### State Concepts

- `this_loc` is the immutable location of the current Sentence.
- `last_ref_vector` means the last confirmed reference vector. It can be used by `同条`, `同項`, `同号`, `同法`, even across distance or parentheses.
- `active_ref_vector` means the reference chain that may be implicitly continued by short connectors such as `、`, `及び`, `並びに`, `又は`, `若しくは`.
- `active_ref_vector` should be cut when real text appears between references, not merely connector words.
- A Reference must not shift both `this_loc` and `last_ref` in parallel. One base context must be selected for that Reference, or the result must be marked unresolved/ambiguous at the group level.

### Strong Rules Observed

- `同` is a strong signal to reuse `last_ref_vector`.
  - Example: `第三十三条第十項第一号又は第二号...（同号に掲げる場合...）`
  - `同号` can cross parentheses and distance to refer back to the last confirmed `第二号`.
- `前` / `次` without `同` tends to use `this_loc`.
  - Example: `第四十四条第二項` text with `前項の規定にかかわらず...`
  - `前項` is the previous paragraph of the current Article, not the previous paragraph of a distant referenced Article.
- Plain numeric cells without `l` or `a`, such as `第二項` or `第四項`, should be treated as `this_loc` unless an active reference chain is clearly alive.
  - Example: `第四項において同じ` points to the current Article's fourth paragraph, not a distant referenced Article.
- Short connector-only gaps can keep `active_ref_vector` alive.
  - Example: `第三条第一項並びに第二項` means `第三条第一項` and `第三条第二項`.
  - Example: `民法第四百二十四条第一項ただし書、第四百二十四条の五、第四百二十四条の七第二項及び第四百二十五条` keeps the `民法` reference chain alive across `、` and `及び`.
- Connector/range words can keep `active_ref_vector` alive for later plain numeric cells.
  - Example: `第八百七十条第一項第一号から第四号まで及び第八号`
  - `第四号` inherits `第八百七十条第一項` through `から`.
  - `第八号` inherits `第八百七十条第一項` through `まで及び`.
- `同` can revive `last_ref_vector`, and following connector-only cells can then continue the revived active chain.
  - Example: `第八百七十条第一項各号...（同項第一号、第三号及び第四号...）`
  - `同項第一号` revives `第八百七十条第一項`.
  - `第三号` and `第四号` continue that revived reference chain through `、` and `及び`.
- If real text appears between references, implicit inheritance should usually stop. The law often adds `同条`, `同項`, or `同号` when it wants to revive a previous reference.
  - Example: `第二十八条第一号の財産を給付した者又は同条第二号...`
  - Because real noun-phrase text appears between the references, the statute uses `同条`.
- `第二号において同じ` has no `同号`, so it is treated as current Article/current context (`this_loc`) rather than distant `last_ref`.

### Validation Policy

- These rules must be validated against many real examples before being treated as stable.
- Target at least 100 legal-text examples covering:
  - short connector chains
  - long noun-phrase gaps
  - parentheses
  - `同条` / `同項` / `同号`
  - `前項` / `次項`
  - `から` / `まで`
  - `各号`
  - qualifiers such as `ただし書` and `本文`
- If a rule breaks on real text, prefer refining `SentenceReferenceGroup` rules over adding responsibility back into `Token` or `Reference`.

### Range Rules

- `RangeToken` / shift-range-like values must end the `TokenGroup`.
- A once-expanded coordinate should not be moved again.
- `前三項第一号` looks possible at a glance, but it would mean a dispersed set of paragraphs and then the first item of each. That is not reader-trackable legal reference structure.
- `前三項各号` is "spread of spread"; warn at `TokenGroup`, and treat as invalid at vector resolution.
- Shift range must not be eagerly expanded into simple numbers like `4,5,6`, because paragraphs/items can have branch numbers. Keep an instruction form such as `7:-3*` until an index-aware layer resolves it.

### Qualifiers And Semantic Marks

- `ただし書`, `本文`, `前段`, `後段` are meaningful, but they are not location vector cells.
- They should not become `Token`.
- They may be marked with `<...>` and stripped before location analysis.
- Future definition hints can also use `<...>`, for example marking legal definitions for HTML tooltips.
- A standalone law name, such as `会社法の規定`, should ultimately become a semantic hint, not an Article reference link.
- Do not decide this in `chunker`. `chunker` should still mark law names as `{...}` first, so `会社法第一条` can be joined into one reference mark.
- A higher layer, probably `SentenceReferenceGroup`, should detect an `l`-only `TokenGroup`:

```text
[l=kai]
```

  and downgrade it to a semantic law mark such as:

```text
<law=kai>
```

- Law semantic marks should be used for hints, such as law name, law number, or enforcement date. They should not link to Article 1 or any arbitrary article.
- `次の各号` currently may resolve by accident as `this_sentence_location + [i=*]`, because `各号` becomes a range token.
- Do not rely on that accident long-term. Consider marking the semantic prefix separately, such as `<scope=次の>{[各号]|[各号]|[i=*]}`.
- Example: `次の各号に掲げる場合の区分に応じ、当該各号に定める地...`
- This rule is not fixed yet; it is a candidate for future `SentenceReferenceGroup` or semantic-mark handling.

## Project Rules

- Do not change code unless explicitly requested.
- Preserve handwritten comments as much as possible.
- New modules should start with a path comment.
- Official Japanese legal XML `Sentence` text should be treated as full-width text. Half-width characters are system-added marks or metadata.

## Reference Mark Format

Reference marks use five fields:

```text
{ raw | arabic | locator | this_loc | last_ref_loc }
```

Current policy:

- `raw`: original legal-text unit, usually kanji numerals.
- `arabic`: full-width Arabic numeral display form where needed.
- `locator`: machine-readable locator.
- `this_loc` / `last_ref_loc`: reserved location fields.

Locator kinds:

- `absloc`: absolute locator, such as law or article.
- `partloc`: lower-level location part relative to a base location.
- `shift`: single-location movement from a base location.
- `range`: multiple-location expansion from a base location.

`each` is represented as `range:i=each` in marks and converted to `RangeToken.EACH = 0` inside `RangeToken`.

## Token Layer

`TokenBase` has four concrete token types:

- `AbsoluteToken`
- `PartLocToken`
- `ShiftToken`
- `RangeToken`

`TokenGroup` currently keeps only a list of tokens and validates suspicious token order, especially `each` not appearing at the end.

`TokenGroup` should not decide final locations by itself.

## Resolver Layer

`ReferenceResolver` reads `Sentence.marked_text`, extracts `{...}`, builds `TokenGroup`, and produces `Reference` objects.

`ReferenceLocationResolver` dispatches tokens to:

- direct token application for `AbsoluteToken` and `PartLocToken`
- `ShiftLocationResolver`
- `RangeLocationResolver`

The resolver returns candidate `FullLocation` lists.

`last_ref_location` is scoped to a single `Sentence`. It should not carry across sentences.

## Sentence / Reference

`Sentence` currently has:

```python
num: str
text: str
marked_text: str = ""
references: list[Reference] = field(default_factory=list)
```

`Reference` currently has:

```python
raw_mark: str
token_group: TokenGroup
this_locations: list[FullLocation]
last_ref_locations: list[FullLocation]
```

No status field for same-law / other-law is currently used. DB-level link validation will decide later.

## ArticleXml / ArticleIndex / ArticleBuilder

`ArticleXMLParser` was changed into the instance class `ArticleXml`.

`ArticleXml(law_type)` holds:

```python
element_locations_by_article: dict[str, list[FullLocation]]
```

The dict key is `article.num`.

While parsing XML, `ArticleXml` appends `Paragraph`, `Item`, `Subitem1`, and `Subitem2` locations into `_current_element_locations`, then stores the list under `element_locations_by_article[article.num]`.

`ArticleIndex.from_articles()` now accepts both:

```python
articles
element_locations_by_article
```

`ArticleElementIndex.from_article()` was removed from the intended flow.

`ArticleElementIndex.from_locations(article_location, locations)` builds the per-Article internal location index from already collected locations. This avoids recursively walking the Article tree a second time.

`ArticleBuilder` flow:

```text
ArticleIndex.articles を iterate
Articleごとに ArticleElementIndex.from_locations() を作る
ReferenceResolver を作る
Article内の Sentence を owner_location 付きで走査
Sentence.references を埋める
完成した list[Article] を返す
```

`ArticleElementIndex` is disposable per Article.

## Known Unfinished Points

- `ArticleElementIndex` is mechanically correct but visually tiring. It may still be simplified.
- `ReferenceResolver` and location resolver modules are still in active design.
- Real XML parse execution was not verified in this environment because `bs4` is missing from available Python runtimes.
- DB persistence and final link validation are not implemented.
