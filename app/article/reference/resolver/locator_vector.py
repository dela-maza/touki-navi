# app/article/reference/resolver/locator_vector.py
from dataclasses import dataclass
from typing import Tuple

from app.article.constants.markers import ReferenceMarker
from app.article.reference.resolver.token import TokenGroup


@dataclass(frozen=True)
class LocatorVector:
    """
    TokenGroup の locator を6次元で保持する計算用ベクトル。

    FullLocation ではないため、shift や range を含むことができる。
    ここでは location を確定せず、SentenceReferenceGroup が参照軸を選ぶための材料にする。
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

    @property
    def law_cell(self) -> str:
        return self.path[0]

    @property
    def article_cell(self) -> str:
        return self.path[1]

    @property
    def lower_cells(self) -> tuple[str, str, str, str]:
        return self.path[2:]

    @property
    def is_law_only(self) -> bool:
        """法典名だけの参照かを返す。"""
        return bool(self.law_cell) and not any(self.path[1:])

    @property
    def has_law_or_article(self) -> bool:
        """法典または条番号を含む、明示的な参照かを返す。"""
        return bool(self.law_cell or self.article_cell)

    @property
    def has_same_reference(self) -> bool:
        """同法・同条・同項・同号など、直前参照を明示的に引く記号を含むかを返す。"""
        return self.law_cell == ReferenceMarker.SAME_LAW or any(cell == "+0" for cell in self.path)

    @property
    def has_shift(self) -> bool:
        """前条・次項など、起点からの移動を含むかを返す。"""
        return any(cell.startswith(("+", "-")) for cell in self.path if cell)

    @property
    def is_part_only(self) -> bool:
        """法典・条を持たず、項以下だけで構成される参照かを返す。"""
        return not self.law_cell and not self.article_cell and any(self.lower_cells)

    @property
    def is_plain_part_only(self) -> bool:
        """項以下だけで、同・前・次・range を含まない参照かを返す。"""
        if not self.is_part_only:
            return False
        for cell in self.lower_cells:
            if not cell:
                continue
            if cell.startswith(("+", "-")) or cell.endswith(ReferenceMarker.RANGE_SUFFIX):
                return False
        return True

    @classmethod
    def _index_by_locator_key(cls, locator_key: str) -> int:
        return cls._locator_key_index()[locator_key]

    @staticmethod
    def _locator_key_index() -> dict[str, int]:
        return {
            "l": 0,
            "a": 1,
            "p": 2,
            "i": 3,
            "s1": 4,
            "s2": 5,
        }
