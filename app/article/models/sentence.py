# touki-navi/models/sentence.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.article.models.reference import Reference

@dataclass
class Sentence:
    """<Sentence> タグそのものを表す、末端の最小テキストコンテナ"""
    num: str
    text: str
    marked_text: str = ""
    references: List["Reference"] = field(default_factory=list)
    # writing_mode: str = "vertical"

class BlockSentenceBase(ABC):
    """
    <ItemSentence> などの文章ブロックを表す、厳格な抽象基盤クラス（インターフェース）。
    """

    @property
    @abstractmethod
    def flat_text(self) -> str:
        """
        子クラスに対して、平文テキストを返すプロパティの実装を『絶対強制』する。
        """
        pass


# =================================================================
# Columnが【無い】
# =================================================================
@dataclass
class PlainBlockSentence(BlockSentenceBase):
    """Columnを持たない、ただのフラットな文の並びを管理するクラス"""
    sentences: List[Sentence] = field(default_factory=list)

    @property
    def flat_text(self) -> str:
        # 💡 基盤クラスの抽象プロパティを素直に具現化
        return "".join([s.text for s in self.sentences])


# =================================================================
# Columnが【有る】
# =================================================================
@dataclass
class ColumnBlockSentence(BlockSentenceBase):
    """Column（表・定義）構造を持つ、多列マトリクスを管理するクラス"""
    columns: Dict[int, List[Sentence]] = field(default_factory=dict)

    @property
    def flat_text(self) -> str:
        # 💡 基盤クラスの抽象プロパティを素直に具現化
        text = ""
        for idx in sorted(self.columns.keys()):
            text += "".join([s.text for s in self.columns[idx]])
        return text
