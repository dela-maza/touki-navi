# touki-navi/models/_____paragraph.py
from dataclasses import dataclass, field
from typing import List
from app.article.models.article_loc import FullLocation
from models.law_element import LawElement  # ここでインポート

@dataclass(frozen=True)
class Paragraph:
    """
    条(Article)の直下にある項。
    """
    num: str
    full_loc: FullLocation
    sentences: List[str]
    items: List[LawElement] = field(default_factory=list)