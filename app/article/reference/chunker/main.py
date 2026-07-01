# app/article/reference/chunker/main.py
import re

from app.article.common.law_utils import convert_law_numbers
from app.article.reference.chunker.locator import ReferenceLocator
from app.article.reference.chunker.post_processor import ReferencePostProcessor
from app.article.reference.chunker.raw_marker import RawReferenceMarker


class ReferenceChunker:
    """
    法令の本文（センテンス）から参照表現を検出し、3要素の角括弧・波括弧フォーマットに構造化する前処理クラス。

        【パッキング規律】
        {[生テキスト(第一条)] | [アラビア数字表記全角（第１条)] | [locator]}
        ※ センテンス内のデジタル半角文字（{}, |, []) は、100%システムが埋め込んだ制御用マーカー（メタデータ）である。

        【アラビア数字表記ルール】
        アラビア数字表記は表示用のため全角で保持する。
        locator 計算時だけ半角に変換し、計算後に表示へ戻す値とは分離する。
    """

    @classmethod
    def to_chunked_str(cls, text: str) -> str:
        if not text:
            return ""

        processed = RawReferenceMarker.apply(text)

        # raw mark を3要素フォーマットに展開
        processed = re.sub(r"\{(.+?)}", cls._expand_raw_mark, processed)

        # 3枠 reference mark 展開後にだけ許される後処理
        return ReferencePostProcessor.apply_after_reference_expansion(processed)

    @classmethod
    def _expand_raw_mark(cls, match: re.Match) -> str:
        """
        :param match: "{[会社法][第百十一条の二][第二項][第一号]}"
        :return: "{[会社法]...|[会社法]...|[l=kai]...}"
        """
        # group(1)以降の数値を指定すると順番に各グループの文字列が返される
        raw_part: str = match.group(1)
        # '[会社法][第百十一条の二][第二項][第一号]' -> ['会社法','第百十一条の二','第二項','第一号']
        raw_values: list[str] = cls._split_bracket_values(raw_part)
        # ['会社法','第百十一条の二','第二項','第一号'] -> ['会社法','第１１１条の２','第２項','第１号']
        arabic_values: list[str] = [cls._to_arabic_value(raw) for raw in raw_values]
        # ['会社法','第１１１条の２','第２項','第１号'] -> '[会社法][第１１１条の２][第２項][第１号]'
        arabic_part = "".join(f"[{arabic}]" for arabic in arabic_values)

        locator_part = ReferenceLocator.to_locator_part(arabic_values)
        return cls._pack_reference(raw_part, arabic_part, locator_part)

    @staticmethod
    def _split_bracket_values(bracket_part: str) -> list[str]:
        """
        :param bracket_part: '[会社法][第百十一条の二][第二項][第一号]'
        :return:['会社法','第百十一条の二','第二項','第一号']
        """
        if not bracket_part:
            return []
        return bracket_part.strip("[]").split("][")

    @staticmethod
    def _pack_reference(raw_part: str, arabic_part: str, locator_part: str) -> str:
        return f"{{{raw_part}|{arabic_part}|{locator_part}}}"

    @staticmethod
    def _to_arabic_value(raw: str) -> str:
        """
        :param raw: '第百十一条の二'
        :return:'第１１１条の２'
        """
        return convert_law_numbers(raw)
