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

class ArticleDepth(Enum):
    PARAGRAPH = (0, "p", "Paragraph", "項")
    ITEM = (1, "i", "Item", "号")
    SUB_ITEM_1 = (2, "s1", "Subitem1", "目")
    SUB_ITEM_2 = (3, "s2", "Subitem2", "細目")

    def __init__(self, index: int, short_name: str, tag_name: str, label_jp: str):
        self.index = index
        self.short_name = short_name
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

class SentenceType(Enum):
    SENTENCE = 0
    COLUMN = 1
