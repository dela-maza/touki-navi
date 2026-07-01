# app/article/reference/chunker/locator.py
import re

from app.article.common.law_utils import to_hankaku
from app.article.constants.enums import LawType
from app.article.constants.markers import ReferenceMarker
from app.article.constants.xml_tags import Subitem1Rule


class ReferenceLocator:
    """アラビア数字化された参照セルを locator 表現へ変換する。"""

    @classmethod
    def to_locator_part(cls, arabic_values: list[str]) -> str:
        return "".join(cls._to_locator_chunk(arabic) for arabic in arabic_values)

    @classmethod
    def _to_locator_chunk(cls, arabic_part: str) -> str:
        value = to_hankaku(arabic_part)

        if arabic_part == "同法":
            return f"[l={ReferenceMarker.SAME_LAW}]"

        law = cls._find_law_type(arabic_part)
        if law:
            return f"[l={law.short_name}]"

        # 各号
        if value == "各号":
            return f"[i={ReferenceMarker.RANGE_SUFFIX}]"

        # 前○条、前○項、前○号
        range_match = re.match(r"前([0-9]+)([条項号])", value)
        if range_match:
            # [条|項|号] ->  locator_key = [a|p|i]
            locator_key: str = cls._locator_key_by_unit(range_match.group(2))
            # '前三号' -> 'i=-3*'
            return f"[{locator_key}=-{range_match.group(1)}{ReferenceMarker.RANGE_SUFFIX}]"

        # 前条項号・同条項号・次条項号
        relative_shifts = {
            "前条": "a=-1", "同条": "a=+0", "次条": "a=+1",
            "前項": "p=-1", "同項": "p=+0", "次項": "p=+1",
            "前号": "i=-1", "同号": "i=+0", "次号": "i=+1",
        }
        if value in relative_shifts:
            return f"[{relative_shifts[value]}]"

        article_match = re.fullmatch(r"第([0-9]+)条(?:の([0-9]+))*", value)
        if article_match:
            return f"[a={cls._unit_number_to_id(value)}]"

        number_match = re.search(r"[0-9]+", value)
        if "項" in value and number_match:
            return f"[p={number_match.group(0)}]"

        if "号" in value and number_match:
            return f"[i={number_match.group(0)}]"

        if Subitem1Rule.get_pattern().fullmatch(value):
            return f"[s1={Subitem1Rule.MAP[value]}]"

        if re.fullmatch(r"\([0-9]+\)", value):
            return f"[s2={value[1:-1]}]"

        return ""

    @staticmethod
    def _locator_key_by_unit(unit: str) -> str:
        return {
            "条": "a",
            "項": "p",
            "号": "i",
        }[unit]

    @staticmethod
    def _find_law_type(value: str) -> LawType | None:
        for law in LawType:
            if value == law.name_jp:
                return law
        return None

    @staticmethod
    def _unit_number_to_id(value: str) -> str:
        content = re.sub(r"[第条項号]", "", value)
        return "_".join(part for part in content.split("の") if part)
