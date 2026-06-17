# touki-navi/models/article_loc.py
from typing import cast,Tuple
from dataclasses import dataclass
from app.article.constants.enums import LawType, ArticleDepth

@dataclass(frozen=True)
class ArticleLocation:
    """
    一条の中の「相対住所」。
    idx_path: (項index, 号index, 細別1index, 細別2index)
    ※インデックスは 0 スタートとする（第1項なら 0）
    """
    path: Tuple[int, int, int, int] = (0, 0, 0, 0)

    @property
    def depth(self) -> ArticleDepth:
        """
        現在の階層を判定する。
        """
        for i in range(len(self.path) - 1, 0, -1):
            if self.path[i] > 0:
                return ArticleDepth(i)
        return ArticleDepth.PARAGRAPH

    def get_value(self, depth: ArticleDepth) -> int:
        """
        指定された階層の現在のインデックス値を取得する。
        """
        # depth は ArticleDepth Enum (PARAGRAPH=0, ITEM=1, ...)
        # その index プロパティ（0〜3）を使って tuple から値を取り出す
        return self.path[depth.index]

    def set_at(self, depth: ArticleDepth, val: any) -> "ArticleLocation": # int から any へ
        path_list = list(self.path)
        target_idx = depth.index
        path_list[target_idx] = val # カタカナや数値がそのまま入る

        # 以降のリセット
        for i in range(target_idx + 1, len(path_list)):
            path_list[i] = 0
        return ArticleLocation(path=tuple(path_list))

    @property
    def addr(self) -> str:
        """2.3.0.0 形式（項.号.目1.目2）の文字列を返す"""
        return ".".join(map(str, self.path))

@dataclass(frozen=True)
class FullLocation:
    law_type: LawType
    article_num: str
    relative_loc: ArticleLocation

    # --- 状態遷移メソッド ---
    @staticmethod
    def update_law( new_law: LawType) -> "FullLocation": # staticmethodを解除
        return FullLocation(
            law_type=new_law,
            article_num="0",
            relative_loc=ArticleLocation((0, 0, 0, 0))
        )

    def update_article(self, num_str: str) -> "FullLocation":
        """条が切り替わった場合（項以下をリセット）"""
        return FullLocation(
            self.law_type,
            article_num=num_str,
            relative_loc=ArticleLocation((0, 0, 0, 0))
        )

    def update_relative(self, depth: ArticleDepth, val: int) -> "FullLocation":
        """項・号・目が切り替わった場合（ArticleLocationのロジックを使用）"""
        # 既存の set_at をそのまま活用！
        new_relative = self.relative_loc.set_at(depth, val)
        return FullLocation(
            self.law_type,
            self.article_num,
            relative_loc=new_relative
        )

    @property
    def id_attr(self) -> str:
        """
        すべてをピリオドで繋ぐ形式に変更
        例: shoutouki.19_2.1.0.0.0
        相対値の場合: shoutouki.-1.1.0.0.0
        """
        return f"{self.law_type.short_name}.{self.article_num}.{self.relative_loc.addr}"
    def to_dict(self):
        return {
            "law_short_name": self.law_type.short_name,
            "law_name_jp": self.law_type.name_jp,
            "article_num": self.article_num,
            "relative_loc": self.relative_loc.addr,
            "id_attr": self.id_attr
        }