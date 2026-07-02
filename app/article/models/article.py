# app/article/models/article.py
from dataclasses import dataclass, field, replace
from typing import List, Any
from app.article.constants.enums import LawType
from app.article.models.article_loc import AbsoluteArticleLocation, ArticleInnerLocation
from app.article.models.sentence import BlockSentenceBase

# =================================================================
# 🧬 1. 基盤インターフェース（下流階層用）
# =================================================================
@dataclass
class SubDivisionBase:
    """
    号・目・細目など、下流へネストしていく箇条書き階層（Subdivision）の共通基盤。
    """
    num: str                  # XML属性のNum（例: "1", "1_2"）
    title: str                # 画面表示用タイトル（例: "一", "イ", "（１）"）
    location: AbsoluteArticleLocation    # 空文字パディング行列が入った絶対座標
    body: BlockSentenceBase   # ABCで定義された、Columnの有無を隠蔽した文章ブロック


# =================================================================
# 🌿 2. 従・箇条書きツリーノード
# =================================================================
@dataclass
class Subitem2(SubDivisionBase):
    """細目 (Subitem2) ノード"""
    children: List[Any] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "num": self.num,
            "title": self.title,
            "body": self.body.flat_text,  # ABCの窓口から安全にテキスト化
            "children": self.children
        }


@dataclass
class Subitem1(SubDivisionBase):
    """目 (Subitem1) ノード"""
    children: List[Subitem2] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "num": self.num,
            "title": self.title,
            "body": self.body.flat_text,
            "children": [c.to_dict() for c in self.children]
        }


@dataclass
class Item(SubDivisionBase):
    """号 (Item) ノード"""
    children: List[Subitem1] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "num": self.num,
            "title": self.title,
            "body": self.body.flat_text,
            "children": [c.to_dict() for c in self.children]
        }


# =================================================================
# 👑 3. 主・トップレベルノード
# =================================================================
@dataclass
class Paragraph:
    """
    項 (Paragraph) ノード
    箇条書き（SubDivisionBase）とは完全に分離された、条文直下の絶対的独立ブロック。
    """
    num: str
    location: AbsoluteArticleLocation
    body: BlockSentenceBase
    items: List[Item] = field(default_factory=list)

    def resolve_references(self) -> 'Paragraph':
        """【TODO】この項の配下にある文章の参照解決を走り終えて、新しい項を返す"""
        # 今はモックとして自分自身をそのまま返す（後ほど実装）
        return self

    def to_dict(self) -> dict:
        return {
            "num": self.num,
            "body": self.body.flat_text,
            "items": [i.to_dict() for i in self.items]
        }


# =================================================================
# 🏛️ 4. ルートエンティティ
# =================================================================
@dataclass(frozen=True)
class Article:
    """条 (Article) を表すルートクラス"""
    law_type: LawType
    num: str
    title: str
    caption: str
    paragraphs: List[Paragraph]

    @property
    def location(self) -> AbsoluteArticleLocation:
        return AbsoluteArticleLocation(
            law_type=self.law_type,
            article_num=self.num,
            inner_loc=ArticleInnerLocation()
        )

    @property
    def is_branch(self) -> bool:
        return "_" in self.num

    @property
    def full_title(self) -> str:
        return f"{self.title} {self.caption}".strip()

    def resolve_all(self) -> 'Article':
        """配下の全 Paragraph に対して参照条文解決を実行し、新しい Article を返す"""
        resolved_paragraphs = [p.resolve_references() for p in self.paragraphs]
        return replace(self, paragraphs=resolved_paragraphs)

    def to_dict(self) -> dict:
        return {
            "num": self.num,
            "title": self.title,
            "caption": self.caption,
            "paragraphs": [p.to_dict() for p in self.paragraphs]
        }
