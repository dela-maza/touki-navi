# touki-navi/models/article_loc.py
from typing import Tuple
from dataclasses import dataclass
from app.article.constants.enums import LawType, ArticleDepth


@dataclass(frozen=True)
class ArticleLocation:
    """
    一条の中の「相対住所」。
    """
    path: Tuple[str, str, str, str] = ("0", "0", "0", "0")

    @property
    def depth(self) -> ArticleDepth:
        """
        現在の階層を判定する。
        """
        for i in range(len(self.path) - 1, 0, -1):
            if self.path[i] != "0":
                depth = ArticleDepth.from_index(i)
                return depth if depth else ArticleDepth.PARAGRAPH
        return ArticleDepth.PARAGRAPH

    def get_path_index(self, depth: ArticleDepth) -> str:
        """
        指定された階層の現在のインデックス値を取得する。
        """
        # depth は ArticleDepth Enum (PARAGRAPH=0, ITEM=1, ...)
        # その index プロパティ（0〜3）を使って tuple から値を取り出す
        return self.path[depth.index]

    def set_at(self, depth: ArticleDepth, val: str) -> "ArticleLocation":
        path_list: list[str] = list(self.path)  # tuple -> list
        target_idx: int = depth.index
        path_list[target_idx] = str(val)  # 確実に文字列として代入

        # 以降のリセット
        for i in range(target_idx + 1, len(path_list)):
            path_list[i] = "0"
        return ArticleLocation(path=tuple(path_list))

    @property
    def addr(self) -> str:
        """2.3.0.0 形式（項.号.目1.目2）の文字列を返す"""
        return ".".join(self.path)


@dataclass(frozen=True, init=False)
class FullLocation:
    path: Tuple[str, str, str, str, str, str]

    def __init__(
            self,
            law_type: LawType | None = None,
            article_num: str | None = None,
            relative_loc: ArticleLocation | None = None,
            path: Tuple[str, str, str, str, str, str] | None = None,
    ):
        if path is not None:
            if len(path) != 6:
                raise ValueError(f"FullLocation.path must have 6 elements: {path}")
            object.__setattr__(self, "path", tuple(str(cell) for cell in path))
            return

        if law_type is None or article_num is None:
            raise ValueError("FullLocation requires path or law_type and article_num")

        relative_path = relative_loc.path if relative_loc else ArticleLocation().path
        object.__setattr__(
            self,
            "path",
            (
                law_type.short_name,
                str(article_num),
                relative_path[0],
                relative_path[1],
                relative_path[2],
                relative_path[3],
            )
        )

    @property
    def law_type(self) -> LawType:
        return LawType.from_short_name(self.path[0])

    @property
    def article_num(self) -> str:
        return self.path[1]

    @property
    def relative_loc(self) -> ArticleLocation:
        return ArticleLocation(self.path[2:])

    # --- 状態遷移メソッド ---
    def update_law(self, new_law: LawType | str) -> "FullLocation":
        """
        law_typeが変わった場合
        article_num以下をリセット
        """
        if isinstance(new_law, str):
            law_type = next((law for law in LawType if law.short_name == new_law), self.law_type)
        else:
            law_type = new_law

        return FullLocation(path=(law_type.short_name, "0", "0", "0", "0", "0"))

    def update_article(self, num_str: str) -> "FullLocation":
        """
        条が切り替わった場合
        項以下をリセット
        """
        return FullLocation(path=(self.path[0], str(num_str), "0", "0", "0", "0"))

    def update_relative(self, depth: ArticleDepth, val: str) -> "FullLocation":
        """項・号・目が切り替わった場合（ArticleLocationのロジックを使用）"""
        # 既存の set_at をそのまま活用
        new_relative = self.relative_loc.set_at(depth, val)
        return FullLocation(path=(self.path[0], self.path[1], *new_relative.path))

    @property
    def addr(self) -> str:
        """
        すべてをピリオドで繋ぐ形式に変更
        例: shoutouki.19_2.1.0.0.0
        相対値の場合: shoutouki.-1.1.0.0.0
        """
        return ".".join(self.path)

    @property
    def id_attr(self) -> str:
        """HTML id属性用の互換名。内部ロジックでは addr を優先する。"""
        return self.addr

    def to_dict(self):
        return {
            "law_short_name": self.law_type.short_name,
            "law_name_jp": self.law_type.name_jp,
            "article_num": self.article_num,
            "relative_loc": self.relative_loc.addr,
            "addr": self.addr,
            "id_attr": self.id_attr
        }
