# reference/resolver/shift.py
import re
from app.article.models.article import ArticleIndex
from app.article.models.law import LawLibrary
from app.article.models.article_loc import FullLocation, ArticleDepth
from app.article.reference.resolver.token import Token
from app.article.common.law_utils import kanji_to_id


class LocationShiftResolver:
    """
    一区切り（項・号）の解析ごとに生成され、廃棄される、
    文脈依存の相対座標解決者。
    """

    def __init__(self, base_loc: FullLocation):
        # 生成時の現在地を「基点」として保持する
        self.base_loc = base_loc
        # 頻繁に参照する地図（Index）も、生成時に一度だけ取得しておく
        try:
            self.index = LawLibrary.get_index(base_loc.law_type)
        except ValueError:
            self.index = None

    def apply(self, token: Token) -> FullLocation:
        """
        保持している base_loc を基準に、Token の相対表現を解決する。
        """
        label = token.label

        # 1. 「同条」
        if label == "同条":
            return self.base_loc.update_article(self.base_loc.article_num)

        # 2. 「同項」
        if label == "同項":
            current_p = self.base_loc.relative_loc.get_path_index(ArticleDepth.PARAGRAPH)
            return self.base_loc.update_relative(ArticleDepth.PARAGRAPH, current_p)

        # 3. 「前○条」
        if label.startswith("前") and label.endswith("条"):
            return self._handle_prev_articles(label)

        # 4. 「次条」
        if label == "次条":
            return self._handle_offset(offset=1, length=1)

        return self.base_loc

    def _handle_prev_articles(self, label: str) -> FullLocation:
        # 数字抽出ロジック（前述と同じ）
        match = re.search(r"前([〇一二三四五六七八九十百０-９]+)条", label)
        num = 1 if not match else int(kanji_to_id(match.group(1), level=None))

        return self._handle_offset(offset=-num, length=num)

    def _handle_offset(self, offset: int, length: int) -> FullLocation:
        if not self.index:
            return self.base_loc

        target_ids = self.index.get_offset_ids(self.base_loc.article_num, offset, length)
        if not target_ids:
            return self.base_loc

        target_id = target_ids[0] if length == 1 else f"{target_ids[0]}-{target_ids[-1]}"
        return self.base_loc.update_article(target_id)