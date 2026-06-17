# app/article/models/index.py

class ArticleIndex:
    """
    法典の「構造（IDの並び順）」のみを管理する軽量クラス。
    実体（Articleオブジェクト）は保持しない。
    """

    def __init__(self, id_list: list[str]):
        # ID（"10", "11_2" 等）の順序付きリスト
        # 文字列のリストなので、数万件でも数MB程度に収まる
        self.id_list = id_list

        # IDからインデックスを引くためのハッシュマップ
        self.index_cache: dict[str, int] = {
            id_val: i for i, id_val in enumerate(id_list)
        }

    def get_offset_ids(self, current_id: str, offset: int, length: int = 1) -> list[str]:
        """
        指定されたオフセットと長さに基づいて、IDの範囲を返す。
        """
        if current_id not in self.index_cache:
            return []

        current_idx = self.index_cache[current_id]
        start_idx = current_idx + offset
        end_idx = start_idx + length

        # 安全な範囲でスライス
        actual_start = max(0, start_idx)
        actual_end = min(len(self.id_list), end_idx)

        return self.id_list[actual_start:actual_end]
