# app/article/reference/chunker/post_processor.py
import re

from app.article.constants.inline_marks import (
    CONNECTOR_TEXTS,
    INLINE_MARK_CONNECTOR,
    INLINE_MARK_QUALIFIER,
    INLINE_MARK_RANGE_CONNECTOR,
    RANGE_CONNECTOR_TEXTS,
    REFERENCE_QUALIFIER_TEXTS,
)


class ReferencePostProcessor:
    """3枠 reference mark 展開後にだけ呼ぶ後処理。"""

    @classmethod
    def apply_after_reference_expansion(cls, text: str) -> str:
        """
        3枠 reference mark の展開後にだけ呼ぶ。

        呼び出し順を変えると、raw mark の結合や3枠展開を壊す可能性がある。
        """
        processed = cls.apply_affix_corrections(text)
        processed = cls.apply_reference_qualifier_marks(processed)
        return cls.apply_reference_connector_marks(processed)

    @classmethod
    def apply_affix_corrections(cls, text: str) -> str:
        """法律・官報・省令など、直前語との関係で参照 mark から外すべき表現を戻す。"""
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
    def apply_reference_qualifier_marks(cls, text: str) -> str:
        """3枠 reference mark の直後に続く qualifier だけを <q=...> にする。"""
        processed = text
        for raw_text in REFERENCE_QUALIFIER_TEXTS:
            pattern = r"}" + re.escape(raw_text)
            processed = re.sub(pattern, "}" + f"<{INLINE_MARK_QUALIFIER}={raw_text}>", processed)
        return processed

    @classmethod
    def apply_reference_connector_marks(cls, text: str) -> str:
        """3枠 reference mark 同士の間にある connector だけを <c=...> / <r=...> にする。"""
        return re.sub(r"}(.+?){", cls._replace_connector_gap, text)

    @classmethod
    def _replace_connector_gap(cls, match: re.Match) -> str:
        """`}.+?{` で囲まれた gap 内の connector だけを mark する。"""
        gap_text = match.group(1)
        marked_gap = cls._mark_connector_texts(gap_text)
        return "}" + marked_gap + "{"

    @classmethod
    def _mark_connector_texts(cls, gap_text: str) -> str:
        """Reference 間の gap に含まれる connector 文字列を mark に置換する。"""
        marked = gap_text
        for connector in RANGE_CONNECTOR_TEXTS:
            marked = re.sub(re.escape(connector), f"<{INLINE_MARK_RANGE_CONNECTOR}={connector}>", marked)
        for connector in CONNECTOR_TEXTS:
            marked = re.sub(re.escape(connector), f"<{INLINE_MARK_CONNECTOR}={connector}>", marked)
        return marked
