from enum import Enum
from typing import Optional


class LawType(Enum):
    KAI = ("kai", "会社法")
    SHOU = ("syou", "商法")
    SHOU_TOU = ("shoutou", "商業登記法")
    SHOU_TOU_KI = ("shoutouki", "商業登記規則")

    def __init__(self, short_name, name_jp):
        self.short_name = short_name
        self.name_jp = name_jp

    @classmethod
    def from_short_name(cls, short_name: str) -> "LawType":
        """URLやファイル名に使う short_name から LawType を取得する。"""
        for law_type in cls:
            if law_type.short_name == short_name:
                return law_type
        raise ValueError(f"unknown law short_name: {short_name}")

class ArticleDepth(Enum):
    PARAGRAPH = (0, "p", "Paragraph", "項")
    ITEM = (1, "i", "Item", "号")
    SUB_ITEM_1 = (2, "s1", "Subitem1", "目")
    SUB_ITEM_2 = (3, "s2", "Subitem2", "細目")

    def __init__(self, index: int, locator_key: str, tag_name: str, label_jp: str):
        self.index = index
        self.locator_key = locator_key
        self.tag_name = tag_name
        self.label_jp = label_jp

    @classmethod
    def from_index(cls, index: int) -> Optional["ArticleDepth"]:
        for depth in cls:
            if depth.index == index:
                return depth
        return None

    @classmethod
    def determine_depth(cls, text: str) -> Optional["ArticleDepth"]:
        if text.endswith("項"):
            return cls.PARAGRAPH
        if text.endswith("号"):
            return cls.ITEM
        if text.startswith(("（", "(")) and text.endswith(("）", ")")):
            return cls.SUB_ITEM_2
        if len(text) == 1 and text in "イロハニホヘトチリヌルヲ":
            return cls.SUB_ITEM_1
        return None

    @classmethod
    def from_label(cls, label: str):
        """「項」や「号」という文字から Enum を特定する"""
        for depth in cls:
            if depth.label_jp == label:
                return depth
        return None

    @classmethod
    def from_locator_key(cls, locator_key: str) -> "ArticleDepth":
        """Tokenのlocator_key（p, i, s1, s2）から ArticleDepth を特定する"""
        for depth in cls:
            if depth.locator_key == locator_key:
                return depth
        raise KeyError(locator_key)


class TocDepth(Enum):
    PART = (0, "p", "Part", "編")
    CHAPTER = (1, "c", "Chapter", "章")
    SECTION = (2, "s", "Section", "節")
    SUB_SECTION = (3, "ss", "Subsection", "款")
    DIVISION = (4, "d", "Division", "目")

    def __init__(self, index: int, locator_key: str, tag_name: str, label_jp: str):
        self.index = index
        self.locator_key = locator_key
        self.tag_name = tag_name
        self.label_jp = label_jp

    @classmethod
    def from_index(cls, index: int) -> Optional["TocDepth"]:
        for depth in cls:
            if depth.index == index:
                return depth
        return None

    @classmethod
    def from_label(cls, label: str) -> Optional["TocDepth"]:
        """「編」や「章」という文字から Enum を特定する。"""
        for depth in cls:
            if depth.label_jp == label:
                return depth
        return None

    @classmethod
    def from_locator_key(cls, locator_key: str) -> "TocDepth":
        """Toc用Tokenのlocator_key（p, c, s, ss, d）から TocDepth を特定する。"""
        for depth in cls:
            if depth.locator_key == locator_key:
                return depth
        raise KeyError(locator_key)


class InlineMarkKind(Enum):
    """Sentence 内に埋め込む、location token ではない半角ASCII mark の種類。"""

    # 例: <q=ただし書>
    QUALIFIER = "q"
    # 例: <h=law:kai>, <h=part:本則>
    HINT = "h"
    # 例: <c=及び>
    CONNECTOR = "c"


class QualifierMark(Enum):
    """location に近い修飾情報。参照先の一部を限定する。"""

    PROVISO = "ただし書"
    MAIN_TEXT = "本文"
    FIRST_PART = "前段"
    LATTER_PART = "後段"


class HintMark(Enum):
    """UI / semantic hint 用の mark key。location 解決そのものからは距離がある。"""

    # 例: <h=law:kai>
    LAW = "law"
    # 例: <h=part:本則>, <h=part:附則>
    PART = "part"
    # 例: <h=term:登記簿>
    TERM = "term"


class ConnectorMark(Enum):
    """Reference 同士の連鎖を維持しうる接続語。"""

    COMMA = "、"
    OYOBI = "及び"
    NARABINI = "並びに"
    MATAWA = "又は"
    MOSHIKUWA = "若しくは"
    KARA = "から"
    MADE = "まで"


class SentenceType(Enum):
    SENTENCE = 0
    COLUMN = 1
