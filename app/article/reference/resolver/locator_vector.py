# app/article/reference/resolver/locator_vector.py
from dataclasses import dataclass
from typing import Tuple

from app.article.constants.markers import ReferenceMarker
from app.article.models.article_loc import AbsoluteArticleLocation


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
    def from_tokens(cls, tokens: list) -> "LocatorVector":
        """Token の並びが持つ locator_key / locator_value を6次元 path に配置する。"""
        path = ["", "", "", "", "", ""]
        for token in tokens:
            # token.locator_key -> 0, 1, 2, 3, 4, 5
            index = cls._index_by_locator_key(token.locator_key)
            path[index] = token.locator_value
        return cls(path=tuple(path))

    def merge(self, base_location: AbsoluteArticleLocation) -> "LocatorVector":
        """
        base_location と self.path を合成し、まだ確定 location に畳まない LocatorVector を返す。

        locator が現れた階層より左側は base_location から継承し、
        locator が現れた階層より右側の空欄は 0 に落とす。
        shift / range は、後段の index 解決に渡せる形で vector 内に残す。
        """
        first_locator_index = self._first_locator_index()
        if first_locator_index is None:
            return LocatorVector(path=base_location.path)

        merged_path: list[str] = []
        for index, locator_cell in enumerate(self.path):
            base_cell = base_location.path[index]

            if not locator_cell:
                merged_path.append(base_cell if index < first_locator_index else "0")
                continue

            merged_path.append(self._merge_cell(base_cell, locator_cell))

        return LocatorVector(path=tuple(merged_path))

    # def deploy_locations(self) -> list[AbsoluteArticleLocation]:
    #     """
    #     確定済みの LocatorVector を AbsoluteArticleLocation の list に展開する。
    #
    #     range / each / shift range が残っている vector は、まだ index 解決前なのでここでは展開しない。
    #     """
    #     if self._has_unresolved_range_cell():
    #         raise ValueError(f"LocatorVector contains unresolved range cell: {self.path}")
    #
    #     return [AbsoluteArticleLocation(path=self.path)]

    @property
    def law_cell(self) -> str:
        return self.path[0]

    @property
    def article_cell(self) -> str:
        return self.path[1]

    @property
    def inner_cells(self) -> tuple[str, str, str, str]:
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
    def is_inner_only(self) -> bool:
        """法典・条を持たず、項以下だけで構成される参照かを返す。"""
        return not self.law_cell and not self.article_cell and any(self.inner_cells)

    @property
    def is_plain_inner_only(self) -> bool:
        """項以下だけで、同・前・次・range を含まない参照かを返す。"""
        if not self.is_inner_only:
            return False
        for cell in self.inner_cells:
            if not cell:
                continue
            if cell.startswith(("+", "-")) or cell.endswith(ReferenceMarker.RANGE_SUFFIX):
                return False
        return True

    @classmethod
    def _index_by_locator_key(cls, locator_key: str) -> int:
        return cls._locator_key_index()[locator_key]

    def _first_locator_index(self) -> int | None:
        """self.path のうち、最初に locator 成分が入っている index を返す。"""
        for index, cell in enumerate(self.path):
            if cell:
                return index
        return None

    def _has_unresolved_range_cell(self) -> bool:
        """index なしでは AbsoluteArticleLocation に展開できない range 成分が残っているかを返す。"""
        for cell in self.path:
            if cell == ReferenceMarker.RANGE_SUFFIX:
                return True
            if cell.endswith(ReferenceMarker.RANGE_SUFFIX):
                return True
        return False

    @classmethod
    def _merge_cell(cls, base_cell: str, locator_cell: str) -> str:
        """
        base の1成分と locator の1成分を合成する。

        loc は locator_cell を優先し、shift は base_cell との関係を保持する。
        """
        if locator_cell == ReferenceMarker.SAME_LAW:
            return base_cell

        if locator_cell == ReferenceMarker.RANGE_SUFFIX:
            return locator_cell

        if cls._is_shift_range_cell(locator_cell):
            return f"{base_cell}:{locator_cell}"

        if cls._is_shift_cell(locator_cell):
            return cls._merge_shift_cell(base_cell, locator_cell)

        return locator_cell

    @staticmethod
    def _is_shift_cell(cell: str) -> bool:
        """+1 / -1 / +0 のような shift 成分かを返す。"""
        return cell.startswith(("+", "-"))

    @classmethod
    def _is_shift_range_cell(cls, cell: str) -> bool:
        """-3* のような shift range 成分かを返す。"""
        return cls._is_shift_cell(cell) and cell.endswith(ReferenceMarker.RANGE_SUFFIX)

    @classmethod
    def _merge_shift_cell(cls, base_cell: str, locator_cell: str) -> str:
        """数値として足せる shift は足し、枝番などは後段用に base:shift 形式で残す。"""
        try:
            return str(int(base_cell) + int(locator_cell))
        except ValueError:
            return f"{base_cell}:{locator_cell}"

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
