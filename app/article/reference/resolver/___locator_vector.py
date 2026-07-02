# app/article/reference/resolver/locator_vector.py
from dataclasses import dataclass
from typing import Tuple

from app.article.constants.markers import ReferenceMarker
from app.article.models.article_loc import AbsoluteArticleLocation
from app.article.reference.resolver.token import TokenGroup


@dataclass(frozen=True)
class LocatorVector:
    """
    locator を6次元で保持する計算用ベクトル。

    FullLocation ではないため、shift や range を含むことができる。
    FullLocation.path と次元を合わせ、上層レイヤで合成してから最終的な location 解決へ進む。
    """

    path: Tuple[str, str, str, str, str, str] = ("", "", "", "", "", "")

    def __post_init__(self) -> None:
        if len(self.path) != 6:
            raise ValueError(f"LocatorVector.path must have 6 elements: {self.path}")
        object.__setattr__(self, "path", tuple(str(cell) for cell in self.path))

    @classmethod
    def from_token_group(cls, token_group: TokenGroup) -> "LocatorVector":
        """TokenGroup が持つ locator_key / locator_value を6次元 path に配置する。"""
        path = ["", "", "", "", "", ""]
        for token in token_group.tokens:
            index = cls._index_by_locator_key(token.locator_key)
            path[index] = token.locator_value
        return cls(path=tuple(path))

    def merge_base_location(self, base_location: AbsoluteArticleLocation) -> "LocatorVector":
        """
        base_location.path とこの LocatorVector.path を合成し、より具体化した LocatorVector を返す。

        空セルは、まだ locator が出現していない間だけ base の値を引き継ぐ。
        一度 locator が出現した後の空セルは、下位座標リセットとして "0" を入れる。
        """
        base_path = base_location.path
        merged: list[str] = []
        locator_started = False
        spread_count = 0

        for base_cell, locator_cell in zip(base_path, self.path):
            if not locator_cell:
                merged.append(base_cell if not locator_started else "0")
                continue

            locator_started = True
            merged_cell = self._merge_cell(base_cell, locator_cell)
            if self._is_spread_cell(merged_cell):
                spread_count += 1
                if spread_count > 1:
                    raise ValueError(f"LocatorVector cannot contain multiple spread cells: {self.path}")
            merged.append(merged_cell)

        return LocatorVector(path=tuple(merged))

    @classmethod
    def _index_by_locator_key(cls, locator_key: str) -> int:
        return cls._locator_key_index()[locator_key]

    @classmethod
    def _locator_key_index(cls) -> dict[str, int]:
        return {
            "l": 0,
            "a": 1,
            "p": 2,
            "i": 3,
            "s1": 4,
            "s2": 5,
        }

    @classmethod
    def _merge_cell(cls, base_cell: str, locator_cell: str) -> str:
        if locator_cell == ReferenceMarker.SAME_LAW:
            return base_cell

        if locator_cell == ReferenceMarker.RANGE_SUFFIX:
            return locator_cell

        if locator_cell.endswith(ReferenceMarker.RANGE_SUFFIX):
            offset = int(locator_cell.removesuffix(ReferenceMarker.RANGE_SUFFIX))
            return cls._create_shift_range_cell(base_cell, offset)

        if locator_cell.startswith(("+", "-")):
            return str(int(base_cell) + int(locator_cell))

        return locator_cell

    @staticmethod
    def _create_shift_range_cell(base_cell: str, offset: int) -> str:
        return f"{base_cell}:{offset}{ReferenceMarker.RANGE_SUFFIX}"

    @staticmethod
    def _is_spread_cell(cell: str) -> bool:
        return cell == ReferenceMarker.RANGE_SUFFIX or cell.endswith(ReferenceMarker.RANGE_SUFFIX)
