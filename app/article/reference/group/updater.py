# app/article/reference/group/updater.py
from app.article.constants.inline_marks import HINT_KEY_LAW, INLINE_MARK_HINT
from app.article.models.reference import Reference
from app.article.reference.group.connector import ReferenceConnector, ReferenceRangeConnector
from app.article.reference.group.state import SentenceLocationState
from app.article.reference.resolver.locator_vector import LocatorVector

ReferenceAppearance = Reference | ReferenceConnector | ReferenceRangeConnector


class SentenceLocationUpdater:
    """
    Reference / connector を1個ずつ読み、SentenceLocationState を更新する。

    FullLocation の確定はまだ行わない。
    現段階では、connector フラグと base_axis の仮判定だけを担当する。
    """

    def update(self, state: SentenceLocationState, appearance: ReferenceAppearance) -> SentenceLocationState:
        """appearance を1個処理し、次の SentenceLocationState を返す。"""
        if isinstance(appearance, ReferenceConnector):
            state.connector = True
            return state

        if isinstance(appearance, ReferenceRangeConnector):
            state.range_connector = True
            return state

        vector = appearance.token_group.relative_vector
        base_axis = self.select_base_axis(vector, state)

        if base_axis != "semantic":
            state.last_ref_exists = True
            state.current_location_type = base_axis

        state.connector = False
        state.range_connector = False

        return state

    def select_base_axis(
            self,
            vector: LocatorVector,
            state: SentenceLocationState,
    ) -> str:
        """LocatorVector と現在状態から、Reference の起点軸を仮に選ぶ。"""
        if vector.is_law_only:
            return "semantic"

        if vector.has_same_reference:
            return "last_ref" if state.last_ref_exists else "this"

        if vector.has_law_or_article:
            return "absolute"

        if vector.is_plain_inner_only and state.connector:
            return "last_ref"

        if vector.is_plain_inner_only and state.range_connector:
            return "last_ref_range"

        if vector.has_shift:
            return "this"

        return "this"

    @staticmethod
    def _create_semantic_mark_text(vector: LocatorVector) -> str | None:
        """location 参照ではない semantic mark に落とせる場合、その mark 文字列を返す。"""
        if vector.is_law_only:
            return f"<{INLINE_MARK_HINT}={HINT_KEY_LAW}:{vector.law_cell}>"
        return None
