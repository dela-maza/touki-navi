# models/toc_loc.py
from enum import Enum
from dataclasses import dataclass
from bs4.element import Tag


class TocDepth(Enum):
    # (内部数値, 本文用タグ名, 目次用タグ名, 日本語名)
    PART = (0, "Part", "TOCPart", "編")
    CHAPTER = (1, "Chapter", "TOCChapter", "章")
    SECTION = (2, "Section", "TOCSection", "節")
    SUB_SECTION = (3, "Subsection", "TOCSubsection", "款")
    DIVISION = (4, "Division", "TOCDivision", "目")

    def __init__(self, index, body_tag, toc_tag, label_jp):
        self.index = index
        self.body_tag = body_tag
        self.toc_tag = toc_tag
        self.label_jp = label_jp

    @property
    def value_index(self) -> int:
        return self.index

    @classmethod
    def from_toc_tag(cls, tag_name: str):
        """TOCChapter 等のタグ名から Enum を特定する"""
        for depth in cls:
            if depth.toc_tag == tag_name:
                return depth
        return None

    @classmethod
    def from_index(cls, index: int):
        """数値(0-4)から該当するEnumを返す"""
        for depth in cls:
            if depth.index == index:
                return depth
        return None

    @classmethod
    def from_body_tag(cls, tag_name: str):
        """Chapter 等の本文タグ名から Enum を特定する"""
        for depth in cls:
            if depth.body_tag == tag_name:
                return depth
        return None


@dataclass(frozen=True)
class TocLocation:
    # パス自体は文字列のタプル（書き換え不可）
    path: tuple[str, str, str, str, str] = ("0", "0", "0", "0", "0")

    @classmethod
    def from_article_node(cls, article_node: Tag) -> "TocLocation":
        temp_path = ["0"] * 5
        current = article_node.parent

        while current is not None:
            # TocDepth.from_body_tag などを使って判定
            depth = TocDepth.from_body_tag(current.name)
            if depth:
                # Enumの index (0〜4) を使ってパスを埋める
                temp_path[depth.index] = current.get("Num", "0")
            current = current.parent

        return cls(tuple(temp_path))

    def set_at(self, depth: TocDepth, value: str) -> "TocLocation":
        new_path = list(self.path)
        new_path[depth.index] = value

        # 下位リセット（ここがこのクラスの肝ですね！）
        for i in range(depth.index + 1, 5):
            new_path[i] = "0"

        return TocLocation(tuple(new_path))

    @property
    def addr(self) -> str:
        return ".".join(self.path)