# app/article/reference/chunker/post_processor.py
import re

from app.article.constants.enums import InlineMarkKind
from app.article.constants.xml_tags import SEMANTIC_MARK_MAP


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
        processed = cls.apply_hint_marks(processed)
        return processed

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
        for raw_text, mark in cls._qualifier_replacements():
            pattern = r"(\{[^{}]*})" + re.escape(raw_text)
            processed = re.sub(pattern, r"\1" + mark, processed)
        return processed

    @classmethod
    def apply_hint_marks(cls, text: str) -> str:
        """UI / semantic hint 用の語を <h=...> にする。"""
        processed = text
        placeholders: list[tuple[str, str]] = []

        for index, (raw_text, meta) in enumerate(cls._hint_items()):
            placeholder = f"@@HINT_MARK_{index}@@"
            mark = cls._pack_inline_mark(meta)
            processed = re.sub(re.escape(raw_text), placeholder, processed)
            placeholders.append((placeholder, mark))

        for placeholder, mark in placeholders:
            processed = processed.replace(placeholder, mark)

        return processed

    @classmethod
    def _qualifier_replacements(cls) -> list[tuple[str, str]]:
        replacements: list[tuple[str, str]] = []
        for raw_text, meta in cls._qualifier_items():
            replacements.append((raw_text, cls._pack_inline_mark(meta)))
        return replacements

    @staticmethod
    def _qualifier_items() -> list[tuple[str, dict]]:
        return [
            (raw_text, meta)
            for raw_text, meta in sorted(SEMANTIC_MARK_MAP.items(), key=lambda item: len(item[0]), reverse=True)
            if meta["kind"] == InlineMarkKind.QUALIFIER
        ]

    @staticmethod
    def _hint_items() -> list[tuple[str, dict]]:
        return [
            (raw_text, meta)
            for raw_text, meta in sorted(SEMANTIC_MARK_MAP.items(), key=lambda item: len(item[0]), reverse=True)
            if meta["kind"] == InlineMarkKind.HINT
        ]

    @staticmethod
    def _pack_inline_mark(meta: dict) -> str:
        """SEMANTIC_MARK_MAP の定義から <q=...> / <h=key:value> を生成する。"""
        kind = meta["kind"].value
        if "key" in meta:
            return f"<{kind}={meta['key']}:{meta['value']}>"
        return f"<{kind}={meta['value']}>"
