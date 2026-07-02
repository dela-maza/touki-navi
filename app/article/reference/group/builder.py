# app/article/reference/group/builder.py
from app.article.models.article_loc import AbsoluteArticleLocation
from app.article.models.reference import Reference
from app.article.reference.group.connector import ReferenceConnector, ReferenceRangeConnector
from app.article.reference.group.state import SentenceLocationState
from app.article.reference.group.updater import SentenceLocationUpdater
from app.article.reference.resolver.locator_vector import LocatorVector

ReferenceAppearance = Reference | ReferenceConnector | ReferenceRangeConnector


class SentenceReferenceVectorBuilder:
    """
    SentenceReferenceGroup の ordered_appearances を走査し、参照解析用の状態を更新する作業員。

    SentenceReferenceGroup は器に留め、出現順の巡回、Reference.vector の確定、
    location 展開のための材料収集はこちらで担当する。
    """

    def __init__(self, group):
        self.group = group
        self.references: list[Reference] = group.references
        self.ordered_appearances: list[ReferenceAppearance] = group.ordered_appearances
        self.state: SentenceLocationState = group.location_state or SentenceLocationState.create_initial(
            group.this_sentence_location
        )
        self.updater = SentenceLocationUpdater()

    def build(self) -> SentenceLocationState:
        """
        ordered_appearances を先頭から読み、各 Reference の vector を確定する。

        index を使った range / each の展開は後段で行うため、ここでは可能な範囲だけ locations を作る。
        """
        for appearance in self.ordered_appearances:
            if isinstance(appearance, Reference):
                base_axis = self._build_reference(appearance)
                self.state = self.updater.update(self.state, appearance)
                self._update_location_state_after_reference(appearance, base_axis)
                continue

            self.state = self.updater.update(self.state, appearance)

        return self.state

    def _build_reference(self, reference: Reference) -> str:
        """Reference の relative_vector と現在 state から、確定前の LocatorVector を作る。"""
        relative_vector = reference.token_group.relative_vector
        base_axis = self.updater.select_base_axis(relative_vector, self.state)

        if base_axis == "semantic":
            reference.vector = relative_vector
            reference.locations = []
            return base_axis

        base_location = self._select_base_location(base_axis)
        reference.vector = relative_vector.merge(base_location)
        reference.locations = self._create_locations_from_vector(reference.vector)
        return base_axis

    def _select_base_location(self, base_axis: str) -> AbsoluteArticleLocation:
        """base_axis に対応する起点 location を返す。"""
        if base_axis in ("last_ref", "last_ref_range") and self.state.last_reference_location is not None:
            return self.state.last_reference_location

        return self.state.inner_location

    def _update_location_state_after_reference(self, reference: Reference, base_axis: str) -> None:
        """Reference から作れた location を、次の Reference が読む作業状態へ反映する。"""
        if not reference.locations:
            return

        last_location = reference.locations[-1]

        if base_axis in ("absolute", "last_ref", "last_ref_range"):
            self.state.last_reference_location = last_location
            self.state.last_ref_exists = True
            return

        if base_axis == "this":
            self.state.inner_location = last_location

    @staticmethod
    def _create_locations_from_vector(vector: LocatorVector) -> list[AbsoluteArticleLocation]:
        """
        index なしで確定できる vector だけ AbsoluteArticleLocation にする。

        range / each / shift range を含む vector は、ArticleElementLocationIndex を受け取る後段で展開する。
        """
        if any(cell.endswith("*") for cell in vector.path):
            return []

        if any(":" in cell for cell in vector.path):
            return []

        return [AbsoluteArticleLocation(path=vector.path)]
