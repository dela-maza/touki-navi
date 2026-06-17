# models/law.py
from app.article.models.article import ArticleIndex
from app.article.constants.enums import LawType

class LawLibrary:
    """
    全ての法典の『背表紙（Index）』を管理する書庫。
    解析に必要な時、いつでもどこからでも参照できる。
    """
    _indices: dict[LawType, ArticleIndex] = {}

    @classmethod
    def register(cls, law_type: LawType, id_list: list[str]):
        """XML解析の初期段階で、IDの並び順を登録する"""
        cls._indices[law_type] = ArticleIndex(id_list)

    @classmethod
    def get_index(cls, law_type: LawType) -> ArticleIndex:
        """指定された法典のインデックスを返す"""
        index = cls._indices.get(law_type)
        if not index:
            raise ValueError(f"Law {law_type} is not registered in the library.")
        return index