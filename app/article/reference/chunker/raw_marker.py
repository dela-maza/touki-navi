# app/article/reference/chunker/raw_marker.py
import re

from app.article.constants.enums import LawType
from app.article.constants.xml_tags import Subitem1Rule, Subitem2Rule


class RawReferenceMarker:
    """本文中の参照らしき最小単位を raw mark `{[...]}` にする。"""

    KANJI_NUM = "一二三四五六七八九十百千万"

    @classmethod
    def apply(cls, text: str) -> str:
        """raw mark 付与から、隣接 raw mark の結合までを行う。"""
        processed = text

        # =================================================================
        # 1. 生テキストの参照表現に、最小単位の raw mark '{[会社法]}'を付与
        # =================================================================
        for law in sorted(LawType, key=lambda l: len(l.name_jp), reverse=True):
            processed = re.sub(re.escape(law.name_jp), f"{{[{law.name_jp}]}}", processed)

        processed = processed.replace("同法", "{[同法]}")

        unit_pattern = rf"第[{cls.KANJI_NUM}]+(?:条|項|号)(?:の[{cls.KANJI_NUM}]+)*"
        processed = re.sub(unit_pattern, r"{[\g<0>]}", processed)  # \g<0> 正規表現にマッチした部分文字列全体

        # =================================================================
        # 2. 条・項・号の相対指定・複数指定 ＆ 範囲指定（前○条）
        # =================================================================
        # 例: 前条、前三条、前三項、前三号、次条、同項、各号
        relative_pattern = rf"(前[{cls.KANJI_NUM}]+[条項号]|[前次同][条項号]|各号)"
        processed = re.sub(relative_pattern, r"{[\g<0>]}", processed)

        # =================================================================
        # 3. 目・細目（イロハ・カッコ数字）
        # =================================================================
        processed = Subitem1Rule.get_pattern().sub(r"{[\g<0>]}", processed)
        processed = Subitem2Rule.get_pattern().sub(r"{[\g<0>]}", processed)

        # 4. 隣接する raw mark を、1つの参照 mark に結合
        return processed.replace("}{", "")
