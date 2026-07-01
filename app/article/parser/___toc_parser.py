# app/article/parser/___toc_parser.py

from bs4.element import Tag
from typing import List
from app.article.models.___toc_loc import TocDepth
from app.article.models.___toc_element import TOCElement
from app.article.models.___toc_loc import TocLocation

class TOCParser:
    def __init__(self, toc_root: Tag):
        """
        toc_root: <TOC> タグのノード
        """
        self.root = toc_root

    def parse(self) -> List[TOCElement]:
        if not self.root:
            return []

        elements = []
        # 起点の住所はすべて "0"
        base_loc = TocLocation()

        for child in self.root.find_all(recursive=False):
            if child.name == "TOCLabel":
                continue

            depth = TocDepth.from_toc_tag(child.name)
            if depth:
                # 自分の階層の Num をセットして解析へ
                elements.append(self._parse_node(child, depth, base_loc))
            elif child.name == "TOCSupplProvision":
                elements.append(self._parse_suppl(child, base_loc))

        return elements

    def _parse_node(self, node: Tag, depth: TocDepth, parent_loc: TocLocation) -> TOCElement:
        """
        parent_loc: 親から引き継いだ住所
        """
        # 1. 自分の住所を確定させる (例: 章なら 2番目のスロットを Num で埋める)
        my_num = node.get("Num", "0")
        current_loc = parent_loc.set_at(depth, my_num)

        title_node = node.find(f"{depth.body_tag}Title", recursive=False)
        label = title_node.get_text() if title_node else ""

        range_node = node.find("ArticleRange", recursive=False)
        article_range = range_node.get_text() if range_node else ""

        # 2. 子要素（節など）に自分の住所を引き継がせる
        children = []
        if depth.index < TocDepth.DIVISION.index:
            next_depth = TocDepth.from_index(depth.index + 1)
            if next_depth:
                for child_node in node.find_all(next_depth.toc_tag, recursive=False):
                    # 自分の current_loc を渡すことで、節の住所に章の Num が残る
                    children.append(self._parse_node(child_node, next_depth, current_loc))

        return TOCElement(
            depth=depth,
            num=my_num,
            label=label,
            article_range=article_range,
            toc_location=current_loc,  # 確定した住所を保持
            children=children
        )

    def _parse_suppl(self, node: Tag, parent_loc: TocLocation) -> TOCElement:
        """
        附則（TOCSupplProvision）の解析用
        parent_loc: ここではベースの (0, 0, 0, 0, 0) が渡されます
        """
        label_node = node.find("SupplProvisionLabel", recursive=False)
        label = label_node.get_text() if label_node else "附則"

        # 附則は特定の章番号を持たないことが多いので、親の住所をそのまま使用するか、
        # 必要であれば特定のフラグを立てた住所にすることも可能です。
        # 今回はシンプルに親の住所（0.0.0.0.0）を割り当てます。

        return TOCElement(
            depth=TocDepth.CHAPTER,  # 便宜上、章レベルとして扱う
            num="",
            label=label,
            article_range="",
            toc_location=parent_loc,  # ここで parent_loc を受け取って保持
            children=[]
        )
