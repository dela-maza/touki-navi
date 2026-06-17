# models/toc_element.py
from dataclasses import dataclass, field
from typing import List
from app.article.models.toc_loc import TocDepth, TocLocation  # TocLocationを追加

@dataclass
class TOCElement:
    depth: TocDepth
    num: str
    label: str
    article_range: str
    toc_location: TocLocation  # 追加：自身の住所
    children: List['TOCElement'] = field(default_factory=list)

    def to_dict(self):
        return {
            "depth": self.depth.index,
            "depth_name": self.depth.name,
            "num": self.num,
            "label": self.label,
            "article_range": self.article_range,
            "toc_location": self.toc_location.addr,  # 文字列（0.1.0.0.0等）で出力
            "children": [c.to_dict() for c in self.children]
        }