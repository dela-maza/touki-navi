# app/article/reference/group/state.py
from dataclasses import dataclass

from app.article.models.article_loc import AbsoluteArticleLocation


@dataclass
class SentenceLocationState:
    """
    Sentence 内の参照解析で使う location 状態。

    this_sentence_location は不変の原点として保持する。
    inner_location / last_reference_location / current_location_type は、
    Reference を先頭から読むたびに更新される予定の状態である。
    """

    this_sentence_location: AbsoluteArticleLocation # sentence自身の座標
    inner_location: AbsoluteArticleLocation # this_sentence_locationからのベクトル移動させた座標
    last_reference_location: AbsoluteArticleLocation | None = None # 現在の参照条文座標
    current_location_type: str = "inner"
    last_ref_exists: bool = False # 仮変数
    connector: bool = False
    range_connector: bool = False

    @classmethod
    def create_initial(cls, this_sentence_location: AbsoluteArticleLocation) -> "SentenceLocationState":
        """Sentence 自身の location から初期状態を作る。"""

        #
        return cls(
            this_sentence_location=this_sentence_location,
            inner_location=this_sentence_location,
        )
