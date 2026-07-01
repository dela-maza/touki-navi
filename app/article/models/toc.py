# app/article/models/toc.py
from dataclasses import dataclass, field

from app.article.constants.enums import LawType, TocDepth
from app.article.models.toc_loc import FullTocLocation


@dataclass
class TocElement:
    """本則TOC内の編・章・節・款・目を表す要素。"""

    depth: TocDepth
    num: str
    title: str
    article_range: str
    location: FullTocLocation
    child_elements: list["TocElement"] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "depth": self.depth.index,
            "depth_name": self.depth.name,
            "num": self.num,
            "title": self.title,
            "article_range": self.article_range,
            "location": self.location.id_attr,
            "child_elements": [child.to_dict() for child in self.child_elements],
        }


@dataclass
class Toc:
    """1つの法典の本則TOC全体を表すルートオブジェクト。"""

    law_type: LawType
    root_depth: TocDepth | None
    child_elements: list[TocElement]
    element_locations: list[FullTocLocation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "law": self.law_type.short_name,
            "law_name": self.law_type.name_jp,
            "root_depth": self.root_depth.name if self.root_depth else None,
            "child_elements": [child.to_dict() for child in self.child_elements],
            "element_locations": [location.id_attr for location in self.element_locations],
        }
