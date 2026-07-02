# app/article/models/reference.py
from dataclasses import dataclass, field

from app.article.models.article_loc import AbsoluteArticleLocation
from app.article.reference.resolver.locator_vector import LocatorVector
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
    vector: LocatorVector | None = None
    locations: list[AbsoluteArticleLocation] = field(default_factory=list)
