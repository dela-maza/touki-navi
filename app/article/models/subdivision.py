# touki-navi/models/subdivision.py
from dataclasses import dataclass, field
from typing import List, Dict, Any
from app.article.constants.enums import ArticleDepth
from app.article.models.article_loc import FullLocation
from app.article.models.sentence import Sentence

@dataclass
class Subdivision:
    """
    項・号・目など、条文のすべての構成要素（区分）の基底データ構造
    """
    num: str
    location: FullLocation
    sentences: List[Sentence]
    depth: ArticleDepth = ArticleDepth.PARAGRAPH  # デフォルト値
    children: List['Subdivision'] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "depth": self.depth.name,
            "num": self.num,
            "location": self.location.to_dict(),
            "sentences": [s.to_dict() for s in self.sentences],
            "children": [child.to_dict() for child in self.children]
        }

# =================================================================
# 各階層のアイデンティティ（型）の定義
# 1つのモジュールにまとめておくことで、インポートも管理も劇的に楽になります
# =================================================================

@dataclass
class Paragraph(Subdivision):
    """条文の直下にぶら下がる独立した『項』を表すクラス"""
    depth: ArticleDepth = ArticleDepth.PARAGRAPH

@dataclass
class Item(Subdivision):
    """項の直下にぶら下がる『号』を表すクラス"""
    depth: ArticleDepth = ArticleDepth.ITEM

@dataclass
class Subitem1(Subdivision):
    """号の直下にぶら下がる『目（イ、ロ、ハ...）』を表すクラス"""
    depth: ArticleDepth = ArticleDepth.SUB_ITEM_1

@dataclass
class Subitem2(Subdivision):
    """目の直下にぶら下がる『目2（（一）、（二）...）』を表すクラス"""
    depth: ArticleDepth = ArticleDepth.SUB_ITEM_2
    # 最下層（目2）のため、childrenの初期化引数をロック（常に空）
    children: List[Subdivision] = field(default_factory=list, init=False)