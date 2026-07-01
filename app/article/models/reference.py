# app/article/models/reference.py
from dataclasses import dataclass

from app.article.reference.resolver.token import TokenGroup


@dataclass
class Reference:
    """
    Sentence.marked_text に含まれる 1個の {...} 参照 mark を表す。

    Reference は DB 上のリンク確定状態を持たない。
    現時点では、3枠 reference mark の raw / arabic / locator を保持する軽い器である。
    raw_text / arabic_text は、将来 HTML 表示で漢数字・アラビア数字を切り替えるために保持する。
    """

    raw_mark_text: str
    raw_text: str
    arabic_text: str
    token_group: TokenGroup
    # vector: LocatorVector | None = None
    start_index: int = 0
    end_index: int = 0
    gap_before_text: str = ""
    base_axis: str | None = None
    semantic_mark_text: str | None = None
