# app/article/reference/resolver/range_loc.py
from app.article.constants.enums import ArticleDepth
from app.article.models.article_loc import FullLocation
from app.article.models.index import ArticleElementLocationIndex, ArticleIndex
from app.article.reference.resolver.token import RangeToken, ShiftRangeToken


class RangeLocationResolver:
    """
    RangeToken を ArticleIndex / ArticleElementLocationIndex で複数 location へ展開する。

    前三条のように Article をまたぐ範囲は ArticleIndex、
    前三号・各号のような Article 内部の範囲は ArticleElementLocationIndex を使う。
    """

    def __init__(
            self,
            article_index: ArticleIndex | None = None,
            element_index: ArticleElementLocationIndex | None = None,
    ):
        self.article_index = article_index
        self.element_index = element_index

    def resolve_locations(self, location: FullLocation, token: RangeToken | ShiftRangeToken) -> list[FullLocation]:
        """RangeToken の locator_key に応じて、条単位または Article 内部要素の範囲を返す。"""
        if token.locator_key == "a":
            return self._apply_article_range(location, token)
        return self._apply_element_range(location, token)

    def _apply_article_range(self, location: FullLocation, token: RangeToken | ShiftRangeToken) -> list[FullLocation]:
        """前○条を複数 location として返す。"""
        if token.range_value == RangeToken.EACH:
            raise ValueError(f"article range requires numeric value: {token.raw}")

        if self.article_index is None:
            raise ValueError(f"ArticleIndex is required for article range: {location.addr}")

        target_ids = self.article_index.get_offset_ids(location.article_num, token.range_value, abs(token.range_value))
        return [location.update_article(target_id) for target_id in target_ids]

    def _apply_element_range(self, location: FullLocation, token: RangeToken | ShiftRangeToken) -> list[FullLocation]:
        """前○項・前○号・各号など、Article 内部要素の範囲を返す。"""
        if self.element_index is None:
            raise ValueError(f"ArticleElementLocationIndex is required for element range: {location.addr}")

        depth: ArticleDepth = token.get_article_depth()

        if token.range_value == RangeToken.EACH:
            return self.element_index.get_children(location, depth)

        siblings = self.element_index.get_siblings(location, depth)
        current_idx = self._find_sibling_index(siblings, location, depth)
        if current_idx is None:
            return []

        start_idx = current_idx + token.range_value
        end_idx = start_idx + abs(token.range_value)
        actual_start = max(0, start_idx)
        actual_end = min(len(siblings), end_idx)

        if actual_start >= actual_end:
            return []
        return siblings[actual_start:actual_end]

    @staticmethod
    def _find_sibling_index(
            siblings: list[FullLocation],
            location: FullLocation,
            depth: ArticleDepth,
    ) -> int | None:
        """兄弟 location 一覧の中から、指定 depth の値が一致する位置を探す。"""
        target_val = location.relative_loc.get_path_index(depth)
        for idx, sibling in enumerate(siblings):
            if sibling.relative_loc.get_path_index(depth) == target_val:
                return idx
        return None
