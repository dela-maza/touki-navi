from typing import TYPE_CHECKING

from app.article.models.index import ArticleIndex
from app.article.models.law import LawLibrary
from app.article.models.article_loc import FullLocation, ArticleDepth
from app.article.constants.markers import ReferenceMarker

if TYPE_CHECKING:
    from app.article.reference.resolver.token import ShiftToken


class LocationShiftResolver:
    """一区切り（条・項・号・目）のトークン解析ごとに、
    文脈依存の相対座標（同・前・次・範囲）を安全に計算して絶対住所（FullLocation）へ変換する。
    """

    def __init__(self, base_loc: FullLocation):
        # 基準となる現在地（座標）
        self.base_loc = base_loc
        # 条文全体のインデックス対照表（前条・次条・範囲の計算用）
        try:
            self.index: ArticleIndex | None = LawLibrary.get_index(base_loc.law_type)
        except (ValueError, AttributeError):
            self.index = None

    def apply(self, token: "ShiftToken") -> FullLocation:
        """Tokenの保持する offset（デジタル合図）を基準に、現在地（base_loc）を安全にシフトさせる。

        生の漢字テキスト（label）に対する文字パースは、ここ（下流）では一切行わない。
        """
        tag: str = token.tag
        offset_num: int | None = token.offset_num
        offset_suffix: str = token.offset_suffix

        # =================================================================
        # 1. 条文レベルの移動（前条・次条・前○条）➔ get_offset_ids に丸投げ
        # =================================================================
        if tag == "a":
            if offset_num is None:
                return self.base_loc

            # 💡 「前三条（例: -3_range）」の場合
            if offset_suffix == ReferenceMarker.RANGE_SUFFIX:
                return self._handle_article_shift(token, offset=offset_num, length=abs(offset_num))

            # 💡 「前条（-1）」「次条（1）」の場合
            if offset_num in (-1, 1):
                return self._handle_article_shift(token, offset=offset_num, length=1)

        # =================================================================
        # 2. 同一の親の中での移動（前項、次号など）、および「同○」の解決
        # =================================================================
        # 💡 同条・同項などの「現状維持」の合図
        if offset_num == 0:
            return self._handle_same_reference(tag)

        # 💡 項・号・目・細目の「前（-1）」「次（1）」の移動
        if tag in ("p", "i", "s1", "s2") and offset_num in (-1, 1):
            return self._handle_relative_sibling(tag, offset=offset_num)

        if tag in ("p", "i", "s1", "s2") and offset_num is not None:
            depth = self._tag_to_depth(tag)
            return self.base_loc.update_relative(depth, str(offset_num))

        # 相対指定の合図がない（絶対指定 "111" など）は、中流の簡易判定に委ねるため素通り
        return self.base_loc

    def _handle_article_shift(self, token: "ShiftToken", offset: int, length: int) -> FullLocation:
        """インデックス対照表の get_offset_ids を100%信用して、条文の移動（単一・範囲）を一括処理する。"""
        if not self.index:
            return self.base_loc

        # インデックス側の安全スライスに丸投げ（例: ['7', '8', '9'] が返る）
        target_ids = self.index.get_offset_ids(self.base_loc.article_num, offset, length)
        if not target_ids:
            return self.base_loc

        # 💡 複数範囲（length > 1）の場合は、Tokenの特設ポケットに実座標リストを注入する（UI用）
        if length > 1:
            token.resolved_ids = target_ids

        # 次のドミノ倒し（文脈引き継ぎ）用には、常にリストの「最後尾」の条文座標を返す
        # (単一移動の場合も、要素数1のリストの最後尾[0]を指すため、全く同じロジックで完結する)
        return self.base_loc.update_article(target_ids[-1])

    def _handle_same_reference(self, tag: str) -> FullLocation:
        """「同条」「同項」など、現在地の座標をそのまま引き継ぐ。"""
        if tag == "a":
            # 条文が同じ場合は、項以下がリセットされた綺麗な座標にする
            return self.base_loc.update_article(self.base_loc.article_num)

        depth = self._tag_to_depth(tag)
        current_val = self.base_loc.relative_loc.get_path_index(depth)
        return self.base_loc.update_relative(depth, current_val)

    def _handle_relative_sibling(self, tag: str, offset: int) -> FullLocation:
        """同一の親の中での、項・号・目の「前」「次」への移動。"""
        depth = self._tag_to_depth(tag)
        current_val = self.base_loc.relative_loc.get_path_index(depth)
        next_val = self._calculate_sibling_num(current_val, offset)
        return self.base_loc.update_relative(depth, next_val)

    # =================================================================
    # ヘルパーメソッド（classmethod）
    # =================================================================

    @classmethod
    def _tag_to_depth(cls, tag: str) -> ArticleDepth:
        """TokenのtagからArticleDepthへのマッピング。"""
        mapping = {
            "p": ArticleDepth.PARAGRAPH,
            "i": ArticleDepth.ITEM,
            "s1": ArticleDepth.SUB_ITEM_1,
            "s2": ArticleDepth.SUB_ITEM_2
        }
        return mapping.get(tag, ArticleDepth.PARAGRAPH)

    @classmethod
    def _calculate_sibling_num(cls, current_val: str, offset: int) -> str:
        """現在の階層番号（str）から移動した番号を計算。枝番（_2）にも追従する。"""
        if not current_val or current_val == "0":
            return "1"
        if current_val.isdigit():
            return str(max(1, int(current_val) + offset))

        parts = current_val.split("_")
        if parts[-1].isdigit():
            parts[-1] = str(max(1, int(parts[-1]) + offset))
            return "_".join(parts)
        return current_val
