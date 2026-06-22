#reference/resolver/main.py
import re
from app.article.reference.resolver.token import TokenGroup


class ReferenceResolver:
    """
    リンク文字列 [[...]] を解析し、HTMLタグへ置換する司令塔。
    """

    def __init__(self, start_location):
        # 座標の初期値を保持
        self.location = start_location

    def _handle_group(self, match: re.Match) -> str:
        raw_segment = match.group(0)
        try:
            # TokenGroup を生成（この中で座標が計算される）
            group = TokenGroup(raw_segment, self.location)

            # 次のリンクのために現在地を更新
            self.location = group.final_location

            # 置換後の文字列（HTML）を返す
            return group.to_resolved_string()

        except Exception as e:
            # エラー時は原本を返し、画面が壊れるのを防ぐ
            print(f"Resolver Error: {e}")
            return raw_segment

    def resolve(self, sentence_text: str) -> str:
        if not sentence_text:
            return ""

        # リンクのパターン
        segment_pattern = r"(\[\[.+?\]\])"

        # re.sub で _handle_group を呼び出し、置換結果を返す
        return re.sub(segment_pattern, self._handle_group, sentence_text)

