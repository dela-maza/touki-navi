# app/article/reference/resolver/token_group_location_analyzer.py
import re

from app.article.models.article_loc import AbsoluteArticleLocation
from app.article.models.index import ArticleElementLocationIndex, ArticleIndex
from app.article.models.reference import Reference
from app.article.models.sentence import Sentence
from app.article.reference.resolver.locator_vector import LocatorVector
from app.article.reference.resolver.token import TokenGroup


class TokenGroupLocationAnalyzer:
    """
    Sentence.marked_text に含まれる {...} を左から読み、Reference の一覧を生成する。

    このクラスは DB を参照しない。
    this_sentence_location と last_ref_location の二軸から絶対座標リストを作るところまでを責務とする。
    """

    MARK_PATTERN = re.compile(r"[{][^{}]*[}]")

    def __init__(
            self,
            article_index: ArticleIndex | None = None,
            element_index: ArticleElementLocationIndex | None = None,
    ):
        self.article_index = article_index
        self.element_index = element_index

    def resolve_sentence(
            self,
            sentence: Sentence,
            this_sentence_location: AbsoluteArticleLocation,
            last_ref_location: AbsoluteArticleLocation | None = None,
    ) -> list[Reference]:
        """Sentence から参照 mark を抽出し、Reference の一覧を返す。"""
        if not sentence.marked_text:
            raise ValueError(
                f"Sentence.marked_text is required: location={this_sentence_location.addr}, sentence_num={sentence.num}"
            )

        return self.resolve_text(sentence.marked_text, this_sentence_location, last_ref_location)

    def resolve_text(
            self,
            marked_text: str,
            this_sentence_location: AbsoluteArticleLocation,
            last_ref_location: AbsoluteArticleLocation | None = None,
    ) -> list[Reference]:
        """marked_text 内の {...} を左から順に Reference へ変換する。"""
        references: list[Reference] = []
        current_last_ref_location = last_ref_location

        for match in self.MARK_PATTERN.finditer(marked_text):
            reference = self._resolve_mark(
                raw_mark=match.group(0),
                this_sentence_location=this_sentence_location,
                last_ref_location=current_last_ref_location,
            )
            references.append(reference)
            current_last_ref_location = self._next_last_ref_location(reference, current_last_ref_location)

        return references

    def _resolve_mark(
            self,
            raw_mark: str,
            this_sentence_location: AbsoluteArticleLocation,
            last_ref_location: AbsoluteArticleLocation | None,
    ) -> Reference:
        """1個の {...} から TokenGroup を作り、二軸の絶対座標リストを生成する。"""
        _, _, locator_part = self._split_mark(raw_mark)
        token_group = TokenGroup.create_object(locator_part)

        this_sentence_locations = self._create_locations_by_base_location(this_sentence_location, token_group)
        last_ref_locations = (
            self._create_locations_by_base_location(last_ref_location, token_group)
            if last_ref_location
            else []
        )

        return Reference(
            raw_mark=raw_mark,
            token_group=token_group,
            this_sentence_locations=this_sentence_locations,
            last_ref_locations=last_ref_locations,
        )

    @staticmethod
    def _create_locations_by_base_location(
            base_location: AbsoluteArticleLocation,
            token_group: TokenGroup,
    ) -> list[AbsoluteArticleLocation]:
        """
        base_location と TokenGroup から FullLocation 候補を生成する。

        range を含む LocatorVector はまだ FullLocation に畳めないため、
        上層の vector resolver 実装まで空リストで返す。
        """
        locator_vector = LocatorVector.from_token_group(token_group)
        merged_vector = locator_vector.merge_base_location(base_location)
        if any(LocatorVector._is_spread_cell(cell) for cell in merged_vector.path):
            return []
        return [AbsoluteArticleLocation(path=merged_vector.path)]

    @staticmethod
    def _split_mark(raw_mark: str) -> tuple[str, str, str]:
        """3枠 reference mark を raw / arabic / locator に分解する。"""
        elements = raw_mark.strip("{}").split("|")
        if len(elements) != 3:
            raise ValueError(f"reference mark must have 3 fields: {raw_mark}")
        return tuple(elements)  # type: ignore[return-value]

    @staticmethod
    def _next_last_ref_location(
            reference: Reference,
            current_last_ref_location: AbsoluteArticleLocation | None,
    ) -> AbsoluteArticleLocation | None:
        """
        次の参照 mark が使う last_ref_location を決める。

        ここでは上位レイヤの採用判断までは行わず、
        直近 mark から計算できた最後の絶対座標を次の計算起点として使う。
        """
        if reference.last_ref_location is not None:
            return reference.last_ref_location
        if reference.this_sentence_location is not None:
            return reference.this_sentence_location
        return current_last_ref_location
