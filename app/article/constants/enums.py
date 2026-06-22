# constants/enums.py
from enum import Enum

class LawType(Enum):
    KAI = ("kai", "会社法")
    SHOU = ("syou", "商法")
    SHOU_TOU = ("shoutou", "商業登記法")
    SHOU_TOU_KI = ("shoutouki", "商業登記規則")

    def __init__(self, short_name, name_jp):
        self.short_name = short_name
        self.name_jp = name_jp

class ArticleDepth(Enum):
    # (インデックス, 短縮名, タグ名, 日本語名)
    PARAGRAPH  = (0, "p",   "Paragraph", "項")
    ITEM       = (1, "i",   "Item",      "号")
    SUB_ITEM_1 = (2, "si1", "Subitem1",  "目")
    SUB_ITEM_2 = (3, "si2", "Subitem2",  "目")

    def __init__(self, index, short_name, tag_name, label_jp):
        self.index = index
        self.short_name = short_name # p, i, si1, si2
        self.tag_name = tag_name     # Paragraph...
        self.label_jp = label_jp     # 項, 号...

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