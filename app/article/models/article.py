# touki-navi/models/article_xml.py
from dataclasses import dataclass, replace
from typing import List
from app.article.models._____paragraph import Paragraph
from app.article.models.article_loc import FullLocation
from app.article.models.article_loc import ArticleLocation
from app.article.constants.enums import LawType


@dataclass(frozen=True)
class Article:
    """
    条(Article)を表すクラス。
    """
    law_type:LawType
    num: str  # XML属性のNum (例: "1", "1_2")
    title: str  # 表示用タイトル (例: "第一条", "第一条の二")
    caption: str  # 条文の見出し (例: "（目的）", "（定義）")
    paragraphs: List[Paragraph]  # 項のリスト（ElementType.PARAGRAPH を想定）

    @property
    def location(self) -> FullLocation:
        """
        自分自身の「条」レベルの座標を動的に生成する。
        Elementsに依存せず、自身の条番号(num)と法典名(law_type)から決定する
        """
        return FullLocation(
            law_type=self.law_type,
            article_num=self.num,
            relative_loc=ArticleLocation()  # (0,0,0,0)
        )

    @property
    def is_branch(self) -> bool:
        """枝番（第〇条の二など）かどうかを判定"""
        return "_" in self.num

    @property
    def full_title(self) -> str:
        """タイトルと見出しを結合した文字列を返す"""
        return f"{self.title} {self.caption}".strip()

    def resolve_all(self) -> 'Article':
        """配下の全 Paragraph に対して参照条文解決を実行し、新しい Article を返す"""
        resolved_paragraphs = [p.resolve_references() for p in self.paragraphs]
        return replace(self, paragraphs=resolved_paragraphs)

    def to_dict(self):
        return {
            "num": self.num,
            "title": self.title,
            "caption": self.caption,
            "paragraphs": [p.to_dict() for p in self.paragraphs]
        }

