# reference/resolver/token.py

import re
from app.article.common.law_utils import kanji_to_id
from app.article.models.article_loc import ArticleDepth, FullLocation

class Token:
    def __init__(self, tag: str, val: str, label: str):
        self.tag = tag
        self.val = val
        self.label = label

    @classmethod
    def parse(cls, raw_content: str) -> "Token":
        if raw_content == "前条":
            return cls(tag="a", val="-1", label=raw_content)
        if raw_content == "同条":
            return cls(tag="a", val="0", label=raw_content)
        if raw_content == "前項":
            return cls(tag="p", val="-1", label=raw_content)
        if raw_content == "同項":
            return cls(tag="p", val="0", label=raw_content)
        if raw_content == "前号":
            return cls(tag="i", val="-1", label=raw_content)
        if raw_content == "同号":
            return cls(tag="i", val="0", label=raw_content)

        if "条" in raw_content:
            return cls(tag="a", val=kanji_to_id(raw_content), label=raw_content)

        from app.article.constants.enums import ArticleDepth
        for depth in ArticleDepth:
            if depth.label_jp in raw_content:
                return cls(tag=depth.short_name, val=kanji_to_id(raw_content), label=raw_content)

        if raw_content.startswith("の"):
            return cls(tag="a", val=kanji_to_id(raw_content), label=raw_content)

        if re.fullmatch(r"[イロハニホヘトチリヌルヲ]+", raw_content):
            return cls(tag="s1", val=raw_content, label=raw_content)

        if re.fullmatch(r"（[０-９]+）", raw_content):
            table = str.maketrans("０１２３４５６７８９", "0123456789", "（）")
            val = raw_content.translate(table)
            return cls(tag="s2", val=val, label=raw_content)

        return cls(tag="unknown", val="0", label=raw_content)

    def get_article_depth(self) -> ArticleDepth:
        mapping = {"p": ArticleDepth.PARAGRAPH, "i": ArticleDepth.ITEM,
                   "s1": ArticleDepth.SUB_ITEM_1, "s2": ArticleDepth.SUB_ITEM_2}
        return mapping.get(self.tag, ArticleDepth.PARAGRAPH)

class TokenGroup:
    def __init__(self, raw_segment: str, current_location: FullLocation):
        clean_segment = raw_segment.replace("[[", "").replace("]]", "")
        self.raw_contents: list[str] = clean_segment.split("][")
        self.tokens: list[Token] = [Token.parse(c) for c in self.raw_contents]
        self.final_location: FullLocation = self._calculate_location(current_location)

    def _calculate_location(self, base_loc: FullLocation) -> FullLocation:
        loc = base_loc
        for token in self.tokens:
            # 簡略化：LocationShiftResolverを使わず直接判定
            if token.tag == "a":
                loc = loc.update_article(token.val)
            elif token.tag in ("p", "i", "s1", "s2"):
                depth = token.get_article_depth()
                val = int(token.val) if token.val.isdigit() else token.val
                loc = loc.update_relative(depth, val)
        return loc

    def to_resolved_string(self) -> str:
        original_text = "".join([t.label for t in self.tokens])
        final_id = self.final_location.id_attr
        return (
            f'<span class="resolved-link-debug" style="border: 1px solid #f39c12; padding: 0 4px; border-radius: 4px; background: #fffdf0;">'
            f'{original_text}'
            f'<span style="color: #e67e22; font-family: monospace; font-weight: bold; margin-left: 8px;">'
            f'[{final_id}]'
            f'</span>'
            f'</span>'
        )