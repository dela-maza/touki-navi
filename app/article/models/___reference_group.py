# app/article/models/reference_group.py
import re
from dataclasses import dataclass, field

from app.article.constants.inline_marks import CONNECTOR_TEXTS, HINT_KEY_LAW, INLINE_MARK_HINT
from app.article.models.article_loc import AbsoluteArticleLocation
from app.article.models.reference import Reference
from app.article.models.sentence import Sentence
from app.article.reference.resolver.locator_vector import LocatorVector
from app.article.reference.resolver.token import TokenGroup


@dataclass
class SentenceReferenceGroup:
    """
    Sentence 内に出現する Reference を出現順に管理する器。

    Reference 単体は1つの TokenGroup のラッパーにすぎないため、
    last_ref などの文脈状態はこの層で扱う。
    FullLocation への確定は、さらに上層の resolver で行う。
    """

    sentence: Sentence
    this_sentence_location: AbsoluteArticleLocation
    references: list[Reference] = field(default_factory=list)

    MARK_PATTERN = re.compile(r"[{][^{}]*[}]")

    @classmethod
    def create_object(
            cls,
            sentence: Sentence,
            this_sentence_location: AbsoluteArticleLocation,
    ) -> "SentenceReferenceGroup":
        """Sentence.marked_text から Reference を出現順に生成する。"""
        if not sentence.marked_text:
            raise ValueError(
                f"Sentence.marked_text is required: location={this_sentence_location.addr}, sentence_num={sentence.num}"
            )

        references = [cls._create_reference(match) for match in cls.MARK_PATTERN.finditer(sentence.marked_text)]
        group = cls(
            sentence=sentence,
            this_sentence_location=this_sentence_location,
            references=references,
        )
        group._apply_reference_axis_rules()
        return group

    @classmethod
    def _create_reference(cls, match: re.Match) -> Reference:
        """1個の reference mark から Reference を生成する。"""
        raw_mark = match.group(0)
        raw_text, arabic_text, locator_part = cls._split_mark(raw_mark)
        return Reference(
            raw_mark_text=raw_mark,
            raw_text=raw_text,
            arabic_text=arabic_text,
            token_group=TokenGroup.create_object(locator_part),
            start_index=match.start(),
            end_index=match.end(),
        )

    @staticmethod
    def _split_mark(raw_mark: str) -> tuple[str, str, str]:
        """3枠 reference mark を raw / arabic / locator に分解する。"""
        elements = raw_mark.strip("{}").split("|")
        if len(elements) != 3:
            raise ValueError(f"reference mark must have 3 fields: {raw_mark}")
        return tuple(elements)  # type: ignore[return-value]

    def _apply_reference_axis_rules(self) -> None:
        """
        Sentence 内の Reference を出現順に走査し、各 Reference が読むべき起点軸を仮決定する。

        ここでは FullLocation を確定しない。
        参照表現が this_sentence_location / last_ref / active_ref のどれを起点にしそうかだけを保持する。
        """
        active_ref_exists = False
        last_ref_exists = False
        previous_end = 0

        for reference in self.references:
            gap_before = self.sentence.marked_text[previous_end:reference.start_index]
            reference.gap_before_text = gap_before

            if not self._is_connector_only_gap(gap_before):
                active_ref_exists = False

            vector = LocatorVector.from_token_group(reference.token_group)
            reference.base_axis = self._select_base_axis(
                vector=vector,
                active_ref_exists=active_ref_exists,
                last_ref_exists=last_ref_exists,
            )
            reference.semantic_mark_text = self._create_semantic_mark_text(vector)

            if reference.base_axis != "semantic":
                last_ref_exists = True
                active_ref_exists = True

            previous_end = reference.end_index

    def _select_base_axis(
            self,
            vector: LocatorVector,
            active_ref_exists: bool,
            last_ref_exists: bool,
    ) -> str:
        """LocatorVector と文脈状態から、Reference の起点軸を選ぶ。"""
        if vector.is_law_only:
            return "semantic"

        if vector.has_same_reference:
            return "last_ref" if last_ref_exists else "this"

        if vector.has_law_or_article:
            return "absolute"

        if vector.is_plain_inner_only and active_ref_exists:
            return "active_ref"

        if vector.has_shift:
            return "this"

        return "this"

    @staticmethod
    def _create_semantic_mark_text(vector: LocatorVector) -> str | None:
        """location 参照ではない semantic mark に落とせる場合、その mark 文字列を返す。"""
        if vector.is_law_only:
            return f"<{INLINE_MARK_HINT}={HINT_KEY_LAW}:{vector.law_cell}>"
        return None

    @classmethod
    def _is_connector_only_gap(cls, gap_text: str) -> bool:
        """Reference 同士の隙間が、参照連鎖を維持できる接続語だけかを返す。"""
        gap = gap_text.strip()
        for connector in CONNECTOR_TEXTS:
            gap = gap.replace(connector, "")
        return not gap.strip()
