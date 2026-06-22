# app/article/reference/chunker.py
import re
from app.article.constants.enums import LawType


class ReferenceChunker:

    @classmethod
    def to_chunked_str(cls, text: str) -> str:
        if not text:
            return ""
        processed: str = text

        # =================================================================
        # 1. 法律名・同法
        # =================================================================
        # 一度しか通らないためガードは不要。長い順にソートして部分一致の誤爆を防ぐ
        for law in sorted(LawType, key=lambda l: len(l.name_jp), reverse=True):
            processed = re.sub(re.escape(law.name_jp), f"[[{law.name_jp}]]", processed)

        # 「同法」を確実に囲む
        processed = processed.replace("同法", "[[同法]]")

        # =================================================================
        # 2. 条・項・号の絶対指定（個別の無限枝番対応）
        # =================================================================
        kanji_num = "一二三四五六七八九十百千万"

        jo_pattern = rf"第[{kanji_num}]+条(?:の[{kanji_num}]+)*"
        kou_pattern = rf"第[{kanji_num}]+項(?:の[{kanji_num}]+)*"
        gou_pattern = rf"第[{kanji_num}]+号(?:の[{kanji_num}]+)*"

        # それぞれを非キャプチャグループ (?: ) でまとめ、全体を一括で囲む
        absolute_pattern = rf"({jo_pattern}|{kou_pattern}|{gou_pattern})"
        processed = re.sub(absolute_pattern, r"[[\1]]", processed)

        # =================================================================
        # 3. 条・項・号の相対指定・複数指定
        # =================================================================
        # 「前条」「次項」「同号」および「各号」を確実にキャッチする
        # ※「各号」を単体で切り出すことで、後続のTokenGroupで複数指定（リスト）として解析可能にします
        relative_pattern = r"([前次同][条項号]|各号)"
        processed = re.sub(relative_pattern, r"[[\1]]", processed)

        # =================================================================
        # 4. 目・細目（イロハ） ※次回議題のため、一旦現状維持
        # =================================================================
        iroha = "イロハニホヘトチリヌルヲ"
        iroha_pattern = rf"(?<![\[ァ-ヶー])([{iroha}])(?![\]ァ-ヶー])"
        processed = re.sub(iroha_pattern, r"[[\1]]", processed)

        # 5. 後処理
        processed = cls._apply_affix_corrections(processed)

        # 6. 連結
        # 例: [[前条]][[第一項]] ➔ [[前条][第一項]]
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