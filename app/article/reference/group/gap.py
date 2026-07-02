# app/article/reference/group/gap.py
from app.article.constants.inline_marks import REFERENCE_CHAIN_TEXTS


class ReferenceGap:
    """Reference 同士の隙間文字列を評価する。"""

    @staticmethod
    def is_connector_only(gap_text: str) -> bool:
        """Reference 同士の隙間が、参照連鎖を維持できる接続語だけかを返す。"""
        gap = gap_text.strip()
        for connector in REFERENCE_CHAIN_TEXTS:
            gap = gap.replace(connector, "")
        return not gap.strip()
