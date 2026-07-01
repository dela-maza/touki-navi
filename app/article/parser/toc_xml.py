# app/article/parser/toc_xml.py
from bs4 import Tag

from app.article.constants.enums import LawType, TocDepth
from app.article.constants.xml_tags import (
    ATTR_NUM,
    TAG_ARTICLE_RANGE,
    TAG_TOC_LABEL,
    TAG_TOC_SUPPL_PROVISION,
    get_toc_xml_tag_meta_by_depth,
    get_toc_xml_tag_meta_by_toc_tag,
)
from app.article.models.toc import Toc, TocElement
from app.article.models.toc_loc import FullTocLocation, TocLocation


class TocXml:
    """
    法令XMLの <TOC> 以下から、本則TOCツリーを生成する。

    附則は本則TOCとは構造が異なるため、このクラスでは扱わない。
    """

    def __init__(self, law_type: LawType):
        self.law_type = law_type
        self.element_locations: list[FullTocLocation] = []

    def parse(self, toc_node: Tag | None) -> Toc:
        """<TOC> ノードから Toc を生成する。"""
        self.element_locations = []

        if toc_node is None:
            raise ValueError(f"TOC node is required: law={self.law_type.short_name}")

        base_location = FullTocLocation(
            law_type=self.law_type,
            relative_loc=TocLocation(),
        )
        child_elements = self._parse_elements(
            nodes=toc_node.find_all(recursive=False),
            parent_location=base_location,
        )

        # リストの先頭深度（編・章）をroot_depthとする
        root_depth = child_elements[0].depth if child_elements else None

        return Toc(
            law_type=self.law_type,
            root_depth=root_depth,
            child_elements=child_elements,
            element_locations=list(self.element_locations),
        )

    def _parse_elements(
            self,
            nodes: list[Tag],
            parent_location: FullTocLocation,
    ) -> list[TocElement]:
        """同じ親を持つTOCノード群を、TocElementのlistに変換する。"""
        elements: list[TocElement] = []

        for node in nodes:
            if node.name in (TAG_TOC_LABEL, TAG_TOC_SUPPL_PROVISION):
                # '<TOCLabel>目次</TOCLabel>'部分のノードは呼び飛ばす
                continue

            try:
                meta = get_toc_xml_tag_meta_by_toc_tag(node.name)
            except KeyError:
                continue

            elements.append(
                self._parse_element(
                    node=node,
                    depth=meta["depth"],
                    parent_location=parent_location,
                )
            )

        return elements

    def _parse_element(
            self,
            node: Tag,
            depth: TocDepth,
            parent_location: FullTocLocation,
    ) -> TocElement:
        """TOC要素1個を読み取り、子要素も再帰的にTocElement化する。"""
        num = node.get(ATTR_NUM, "0")
        location = parent_location.update_relative(depth, num)
        self.element_locations.append(location) #

        meta = get_toc_xml_tag_meta_by_depth(depth)

        title_node = node.find(meta["title_tag"], recursive=False)
        title = title_node.get_text() if title_node else ""

        range_node = node.find(TAG_ARTICLE_RANGE, recursive=False)
        article_range = range_node.get_text() if range_node else ""

        child_elements = self._parse_elements(
            nodes=node.find_all(recursive=False),
            parent_location=location,
        )

        return TocElement(
            depth=depth,
            num=num,
            title=title,
            article_range=article_range,
            location=location,
            child_elements=child_elements,
        )
"""
<TOC>
      <TOCLabel>目次</TOCLabel>
      <TOCChapter Num="1">
        <ChapterTitle>第一章　総則</ChapterTitle>
        <ArticleRange>（第一条・第一条の二）</ArticleRange>
      </TOCChapter>
      <TOCChapter Num="1_2">
        <ChapterTitle>第一章の二　登記所及び登記官</ChapterTitle>
        <ArticleRange>（第一条の三―第五条）</ArticleRange>
      </TOCChapter>
      <TOCChapter Num="2">
        <ChapterTitle>第二章　登記簿等</ChapterTitle>
        <ArticleRange>（第六条―第十三条）</ArticleRange>
      </TOCChapter>
      <TOCChapter Num="3">
        <ChapterTitle>第三章　登記手続</ChapterTitle>
        <TOCSection Num="1">
          <SectionTitle>第一節　通則</SectionTitle>
          <ArticleRange>（第十四条―第二十六条）</ArticleRange>
        </TOCSection>
"""
