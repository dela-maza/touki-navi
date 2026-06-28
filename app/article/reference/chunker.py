# app/article/reference/chunker.py
import re
from app.article.constants.enums import LawType
from app.article.common.law_utils import convert_law_numbers, to_hankaku
from app.article.constants.xml_tags import Subitem1Rule, Subitem2Rule
from app.article.constants.markers import ReferenceMarker


class ReferenceChunker:
    """
    法令の本文（センテンス）から参照表現を検出し、5要素の角括弧・波括弧フォーマットに構造化する前処理クラス。

        【パッキング規律】
        {[生テキスト(漢)] | [アラビア数字表記(全角)] | [shift] | [this_loc] | [last_ref_loc]}
        ※ センテンス内のデジタル半角文字（{}, |, []) は、100%システムが埋め込んだ制御用マーカー（メタデータ）である。

        【アラビア数字表記ルール】
        アラビア数字表記は表示用のため全角で保持する。
        shift 計算時だけ半角に変換し、計算後に表示へ戻す値とは分離する。

        【入力と出力の具体例】
        例1：表記ブレがある場合（条・項・号の絶対指定）
            入力: "会社法第百十一条の二第二項第一号"
            出力: "{[会社法][第百十一条の二][第二項][第一号]|[会社法][第１１１条の２][第２項][第１号]|||}"

        例2：表記ブレがない場合（同法、相対指定、目、細目など）
            入力: "同法前条イ（１）"
            出力: "{[同法][前条][イ][（１）]|[同法][前条][イ][（１）]|[a=-1][s1=1][s2=1]||}"
        """

    @classmethod
    def to_chunked_str(cls, text: str) -> str:
        if not text:
            return ""
        processed: str = text
        kanji_num = "一二三四五六七八九十百千万"

        # =================================================================
        # 1. 生テキストの参照表現に、最小単位の raw mark '{[会社法]}'を付与
        # =================================================================
        for law in sorted(LawType, key=lambda l: len(l.name_jp), reverse=True):
            processed = re.sub(re.escape(law.name_jp), f"{{[{law.name_jp}]}}", processed)

        processed = processed.replace("同法", "{[同法]}")

        unit_pattern = rf"第[{kanji_num}]+(?:条|項|号)(?:の[{kanji_num}]+)*"
        processed = re.sub(unit_pattern, r"{[\g<0>]}", processed)  # \g<0> 正規表現にマッチした部分文字列全体

        # =================================================================
        # 2. 条・項・号の相対指定・複数指定 ＆ 範囲指定（前○条）
        # =================================================================
        # 例: 前条、前三条、前三項、前三号、次条、同項、各号
        relative_pattern = rf"(前[{kanji_num}]+[条項号]|[前次同][条項号]|各号)"
        processed = re.sub(relative_pattern, r"{[\g<0>]}", processed)

        # =================================================================
        # 3. 目・細目（イロハ・カッコ数字）
        # =================================================================
        processed = Subitem1Rule.get_pattern().sub(r"{[\g<0>]}", processed)
        processed = Subitem2Rule.get_pattern().sub(r"{[\g<0>]}", processed)

        # 4. 隣接する raw mark を、1つの参照 mark に結合
        processed = processed.replace("}{", "")

        # 5. raw mark を5要素フォーマットに展開
        processed = re.sub(r"\{(.+?)}", cls._expand_raw_mark, processed)

        # 6. 後処理
        processed = cls._apply_affix_corrections(processed)

        return processed

    @classmethod
    def _expand_raw_mark(cls, match: re.Match) -> str:
        raw_part: str = match.group(1)  # group(1)以降の数値を指定すると順番に各グループの文字列が返される
        raw_values: list[str] = cls._split_bracket_values(raw_part)
        arabic_values: list[str] = [cls._to_arabic_value(raw) for raw in raw_values]
        arabic_part = "".join(f"[{arabic}]" for arabic in arabic_values)

        if cls._is_absolute_location(arabic_values):
            return cls._pack_reference(raw_part, arabic_part, "")

        shift_part = "".join(cls._to_shift_chunk(arabic) for arabic in arabic_values)
        return cls._pack_reference(raw_part, arabic_part, shift_part)

    @classmethod
    def _split_bracket_values(cls, bracket_part: str) -> list[str]:
        """
        :param bracket_part: '[会社法][第百十一条の二][第二項][第一号]'
        :return:['会社法','第百十一条の二','第二項','第一号']
        """

        if not bracket_part:
            return []
        return bracket_part.strip("[]").split("][")

    @classmethod
    def _pack_reference(cls, raw_part: str, arabic_part: str, shift_part: str) -> str:
        return f"{{{raw_part}|{arabic_part}|{shift_part}||}}"

    @classmethod
    def _to_arabic_value(cls, raw: str) -> str:
        """
        :param raw: [第百十一条の二]
        :return:[第１１１条の２][第２項][第１号]
        """
        return convert_law_numbers(raw)

    @classmethod
    def _to_shift_chunk(cls, arabic_part: str) -> str:
        if "条" in arabic_part and not arabic_part.startswith(("前", "同", "次")):
            return ""

        value = to_hankaku(arabic_part) # アラビア全角 -> アラビア半角

        # 各号
        if value == "各号":
            return f"[i={ReferenceMarker.EACH}]"

        # 前○条、前○項、前○号
        range_match = re.match(r"前([0-9]+)([条項号])", value)
        if range_match:
            key = cls._shift_key_by_unit(range_match.group(2))
            return f"[{key}=-{range_match.group(1)}{ReferenceMarker.RANGE_SUFFIX}]"

        # 前条
        relative_shifts = {
            "前条": "a=-1", "同条": "a=0", "次条": "a=1",
            "前項": "p=-1", "同項": "p=0", "次項": "p=1",
            "前号": "i=-1", "同号": "i=0", "次号": "i=1",
        }
        if arabic_part in relative_shifts:
            return f"[{relative_shifts[arabic_part]}]"

        # イロハ
        if Subitem1Rule.get_pattern().fullmatch(arabic_part):
            return f"[s1={Subitem1Rule.MAP.get(arabic_part, arabic_part)}]"

        # アラビア半角数字が含まれていれば、'項|号|（１）'のどれか
        number_match = re.search(r"[0-9]+", value)
        if not number_match:
            return ""

        if "項" in value:
            return f"[p={number_match.group(0)}]"

        if "号" in value:
            return f"[i={number_match.group(0)}]"

        if re.fullmatch(r"\([0-9]+\)", value):
            return f"[s2={value[1:-1]}]" # value[1:-1] : (1)-> 1

        return ""

    @staticmethod
    def _shift_key_by_unit(unit: str) -> str:
        return {
            "条": "a",
            "項": "p",
            "号": "i",
        }[unit]

    @classmethod
    def _is_absolute_location(cls, arabic_values: list[str]) -> bool:
        return any(cls._is_absolute_article(arabic) for arabic in arabic_values)

    @staticmethod
    def _is_absolute_article(arabic: str) -> bool:
        return bool(re.fullmatch(r"第[０-９]+条(?:の[０-９]+)*", arabic))

    @classmethod
    def _apply_affix_corrections(cls, text: str) -> str:
        processed = text
        affix_patterns = [
            (r"法律", r"\{.+?\}"),
            (r"官報", r"\{.+?\}"),
            (r"省令", r"\{.+?\}"),
        ]

        for prefix, target in affix_patterns:
            pattern = r"(" + prefix + r")\{(.+?)\}"
            processed = re.sub(pattern, r"\1\2", processed)

        return processed
