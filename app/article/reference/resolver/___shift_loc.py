# app/article/reference/resolver/shift_loc.py
from app.article.constants.enums import ArticleDepth
from app.article.models.article_loc import AbsoluteArticleLocation
from app.article.models.index import ArticleElementLocationIndex, ArticleIndex
from app.article.reference.resolver.token import ShiftToken


class ShiftLocationResolver:
    """
    ShiftToken を ArticleIndex / ArticleElementLocationIndex で解決する。

    前条・次条など Article をまたぐ単一 shift は ArticleIndex、
    前項・前号など Article 内部の単一 shift は ArticleElementLocationIndex を使う。
    """

    def __init__(
            self,
            article_index: ArticleIndex | None = None,
            element_index: ArticleElementLocationIndex | None = None,
    ):
        self.article_index = article_index
        self.element_index = element_index

    def resolve_locations(self, location: AbsoluteArticleLocation, token: ShiftToken) -> list[AbsoluteArticleLocation]:
        """ShiftToken の locator_key に応じて、条単位または Article 内部要素の shift を解決する。"""
        if token.locator_key == "a":
            return self._apply_article_shift(location, token)
        return self._apply_element_shift(location, token)

    def _apply_article_shift(self, location: AbsoluteArticleLocation, token: ShiftToken) -> list[AbsoluteArticleLocation]:
        """前条・同条・次条・前○条を解決する。"""
        if token.offset_num == 0:
            return [location.update_article(location.article_num)]

        if self.article_index is None:
            raise ValueError(f"ArticleIndex is required for article shift: {location.addr}")

        if token.offset_num not in (-1, 1):
            raise ValueError(f"unexpected article shift offset: {token.offset}")

        target_ids = self.article_index.get_offset_ids(location.article_num, token.offset_num, length=1)
        return [location.update_article(target_id) for target_id in target_ids]

    def _apply_element_shift(self, location: AbsoluteArticleLocation, token: ShiftToken) -> list[AbsoluteArticleLocation]:
        """前項・前号・各号など、Article 内部要素の shift を解決する。"""
        if self.element_index is None:
            raise ValueError(f"ArticleElementLocationIndex is required for element shift: {location.addr}")

        depth: ArticleDepth = token.get_article_depth()

        if token.offset_num in (-1, 0, 1):
            siblings = self.element_index.get_siblings(location, depth)
            current_idx = self._find_sibling_index(siblings, location, depth)
            if current_idx is None:
                return []

            target_idx = current_idx + token.offset_num
            if target_idx < 0 or target_idx >= len(siblings):
                return []

            return [siblings[target_idx]]

        raise ValueError(f"unexpected element shift offset: {token.offset}")

    @staticmethod
    def _find_sibling_index(
            siblings: list[AbsoluteArticleLocation],
            location: AbsoluteArticleLocation,
            depth: ArticleDepth,
    ) -> int | None:
        """兄弟 location 一覧の中から、指定 depth の値が一致する位置を探す。"""
        target_val = location.down_merge.get_path_index(depth)
        for idx, sibling in enumerate(siblings):
            if sibling.down_merge.get_path_index(depth) == target_val:
                return idx
        return None
