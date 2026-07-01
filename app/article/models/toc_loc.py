# app/article/models/toc_loc.py
from dataclasses import dataclass

from app.article.constants.enums import LawType, TocDepth


@dataclass(frozen=True)
class TocLocation:
    """
    法典内の目次上の相対住所。

    part.chapter.section.sub_section.division の5枠を固定で持つ。
    編を持たない法典では、先頭の part 枠は "0" のままになる。
    """

    path: tuple[str, str, str, str, str] = ("0", "0", "0", "0", "0")

    def get_path_index(self, depth: TocDepth) -> str:
        """指定されたTOC階層の現在値を取得する。"""
        return self.path[depth.index]

    def set_at(self, depth: TocDepth, value: str) -> "TocLocation":
        """指定TOC階層に値を入れ、それより下位の階層をリセットする。"""
        path_list = list(self.path)
        path_list[depth.index] = str(value)

        for index in range(depth.index + 1, len(path_list)):
            path_list[index] = "0"

        return TocLocation(path=tuple(path_list))

    @property
    def depth(self) -> TocDepth | None:
        """現在値が入っている最下層のTOC階層を返す。"""
        for index in range(len(self.path) - 1, -1, -1):
            if self.path[index] != "0":
                return TocDepth.from_index(index)
        return None

    @property
    def addr(self) -> str:
        """part.chapter.section.sub_section.division 形式の文字列を返す。"""
        return ".".join(self.path)


@dataclass(frozen=True)
class FullTocLocation:
    """法典情報を含むTOC上の絶対住所。"""

    law_type: LawType
    relative_loc: TocLocation

    def update_relative(self, depth: TocDepth, value: str) -> "FullTocLocation":
        """指定TOC階層を更新した新しい FullTocLocation を返す。"""
        return FullTocLocation(
            law_type=self.law_type,
            relative_loc=self.relative_loc.set_at(depth, value),
        )

    @property
    def id_attr(self) -> str:
        """law.short_name と TocLocation.addr を連結した純粋なTOC座標文字列を返す。"""
        return f"{self.law_type.short_name}.{self.relative_loc.addr}"

    def to_dict(self) -> dict:
        return {
            "law_short_name": self.law_type.short_name,
            "law_name_jp": self.law_type.name_jp,
            "relative_loc": self.relative_loc.addr,
            "id_attr": self.id_attr,
        }
