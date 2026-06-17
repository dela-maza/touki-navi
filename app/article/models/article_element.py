# touki-navi/models/article_element.py
from dataclasses import dataclass, field, replace
from typing import List
from copy import deepcopy
from app.article.models.article_loc import FullLocation, ArticleDepth
from app.article.models.sentence import Sentence
from app.article.reference.chunker import ReferenceChunker


@dataclass(frozen=True)
class ArticleElement:
    depth: ArticleDepth
    num: str
    location: FullLocation
    title: str
    sentences: List[Sentence]
    children: List['ArticleElement'] = field(default_factory=list)

    def resolve_references(self) -> 'ArticleElement':
        # 循環参照回避のためメソッド内でインポート
        from app.article.reference.resolver.main import ReferenceResolver

        resolved_sentences = []

        # enumerateを使ってインデックス i を取得
        for i, s in enumerate(self.sentences):
            # 基点座標をコピーして、文ごとの隔離を徹底
            clean_loc = deepcopy(self.location)
            resolver = ReferenceResolver(start_location=clean_loc)

            chunked = ReferenceChunker.to_chunked_str(s.raw_text)
            result = resolver.resolve(chunked)

            # エラーの原因だった print 部分を修正
            # print(f"DEBUG: Sentence[{i}] resolved on {self.location.id_attr}")

            resolved_sentences.append(replace(s, resolved_text=result))

        # 子要素（号・目）へ再帰
        resolved_children = [child.resolve_references() for child in self.children]

        return replace(self, sentences=resolved_sentences, children=resolved_children)

    def to_dict(self):
        return {
            "depth": self.depth.value,
            "depth_name": self.depth.name,
            "num": self.num,
            "location": self.location.id_attr,
            "title": self.title,
            "sentences": [s.to_dict() for s in self.sentences],
            "children": [c.to_dict() for c in self.children]
        }