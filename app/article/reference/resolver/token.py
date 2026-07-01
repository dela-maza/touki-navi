# app.article.reference.resolver.token.py
import logging
from dataclasses import dataclass

from app.article.constants.markers import ReferenceMarker

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Token:
    """locator の1セルを表す最小単位。"""

    locator_key: str
    locator_value: str

    @classmethod
    def create_object(cls, locator_cell: str) -> "Token":
        """locator cell（例: 'p=-3*'）から Token を生成する。"""
        try:
            locator_key, locator_value = locator_cell.split("=", 1)
        except ValueError as e:
            raise ValueError(f"invalid locator cell: {locator_cell}") from e

        if not locator_key or not locator_value:
            raise ValueError(f"invalid locator cell: {locator_cell}")

        return cls(locator_key=locator_key, locator_value=locator_value)

    @property
    def is_range(self) -> bool:
        """各号など、起点配下へ拡散する range token かを返す。"""
        return self.locator_value == ReferenceMarker.RANGE_SUFFIX

    @property
    def is_shift_range(self) -> bool:
        """前三項など、起点から一定方向へ拡散する shift range token かを返す。"""
        return self.locator_value.endswith(ReferenceMarker.RANGE_SUFFIX) and not self.is_range

    @property
    def is_range_like(self) -> bool:
        """拡散を発生させる token かを返す。"""
        return self.is_range or self.is_shift_range


@dataclass
class TokenGroup:
    """
    1つの reference mark から生成された Token のまとまり。

    TokenGroup は Token の連続性と順序を保持するだけで、location を確定しない。
    this_sentence_location / last_ref_location の二軸からの location 計算、shift の解決、リンク切れ判定は
    ArticleIndex や Article 内 Index を参照できる上位 Resolver 層の責務である。

    ただし、range token は TokenGroup の末尾でなければならない。
    一度拡散した座標がさらに移動する参照は、技術的に解ける可能性があっても、
    法文の読者が座標を追えない異常な参照表現として扱う。
    """

    tokens: list[Token]

    def __post_init__(self) -> None:
        self._validate_token_order()

    @classmethod
    def create_object(cls, locator: str) -> "TokenGroup":
        """locator part（例: '[l=kai][a=1][p=-1]'）から TokenGroup を生成する。"""
        if not locator:
            return cls(tokens=[])

        locator_cells = locator.strip("[]").split("][")
        return cls(tokens=[Token.create_object(locator_cell) for locator_cell in locator_cells])

    @property
    def range_tokens(self) -> list[Token]:
        return [token for token in self.tokens if token.is_range]

    @property
    def shift_range_tokens(self) -> list[Token]:
        return [token for token in self.tokens if token.is_shift_range]

    def _validate_token_order(self) -> None:
        """
        Token の並びとして異様なものを警告する。

        range token は参照の末尾に出るのが通常であり、その後にさらに Token が続く場合はログに残す。
        これは「前三項第一号」のように、拡散後の各座標をさらに移動させる表現を検知するためである。
        """
        for index, token in enumerate(self.tokens):
            if token.is_range_like and index != len(self.tokens) - 1:
                logger.warning(
                    "range token should be last in TokenGroup: tokens=%s",
                    [t.locator_value for t in self.tokens],
                )

        range_like_count = len([token for token in self.tokens if token.is_range_like])
        if range_like_count > 1:
            logger.warning(
                "multiple range tokens may expand locations repeatedly: tokens=%s",
                [t.locator_value for t in self.tokens],
            )
