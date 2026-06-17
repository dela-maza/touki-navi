# app/article/reference/chunker.py
import re
from app.article.constants.enums import LawType
𛂁

class ReferenceChunker:

    @classmethod
    def to_chunked_str(cls, text: str) -> str:
        if not text:
            return ""
        processed = text

        # 1. 法律名・同法
        for law in LawType:
            processed = re.sub(rf"(?<!\[\[){re.escape(law.name_jp)}(?!\]\])",
                               f"[[{law.name_jp}]]", processed)  # re.escape( ) でパターン中の特殊文字をエスケープ
        processed = processed.replace("同法", "[[同法]]")

        # 2. 条・項・号（絶対指定と相対指定を別々に処理）
        kanji_num = "一二三四五六七八九十百千万"

        # 行A: 「第何条」「第何項」「第何号」（枝番対応）
        processed = re.sub(rf"(第[{kanji_num}]+[条項号](?:の[{kanji_num}]+)*)",
                           r"[[\1]]", processed)

        # 行B: 「前条」「前項」「前号」
        processed = re.sub(r"(前[条項号])", r"[[\1]]", processed)

        # 3. 目・細目
        iroha = "イロハニホヘトチリヌルヲ"
        iroha_pattern = rf"(?<![\[ァ-ヶー])([{iroha}])(?![\]ァ-ヶー])"
        processed = re.sub(iroha_pattern, r"[[\1]]", processed)

        # 4. 後処理
        processed = cls._apply_affix_corrections(processed)

        # 5. 連結
        # これにより [[前条]][[第一項]] が [[前条][第一項]] になり、
        # TokenGroup で一括処理できるようになります
        processed = processed.replace("]][[", "][")

        return processed

    @classmethod
    def _apply_affix_corrections(cls, text: str) -> str:
        processed = text
        affix_patterns = [
            (r"法律", r"\[\[.+?\]\]"),
            (r"官報", r"\[\[.+?\]\]"),
            (r"省令", r"\[\[.+?\]\]"),
        ]

        for prefix, target in affix_patterns:
            pattern = rf"({prefix})\[\[(.+?)\]\]"
            processed = re.sub(pattern, r"\1\2", processed)

        return processed

