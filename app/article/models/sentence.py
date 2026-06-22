# touki-navi/models/sentence.py
from dataclasses import dataclass
from bs4.element import Tag
from app.article.constants.enums import SentenceType

@dataclass(frozen=True)
class Sentence:
    """
    条文内の最小単位である「一文」を表すクラス。
    """
    num: str  # XML属性のNum
    raw_text: str  # 純粋なテキスト内容
    resolved_text: str
    sentence_node: Tag  # BeautifulSoupのTagオブジェクトとして定義
    sentence_type: SentenceType = SentenceType.SENTENCE  # Enum型をデフォルト付きで導入

    @property
    def text(self) -> str:
        """
        便宜上、解決済みがあればそれを、なければ生を返すプロパティ
        （後続の表示ロジックを壊さないための工夫）
        """
        return self.resolved_text if self.resolved_text else self.raw_text

    def to_dict(self):
        # Tagを除外した辞書を返す
        return {
            "num": self.num,
            "raw_text": self.raw_text,
            "resolved_text": self.resolved_text,
            "sentence_type": self.sentence_type
        }
{[会社法][第一条][第一項][第一号][イ][（１）]|[会社法][第1条][第1項][第1号][イ][（１）]|[kai.1.1.1.1.1]}