# app/article/reference/group/main.py
import re
from dataclasses import dataclass, field

from app.article.constants.inline_marks import (
    INLINE_MARK_CONNECTOR,
    INLINE_MARK_RANGE_CONNECTOR,
)
from app.article.models.article_loc import AbsoluteArticleLocation
from app.article.models.reference import Reference
from app.article.models.sentence import Sentence
from app.article.reference.group.builder import SentenceReferenceVectorBuilder
from app.article.reference.group.connector import ReferenceConnector, ReferenceRangeConnector
from app.article.reference.group.state import SentenceLocationState
from app.article.reference.resolver.token import TokenGroup

ReferenceAppearance = Reference | ReferenceConnector | ReferenceRangeConnector


@dataclass
class SentenceReferenceGroup:
    """
    Sentence 内に出現する Reference を出現順に管理する器。

    location 関係の状態は SentenceLocationState に保持し、
    ordered_appearances の巡回処理は SentenceReferenceVectorBuilder に委譲する。
    """

    sentence: Sentence
    this_sentence_location: AbsoluteArticleLocation # sentenceのlocation（不変）
    references: list[Reference] = field(default_factory=list)
    ordered_appearances: list[ReferenceAppearance] = field(default_factory=list)
    location_state: SentenceLocationState | None = None

    APPEARANCE_PATTERN = re.compile(r"[{][^{}]*[}]|<[^<>]*>")

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

        ordered_appearances = cls._create_ordered_appearances(sentence.marked_text)
        group = cls(
            sentence=sentence,
            this_sentence_location=this_sentence_location,
            references=[appearance for appearance in ordered_appearances if isinstance(appearance, Reference)],
            ordered_appearances=ordered_appearances,
            location_state=SentenceLocationState.create_initial(this_sentence_location),
        )
        group.location_state = SentenceReferenceVectorBuilder(group).build()
        return group

    @classmethod
    def _create_ordered_appearances(cls, marked_text: str) -> list[ReferenceAppearance]:
        """marked_text から Reference / connector を出現順に抽出する。"""
        appearances: list[ReferenceAppearance] = []
        for match in cls.APPEARANCE_PATTERN.finditer(marked_text):
            appearance = cls._create_appearance(match.group(0))
            if appearance is not None:
                appearances.append(appearance)
        return appearances

    @classmethod
    def _create_appearance(cls, mark_text: str) -> ReferenceAppearance | None:
        """1個の mark 文字列から、location 解析に必要な appearance を生成する。"""
        if mark_text.startswith("{"):
            return cls._create_reference(mark_text)

        if mark_text.startswith(f"<{INLINE_MARK_CONNECTOR}="):
            return ReferenceConnector(text=cls._extract_inline_mark_value(mark_text))

        if mark_text.startswith(f"<{INLINE_MARK_RANGE_CONNECTOR}="):
            return ReferenceRangeConnector(text=cls._extract_inline_mark_value(mark_text))

        return None

    @classmethod
    def _create_reference(cls, raw_mark: str) -> Reference:
        """1個の reference mark から Reference を生成する。"""
        raw_text, arabic_text, locator_part = cls._split_mark(raw_mark)
        return Reference(
            raw_mark_text=raw_mark,
            raw_text=raw_text,
            arabic_text=arabic_text,
            token_group=TokenGroup.create_object(locator_part),
        )

    @staticmethod
    def _split_mark(raw_mark: str) -> tuple[str, str, str]:
        """3枠 reference mark を raw / arabic / locator に分解する。"""
        elements = raw_mark.strip("{}").split("|")
        if len(elements) != 3:
            raise ValueError(f"reference mark must have 3 fields: {raw_mark}")
        return tuple(elements)  # type: ignore[return-value]

    @staticmethod
    def _extract_inline_mark_value(mark_text: str) -> str:
        """<c=及び> / <r=から> から value 部分だけを取り出す。"""
        return mark_text.strip("<>").split("=", 1)[1]
