# app/article/models/index.py
from dataclasses import dataclass, field

from app.article.constants.enums import ArticleDepth
from app.article.models.article import Article
from app.article.models.article_loc import ArticleLocation, FullLocation


class ArticleIndex:
    """
    法典内の Article 一覧と、その条番号順序を管理する index。
    """

    def __init__(
            self,
            articles: list[Article],
            element_locations_by_article: dict[str, list[FullLocation]] | None = None,
    ):
        self.articles: list[Article] = articles

        # ID（"10", "11_2" 等）の順序付きリスト
        self.id_list: list[str] = [article.num for article in articles]

        # Article.num から、その Article 内部の Paragraph / Item / Subitem location を引くためのmap
        self.element_locations_by_article: dict[str, list[FullLocation]] = element_locations_by_article or {}

        # IDからインデックスを引くためのハッシュマップ
        self.index_cache: dict[str, int] = {
            id_val: i for i, id_val in enumerate(self.id_list)
        }

    @classmethod
    def from_articles(
            cls,
            articles: list[Article],
            element_locations_by_article: dict[str, list[FullLocation]] | None = None,
    ) -> "ArticleIndex":
        """生成済み Article の list を保持する ArticleIndex を生成する。"""
        return cls(articles, element_locations_by_article)

    @classmethod
    def from_article_ids(cls, id_list: list[str]) -> "ArticleIndex":
        """Article 本体がない旧用途向けに、num だけを持つ軽量 ArticleIndex を生成する。"""
        index = cls([])
        index.id_list = id_list
        index.index_cache = {
            id_val: i for i, id_val in enumerate(id_list)
        }
        return index

    def get_element_locations(self, article_num: str) -> list[FullLocation]:
        """Article.num から、その Article 内部要素の location 一覧を返す。"""
        return self.element_locations_by_article.get(article_num, [])

    def get_offset_ids(self, current_id: str, offset: int, length: int = 1) -> list[str]:
        """
        指定されたオフセットと長さに基づいて、IDの範囲を返す。
        """
        if current_id not in self.index_cache:
            return []

        current_idx = self.index_cache[current_id]
        start_idx = current_idx + offset
        end_idx = start_idx + length

        # 安全な範囲でスライス
        actual_start = max(0, start_idx)
        actual_end = min(len(self.id_list), end_idx)

        return self.id_list[actual_start:actual_end]


@dataclass
class ArticleElementLocationIndex:
    """
    Article 1個の内部要素 location だけを扱う flat index。

    前条・次条のように Article をまたぐ shift は ArticleIndex の責務。
    このクラスは、同一 Article 内の項・号・目・細目について、
    同じ親を持つ兄弟要素の並び順だけを管理する。
    """

    article_location: FullLocation
    locations_by_addr: dict[str, FullLocation] = field(default_factory=dict)
    child_locations_by_parent_addr: dict[str, list[FullLocation]] = field(default_factory=dict)

    @classmethod
    def from_locations(
            cls,
            article_location: FullLocation,
            locations: list[FullLocation],
    ) -> "ArticleElementLocationIndex":
        """ArticleXml が収集した location 一覧から、Article 内部要素の索引を生成する。"""
        index = cls(article_location=article_location)

        for location in locations:
            index._add_location(location, location.relative_loc.depth)

        return index

    def get_by_addr(self, addr: str) -> FullLocation | None:
        """addr から Article 内部要素 location を返す。"""
        return self.locations_by_addr.get(addr)

    def has_location(self, location: FullLocation) -> bool:
        """指定 location が Article 内部要素として存在するかを返す。"""
        return location.addr in self.locations_by_addr

    def get_siblings(self, location: FullLocation, depth: ArticleDepth) -> list[FullLocation]:
        """location と同じ親を持つ、同階層の兄弟 location 一覧を返す。"""
        parent_key = self._parent_key(location, depth)
        return self.child_locations_by_parent_addr.get(parent_key, [])

    def get_children(self, parent: FullLocation, depth: ArticleDepth) -> list[FullLocation]:
        """parent を親に持つ、指定階層 depth の子要素一覧を返す。"""
        return self.child_locations_by_parent_addr.get(parent.addr, [])

    def _add_location(self, location: FullLocation, depth: ArticleDepth) -> None:
        """1つの location を addr map と親別の子要素 list の両方へ登録する。"""
        self.locations_by_addr[location.addr] = location

        parent_key = self._parent_key(location, depth)
        self.child_locations_by_parent_addr.setdefault(parent_key, []).append(location)

    @classmethod
    def _parent_key(cls, location: FullLocation, depth: ArticleDepth) -> str:
        """location の親 location を addr 文字列として返す。"""
        return cls._parent_location(location, depth).addr

    @staticmethod
    def _parent_location(location: FullLocation, depth: ArticleDepth) -> FullLocation:
        """指定 depth の親にあたる location を作る。"""
        path = list(location.relative_loc.path)
        for idx in range(depth.index, len(path)):
            path[idx] = "0"

        return FullLocation(
            law_type=location.law_type,
            article_num=location.article_num,
            relative_loc=ArticleLocation(tuple(path)),
        )
