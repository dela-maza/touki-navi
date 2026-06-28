# app.article.reference.resolver.token.py
import re
from abc import ABC, abstractmethod

from app.article.common.law_utils import to_hankaku
from app.article.constants.enums import LawType
from app.article.constants.markers import ReferenceMarker
from app.article.constants.xml_tags import Subitem1Rule, Subitem2Rule
from app.article.models.article_loc import ArticleDepth, FullLocation
from app.article.models.law import LawLibrary


class TokenBase(ABC):
    """
    TokenGroup が扱う最小単位の共通インターフェイス。

    Token は AbsoluteToken または ShiftToken のどちらかであり、同時に両方にはならない。
    AbsoluteToken は起点なしで location に反映できる単位、
    ShiftToken は this_location / last_ref_location という起点があって初めて反映できる単位である。
    """

    def __init__(self, key: str, raw: str, arabic: str):
        self.key = key
        self.raw = raw
        self.arabic = arabic

    @abstractmethod
    def apply_to(self, location: FullLocation) -> FullLocation:
        """この Token を location に反映した新しい FullLocation を返す。"""

    @property
    def label(self) -> str:
        """旧実装の呼び出し名を残しつつ、表示用には raw を返す。"""
        return self.raw

    @property
    def tag(self) -> str:
        """旧実装の呼び出し名を残しつつ、新しい key を返す。"""
        return self.key


class AbsoluteToken(TokenBase):
    """
    起点なしで location に反映できる Token。

    例:
        [会社法] -> law=kai
        [第１条] -> a=1
        [第１項] -> p=1
        [第１号] -> i=1
    """

    def __init__(self, key: str, value: str, raw: str, arabic: str):
        super().__init__(key, raw, arabic)
        self.value = value

    def apply_to(self, location: FullLocation) -> FullLocation:

        # 法典名・条番号
        if self.key == "law":
            return location.update_law(self.value)
        if self.key == "a":
            return location.update_article(self.value)

        # 項以下
        depth = self.get_article_depth()
        return location.update_relative(depth, self.value)

    def get_article_depth(self) -> ArticleDepth:
        return _key_to_depth(self.key)


class ShiftToken(TokenBase):
    """
    起点 location があって初めて反映できる Token。

    例:
        [p=1] -> 起点 location の第1項
        [i=-1] -> 起点 location の前号
        [a=-3_range] -> 起点 location から前三条
    """

    def __init__(self, key: str, offset: str, raw: str, arabic: str):
        super().__init__(key, raw, arabic)
        self.offset = offset
        self.offset_num, self.offset_suffix = self._parse_offset(offset)
        self.resolved_ids: list[str] | None = None

    def apply_to(self, location: FullLocation) -> FullLocation:
        # ShiftToken の location 適用は TokenGroup の責務。
        return location

    def get_article_depth(self) -> ArticleDepth:
        return _key_to_depth(self.key)

    @staticmethod
    def _parse_offset(offset: str) -> tuple[int | None, str]:
        """
        :param offset: '-3_range'
        :return: (-3, 'range')
        """

        # 'each'
        if offset == ReferenceMarker.EACH:
            return None, ReferenceMarker.EACH  # (None, "each")

        # '-3_range'
        suffix = ""
        value = offset  # '-3_range'
        if value.endswith(ReferenceMarker.RANGE_SUFFIX):
            suffix = ReferenceMarker.RANGE_SUFFIX  # 'range'
            value = value.removesuffix(ReferenceMarker.RANGE_SUFFIX)  # '-3'

        try:
            return int(value), suffix
        except ValueError as e:
            raise ValueError(f"invalid shift offset: {offset}") from e

