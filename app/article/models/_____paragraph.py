# touki-navi/models/_____paragraph.py
from dataclasses import dataclass
from app.article.models.subdivision import Subdivision
from app.article.constants.enums import ArticleDepth

@dataclass
class Paragraph(Subdivision):
    """
    条文の直下にぶら下がる「項」を表すクラス
    """
    def __init__(self, num: str, location, sentences, children=None):
        super().__init__(
            depth=ArticleDepth.PARAGRAPH,
            num=num,
            location=location,
            sentences=sentences,
            children=children or []
        )