# reference/resolver/shift.py
import re
from app.article.models.law import LawLibrary
from app.article.models.article_loc import FullLocation, ArticleDepth
from app.article.reference.resolver.token import Token
from app.article.common.law_utils import kanji_to_id


class LocationShiftResolver:
    """
    一区切り（条・項・号・目）のトークン解析ごとに、
    文脈依存の相対座標（同・前・次）を安全に計算して絶対住所（FullLocation）へ変換する。
    """

    def __init__(self, base_loc: FullLocation):
        # 基準となる現在地（座標）
        self.base_loc = base_loc
        # 条文全体のインデックス対照表（前条・次条の計算用）
        try:
            self.index = LawLibrary.get_index(base_loc.law_type)
        except (ValueError, AttributeError):
            self.index = None

    def apply(self, token: Token) -> FullLocation:
        """
        保持している base_loc を基準に、Token の相対表現（前・次・同）を解決する。
        """
        label = token.label
        tag = token.tag

        # =================================================================
        # 1. 「同○」の解決（同条・同項・同号・同目）
        # =================================================================
        if label.startswith("同"):
            return self._handle_same_reference(label, tag)

        # =================================================================
        # 2. 「前○」の解決（前条、前項、前号、前述の「前○条」含む）
        # =================================================================
        if label.startswith("前"):
            if "条" in label:
                return self._handle_prev_articles(label)
            return self._handle_relative_sibling(tag, offset=-1)

        # =================================================================
        # 3. 「次○」の解決（次条、次項、次号）
        # =================================================================
        if label.startswith("次"):
            if label == "次条":
                return self._handle_article_offset(offset=1, length=1)
            return self._handle_relative_sibling(tag, offset=1)

        # 相対指定に該当しない場合は現在地をそのまま返す
        return self.base_loc

    def _handle_same_reference(self, label: str, tag: str) -> FullLocation:
        """「同条」「同項」など、現在地の座標をそのまま固定して引き継ぐ"""
        if label == "同条":
            # update_articleにより、項以下が ("0", "0", "0", "0") にリセットされた綺麗な座標になる
            return self.base_loc.update_article(self.base_loc.article_num)

        # article_loc.py の get_path_index に合わせて修正
        depth = self._tag_to_depth(tag)
        current_val = self.base_loc.relative_loc.get_path_index(depth)
        return self.base_loc.update_relative(depth, current_val)

    def _handle_prev_articles(self, label: str) -> FullLocation:
        """「前条」または「前二条」などの複数条文の移動"""
        match = re.search(r"前([〇一二三四五六七八九十百０-９]+)条", label)
        num = 1 if not match else int(kanji_to_id(match.group(1), level=None))
        return self._handle_article_offset(offset=-num, length=num)

    def _handle_relative_sibling(self, tag: str, offset: int) -> FullLocation:
        """同一の親の中での、項・号・目の「前」「次」への移動"""
        depth = self._tag_to_depth(tag)
        # article_loc.py の get_path_index に合わせて修正
        current_val = self.base_loc.relative_loc.get_path_index(depth)

        # クラスメソッドを呼び出す（selfは不要）
        next_val = self._calculate_sibling_num(current_val, offset)

        return self.base_loc.update_relative(depth, next_val)

    def _handle_article_offset(self, offset: int, length: int) -> FullLocation:
        """条文レベルのオフセット移動（対照表のIndexを使用）"""
        if not self.index:
            return self.base_loc

        target_ids = self.index.get_offset_ids(self.base_loc.article_num, offset, length)
        if not target_ids:
            return self.base_loc

        target_id = target_ids[0] if length == 1 else f"{target_ids[0]}-{target_ids[-1]}"
        return self.base_loc.update_article(target_id)

    # =================================================================
    # JetBrains（PyCharm）インスペクション対策（classmethod化）
    # =================================================================

    @classmethod
    def _tag_to_depth(cls, tag: str) -> ArticleDepth:
        """TokenのtagからArticleDepthへのマッピング"""
        mapping = {
            "p": ArticleDepth.PARAGRAPH,
            "i": ArticleDepth.ITEM,
            "s1": ArticleDepth.SUB_ITEM_1,
            "s2": ArticleDepth.SUB_ITEM_2
        }
        return mapping.get(tag, ArticleDepth.PARAGRAPH)

    @classmethod
    def _calculate_sibling_num(cls, current_val: str, offset: int) -> str:
        """現在の階層番号（str）から移動した番号を計算"""
        if not current_val or current_val == "0":
            return "1"

        # 単純な整数の場合（例: "2"）
        if current_val.isdigit():
            calculated = max(1, int(current_val) + offset)
            return str(calculated)

        # 枝番がある場合（例: "1_2"）のフォールバック
        parts = current_val.split("_")
        if parts[-1].isdigit():
            next_sub = max(1, int(parts[-1]) + offset)
            parts[-1] = str(next_sub)
            return "_".join(parts)

        return current_val