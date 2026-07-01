# app/article/reference/resolver/token_group_location.py
from app.article.models.article_loc import FullLocation
from app.article.models.index import ArticleElementLocationIndex, ArticleIndex
from app.article.reference.resolver.range_loc import RangeLocationResolver
from app.article.reference.resolver.shift_loc import ShiftLocationResolver
from app.article.reference.resolver.token import LocationToken, RangeToken, ShiftRangeToken, ShiftToken, TokenBase, TokenGroup


class TokenGroupLocation:
    """
    TokenGroup を解析し、FullLocation 候補を生成する。

    Token の派生クラスを見て、Location / Shift / Range のどれか一つだけを呼び出す。
    各号や前○号のように複数候補が出る場合に備え、戻り値は常に list[FullLocation] とする。
    """

    def __init__(
            self,
            article_index: ArticleIndex | None = None,
            element_index: ArticleElementLocationIndex | None = None,
    ):
        self.shift_resolver = ShiftLocationResolver(article_index=article_index, element_index=element_index)
        self.range_resolver = RangeLocationResolver(article_index=article_index, element_index=element_index)

    def create_locations_by_base_location(self, base_location: FullLocation, token_group: TokenGroup) -> list[FullLocation]:
        """base_location を起点に、TokenGroup の順序どおり location 候補を作る。"""
        locations: list[FullLocation] = [base_location]

        for token in token_group.tokens:
            next_locations: list[FullLocation] = []
            for location in locations:
                next_locations.extend(self._create_locations_from_token(location, token))
            locations = next_locations

            if not locations:
                return []

        return locations

    def _create_locations_from_token(self, location: FullLocation, token: TokenBase) -> list[FullLocation]:
        """Token の派生クラスに応じて、対応する resolver を一つだけ呼び出す。"""
        if isinstance(token, LocationToken):
            return [token.resolve_location(location)]

        if isinstance(token, ShiftToken):
            return self.shift_resolver.resolve_locations(location, token)

        if isinstance(token, (RangeToken, ShiftRangeToken)):
            return self.range_resolver.resolve_locations(location, token)

        raise TypeError(f"unsupported token type: {type(token).__name__}")
