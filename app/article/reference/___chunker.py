# app/article/reference/chunker.py
import re
from app.article.constants.enums import LawType
from app.article.common.law_utils import convert_law_numbers, to_hankaku
from app.article.constants.xml_tags import SEMANTIC_MARK_MAP, Subitem1Rule, Subitem2Rule
from app.article.constants.markers import ReferenceMarker


class ReferenceChunker:
    """
    法令の本文（センテンス）から参照表現を検出し、3要素の角括弧・波括弧フォーマットに構造化する前処理クラス。

        【パッキング規律】
        {[生テキスト(第一条)] | [アラビア数字表記全角（第１条)] | [locator]}
        ※ センテンス内のデジタル半角文字（{}, |, []) は、100%システムが埋め込んだ制御用マーカー（メタデータ）である。

        【アラビア数字表記ルール】
        アラビア数字表記は表示用のため全角で保持する。
        locator 計算時だけ半角に変換し、計算後に表示へ戻す値とは分離する。

        【入力と出力の具体例】
        例1：表記ブレがある場合
            入力: "会社法第百十一条の二第二項第一号"
            出力: "{[会社法][第百十一条の二][第二項][第一号]|[会社法][第１１１条の２][第２項][第１号]|[l=kai][a=111_2][p=2][i=1]}"

        例2：表記ブレがない場合（同法、相対指定、目、細目など）
            入力: "同法前条イ（１）"
            出力: "{[同法][前条][イ][（１）]|[同法][前条][イ][（１）]|[l=same_law][a=-1][s1=1][s2=1]}"
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

        # 5. raw mark を3要素フォーマットに展開
        processed = re.sub(r"\{(.+?)}", cls._expand_raw_mark, processed)

        # 6. 後処理
        processed = cls._apply_affix_corrections(processed)
        processed = cls._apply_semantic_marks(processed)

        return processed

    @classmethod
    def _expand_raw_mark(cls, match: re.Match) -> str:
        """

        :param match: "{[会社法][第百十一条の二][第二項][第一号]}"
        :return:
        """
        # group(1)以降の数値を指定すると順番に各グループの文字列が返される
        raw_part: str = match.group(1)
        # '[会社法][第百十一条の二][第二項][第一号]' -> ['会社法','第百十一条の二','第二項','第一号']
        raw_values: list[str] = cls._split_bracket_values(raw_part)
        # ['会社法','第百十一条の二','第二項','第一号'] -> ['会社法','第１１１条の２','第２項','第１号']
        arabic_values: list[str] = [cls._to_arabic_value(raw) for raw in raw_values]
        # ['会社法','第１１１条の２','第２項','第１号'] -> '[会社法][第１１１条の２][第２項][第１号]'
        arabic_part = "".join(f"[{arabic}]" for arabic in arabic_values)

        locator_part = cls._to_locator_part(arabic_values)
        return cls._pack_reference(raw_part, arabic_part, locator_part)

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
    def _pack_reference(cls, raw_part: str, arabic_part: str, locator_part: str) -> str:
        return f"{{{raw_part}|{arabic_part}|{locator_part}}}"

    @classmethod
    def _to_arabic_value(cls, raw: str) -> str:
        """
        :param raw: '第百十一条の二'
        :return:'第１１１条の２'
        """
        return convert_law_numbers(raw)

    @classmethod
    def _to_locator_part(cls, arabic_values: list[str]) -> str:
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

    @classmethod
    def _apply_semantic_marks(cls, text: str) -> str:
        """location ではないが意味を持つ語を <kind=value> で mark する。"""
        processed = text
        placeholders: list[tuple[str, str]] = []

        for index, (raw_text, meta) in enumerate(
                sorted(SEMANTIC_MARK_MAP.items(), key=lambda item: len(item[0]), reverse=True)
        ):
            placeholder = f"@@SEMANTIC_MARK_{index}@@"
            mark = cls._pack_inline_mark(meta)
            processed = re.sub(re.escape(raw_text), placeholder, processed)
            placeholders.append((placeholder, mark))

        for placeholder, mark in placeholders:
            processed = processed.replace(placeholder, mark)

        return processed

    @staticmethod
    def _pack_inline_mark(meta: dict) -> str:
        """SEMANTIC_MARK_MAP の定義から <q=...> / <h=key:value> を生成する。"""
        kind = meta["kind"].value
        if "key" in meta:
            return f"<{kind}={meta['key']}:{meta['value']}>"
        return f"<{kind}={meta['value']}>"