class TokenGroup:
    """
    1つの reference mark を分解し、TokenUnit から location を組み立てるレイヤ。

    TokenGroup は this_location と last_ref_location の二軸を保持する。
    this_location は現在処理中の条文自身を起点に計算した location、
    last_ref_location は直前の参照条文を起点に計算した location である。

    ただし、このクラスはどちらの location が実在するか、またはリンクとして採用されるかを判断しない。
    その判断は DB 照会を行う上位レイヤの責務である。
    """

    def __init__(self, raw_segment: str,
                 this_location: FullLocation, last_ref_location: FullLocation):
        self.raw_segment = raw_segment

        raw_part, arabic_part, shift_part, this_loc_part, last_ref_loc_part = self._split_segment(raw_segment)
        self.raw_units: list[str] = self._split_bracket_values(raw_part)
        self.arabic_units: list[str] = self._split_bracket_values(arabic_part)
        self.shift_units: list[str] = self._split_bracket_values(shift_part)
        self.this_loc_part = this_loc_part
        self.last_ref_loc_part = last_ref_loc_part

        self.absolute_tokens: list[AbsoluteToken] = self._create_absolute_tokens()
        self.shift_tokens: list[ShiftToken] = self._create_shift_tokens()
        self.tokens: list[TokenBase] = [*self.absolute_tokens, *self.shift_tokens]

        self.this_location: FullLocation = self._build_location(this_location)
        self.last_ref_location: FullLocation = self._build_location(last_ref_location)
        self.final_last_ref: FullLocation = self.last_ref_location

        # 旧呼び出し名との互換用。main.py の整理時に削除する。
        self.location_via_this: FullLocation = self.this_location
        self.location_via_ref: FullLocation = self.last_ref_location

    @classmethod
    def _split_segment(cls, raw_segment: str) -> tuple[str, str, str, str, str]:
        elements = raw_segment.strip("{}").split("|")
        if len(elements) != 5:
            raise ValueError(f"reference mark must have 5 fields: {raw_segment}")
        return tuple(elements)  # type: ignore[return-value]

    @classmethod
    def _split_bracket_values(cls, bracket_part: str) -> list[str]:
        if not bracket_part:
            return []
        return bracket_part.strip("[]").split("][")

    def _create_absolute_tokens(self) -> list[AbsoluteToken]:
        tokens: list[AbsoluteToken] = []
        for raw, arabic in zip(self.raw_units, self.arabic_units):
            token = self._create_absolute_token(raw, arabic)
            if token:
                if self.shift_units and token.key != "law":
                    continue
                tokens.append(token)
        return tokens

    def _create_absolute_token(self, raw: str, arabic: str) -> AbsoluteToken | None:
        law = _find_law_type(arabic)
        if law:
            return AbsoluteToken("law", law.short_name, raw, arabic)

        if arabic == "同法":
            return None

        value = to_hankaku(arabic)

        article_match = re.fullmatch(r"第([0-9]+)条(?:の([0-9]+))*", value)
        if article_match:
            return AbsoluteToken("a", _unit_number_to_id(value), raw, arabic)

        paragraph_match = re.fullmatch(r"第([0-9]+)項", value)
        if paragraph_match:
            return AbsoluteToken("p", paragraph_match.group(1), raw, arabic)

        item_match = re.fullmatch(r"第([0-9]+)号", value)
        if item_match:
            return AbsoluteToken("i", item_match.group(1), raw, arabic)

        if Subitem1Rule.get_pattern().fullmatch(arabic):
            return AbsoluteToken("s1", Subitem1Rule.MAP.get(arabic, arabic), raw, arabic)

        if Subitem2Rule.get_pattern().fullmatch(arabic):
            return AbsoluteToken("s2", Subitem2Rule.to_id(arabic), raw, arabic)

        return None

    def _create_shift_tokens(self) -> list[ShiftToken]:
        tokens: list[ShiftToken] = []
        for shift in self.shift_units:
            key, offset = shift.split("=", 1)
            raw, arabic = self._find_unit_for_shift(key, offset)
            tokens.append(ShiftToken(key, offset, raw, arabic))
        return tokens

    def _find_unit_for_shift(self, key: str, offset: str) -> tuple[str, str]:
        for raw, arabic in zip(self.raw_units, self.arabic_units):
            value = to_hankaku(arabic)
            if key == "a" and "条" in value:
                return raw, arabic
            if key == "p" and "項" in value:
                return raw, arabic
            if key == "i" and "号" in value:
                return raw, arabic
            if key == "s1" and Subitem1Rule.get_pattern().fullmatch(arabic):
                return raw, arabic
            if key == "s2" and re.fullmatch(r"\([0-9]+\)", value):
                return raw, arabic
        return "", ""

    def _build_location(self, base_location: FullLocation) -> FullLocation:
        current_location = base_location
        for token in self.tokens:
            if isinstance(token, ShiftToken):
                current_location = self._apply_shift_token(current_location, token)
                continue
            current_location = token.apply_to(current_location)
        return current_location

    def _apply_shift_token(self, location: FullLocation, token: ShiftToken) -> FullLocation:
        if token.key == "a":
            return self._apply_article_shift(location, token)

        if token.offset_num is None:
            return location

        depth = token.get_article_depth()

        if token.offset_num == 0:
            current_val = location.relative_loc.get_path_index(depth)
            return location.update_relative(depth, current_val)

        if token.offset_num in (-1, 1):
            current_val = location.relative_loc.get_path_index(depth)
            next_val = self._calculate_sibling_num(current_val, token.offset_num)
            return location.update_relative(depth, next_val)

        return location.update_relative(depth, str(token.offset_num))

    def _apply_article_shift(self, location: FullLocation, token: ShiftToken) -> FullLocation:
        if token.offset_num is None:
            return location

        if token.offset_num == 0:
            return location.update_article(location.article_num)

        if token.offset_suffix == ReferenceMarker.RANGE_SUFFIX:
            return self._move_article_by_index(location, token, offset=token.offset_num, length=abs(token.offset_num))

        if token.offset_num in (-1, 1):
            return self._move_article_by_index(location, token, offset=token.offset_num, length=1)

        raise ValueError(f"unexpected article shift offset: {token.offset}")

    def _move_article_by_index(
            self, location: FullLocation, token: ShiftToken, offset: int, length: int) -> FullLocation:
        try:
            index = LawLibrary.get_index(location.law_type)
        except (ValueError, AttributeError):
            return location

        target_ids = index.get_offset_ids(location.article_num, offset, length)
        if not target_ids:
            return location

        if length > 1:
            token.resolved_ids = target_ids

        return location.update_article(target_ids[-1])

    @staticmethod
    def _calculate_sibling_num(current_val: str, offset: int) -> str:
        if not current_val or current_val == "0":
            return "1"
        if current_val.isdigit():
            return str(max(1, int(current_val) + offset))

        parts = current_val.split("_")
        if parts[-1].isdigit():
            parts[-1] = str(max(1, int(parts[-1]) + offset))
            return "_".join(parts)
        return current_val

    def to_resolved_string(self) -> str:
        """
        2つの座標軸のID（id_attr）をデータ属性として埋め込んだ
        曖昧さ対応のデバッグ用マークアップを生成する。
        """
        original_text = "".join(self.raw_units)

        id_cur = self.this_location.id_attr
        id_ref = self.last_ref_location.id_attr

        is_ambiguous = (id_cur != id_ref)
        border_color = "#e74c3c" if is_ambiguous else "#f39c12"
        bg_color = "#fdf2e9" if is_ambiguous else "#fffdf0"

        debug_info = f"cur:[{id_cur}] | ref:[{id_ref}]" if is_ambiguous else f"[{id_cur}]"

        return (
            f'<span class="resolved-link-debug" '
            f'data-id-cur="{id_cur}" '
            f'data-id-ref="{id_ref}" '
            f'style="border: 1px solid {border_color}; padding: 0 4px; border-radius: 4px; background: {bg_color}; cursor: help;" '
            f'title="{debug_info}">'
            f'{original_text}'
            f'<span style="color: #e67e22; font-family: monospace; font-weight: bold; margin-left: 8px;">'
            f'[{debug_info}]'
            f'</span>'
            f'</span>'
        )

    def to_resolved_string_with_options(self) -> str:
        """main.py が旧名を呼んでいる間の互換メソッド。"""
        return self.to_resolved_string()


def _find_law_type(value: str) -> LawType | None:
    for law in LawType:
        if value == law.name_jp:
            return law
    return None


def _key_to_depth(key: str) -> ArticleDepth:
    mapping = {
        "p": ArticleDepth.PARAGRAPH,
        "i": ArticleDepth.ITEM,
        "s1": ArticleDepth.SUB_ITEM_1,
        "s2": ArticleDepth.SUB_ITEM_2,
    }
    return mapping[key]


def _unit_number_to_id(value: str) -> str:
    content = re.sub(r"[第条項号]", "", value)
    return "_".join(part for part in content.split("の") if part)
