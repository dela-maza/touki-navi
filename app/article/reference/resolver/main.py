#reference/resolver/main.py
import re

from app.article.models.article_loc import FullLocation
from app.article.reference.resolver.token import TokenGroup


class ReferenceResolver:
    """
    リンク文字列 [[...]] を解析し、HTMLタグへ置換する司令塔。
    """

    def __init__(self, cur_location:FullLocation):
        # 座標の初期値を保持
        self.cur_location = cur_location  # 100条（不変）
        self.last_ref_location = cur_location  # 初期値は100条（変動）

    def _handle_group(self, match: re.Match) -> str:
        raw_segment = match.group(0)
        try:
            # 💡 TokenGroup に「真の現在地」と「直近の参照」の双方を叩き込む
            group = TokenGroup(raw_segment, self.cur_location, self.last_ref_location)

            # 次のトークンのために、変動する文脈（111条など）を更新して記憶
            self.last_ref_location = group.final_last_ref

            # 💡 双方の可能性のID（id_attr）を抱えた特殊なタグ、または構造を返す
            return group.to_resolved_string_with_options()

        except Exception as e:
            print(f"Resolver Error: {e}")
            return raw_segment

    def resolve(self, sentence_text: str) -> str:
        if not sentence_text:
            return ""

        # リンクのパターン
        segment_pattern = r"(\[\[.+?\]\])"

        # re.sub で _handle_group を呼び出し、置換結果を返す
        return re.sub(segment_pattern, self._handle_group, sentence_text)

