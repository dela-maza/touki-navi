# touki-navi/parser/article_xml.py
from typing import List, Optional, Dict, Any
from bs4 import Tag
from app.article.constants.enums import LawType, ArticleDepth
from app.article.constants.xml_tags import XML_TAG_MAP, ATTR_NUM, TAG_COLUMN, TAG_SENTENCE, get_xml_tag_meta_by_depth
from app.article.models.article_loc import AbsoluteArticleLocation, ArticleInnerLocation
from app.article.models.sentence import Sentence, BlockSentenceBase, PlainBlockSentence, ColumnBlockSentence
from app.article.models.article import Article, Paragraph, Item, Subitem1, Subitem2
from app.article.reference.chunker import ReferenceChunker


# =================================================================
# ArticleXml の役割と関数チェーン
# =================================================================
# このモジュールの責務は、法令XMLの <Article> 以下を Python の Article モデルツリーへ変換すること。
# 参照解決（前条・同項などの意味解釈）や画面表示用HTML化は、ここでは行わない。
#
# 変換される階層:
#   Article
#     └─ Paragraph
#          └─ Item
#               └─ Subitem1
#                    └─ Subitem2
#
# 関数の流れ:
#   parse_articles()
#     └─ 複数の <Article> を探し、1条ずつ _parse_single_article() に渡す。
#
#   _parse_single_article()
#     └─ 1つの <Article> から Article モデルを作る。
#        Article 直下の Paragraph はここで処理し、
#        Paragraph 配下の Item / Subitem1 / Subitem2 は _parse_list_tree() に任せる。
#
#   _parse_block_sentence()
#     └─ ParagraphSentence / ItemSentence / Subitem1Sentence などの本文ブロックを読む。
#        Sentence が直下にある場合は PlainBlockSentence、
#        Column を挟む場合は ColumnBlockSentence に変換する。
#
#   _parse_list_tree()
#     └─ Item / Subitem1 / Subitem2 の「同じ形で下へ続く箇条書き階層」を再帰的に読む。
#        複数ノードを集める入口で、1個分の処理は _parse_list_element() に任せる。
#
#   _parse_list_element()
#     └─ Item / Subitem1 / Subitem2 のうち、現在階層に対応する1ノードを読む。
#        自分の本文を _parse_block_sentence() で読み、
#        子階層を _parse_list_tree() で読み、
#        最後に _create_list_element() でモデル化する。
#
#   _next_depth()
#     └─ ITEM -> SUB_ITEM_1 -> SUB_ITEM_2 -> None の順で、次に潜る階層を決める。
#
#   _create_list_element()
#     └─ ArticleDepth に応じて Item / Subitem1 / Subitem2 のどれを作るかを決める。
# =================================================================


class ArticleXml:
    def __init__(self, law_type: LawType):
        self.law_type = law_type
        self.element_locations_by_article: dict[str, list[AbsoluteArticleLocation]] = {}
        self._current_element_locations: list[AbsoluteArticleLocation] = []

    def parse_articles(self, law_body_node: Tag) -> List[Article]:
        """
        <LawBody> を直接受け取り、内包される全ての <Article> をパースして返す。
        """
        self.element_locations_by_article = {}

        # 💡 マップから "Article" というタグ名を引いて検索をかける
        article_tag_name = XML_TAG_MAP["article"]["tag_name"]
        article_nodes: List[Tag] = law_body_node.find_all(article_tag_name, recursive=True)
        articles: List[Article] = []

        for article_node in article_nodes:
            self._current_element_locations = []
            art: Article = self._parse_single_article(article_node)
            self.element_locations_by_article[art.num] = list(self._current_element_locations)
            articles.append(art)

        return articles

    def _parse_single_article(self, node: Tag) -> Article:
        """
        単一の <Article> ノードから Article オブジェクトを構築する。
        """
        # 条レベル of メタデータ情報を一撃で回収
        meta = XML_TAG_MAP["article"]

        # <Article Num="1_2">
        article_num: str = node.get(ATTR_NUM, '')

        # caption  <ArticleCaption>（定義）</ArticleCaption>
        caption_node: Optional[Tag] = node.find(meta["caption_tag"])
        article_caption: str = caption_node.get_text() if caption_node else ""

        # title <ArticleTitle>第一条の二</ArticleTitle>
        title_node: Optional[Tag] = node.find(meta["title_tag"])
        article_title: str = title_node.get_text() if title_node else ""

        # articleのlocation値
        base_location: AbsoluteArticleLocation = AbsoluteArticleLocation(
            law_type=self.law_type,
            article_num=article_num,
            inner_loc=ArticleInnerLocation()
        )

        # =================================================================
        # 👑 1層目: 項 (Paragraph) のループ（主文ブロックとして独立処理）
        # =================================================================

        # 項レベルのメタデータ情報を一撃で回収
        pg_tag = XML_TAG_MAP["paragraph"]
        paragraphs: List[Paragraph] = []

        # 💡 pg_tag["tag_name"] の辞書引き形式に修正してバグを回避
        for pg_node in node.find_all(pg_tag["tag_name"], recursive=False):
            pg_num: str = pg_node.get(ATTR_NUM, '1')  # <Paragraph Num="1">
            pg_location: AbsoluteArticleLocation = base_location.update_inner_location(ArticleDepth.PARAGRAPH, pg_num)
            self._current_element_locations.append(pg_location)

            # 💡 号から下の箇条書き世界は、完全に構造が統一されたツリーなので再帰に流し込む
            items = self._parse_list_tree(pg_node, ArticleDepth.ITEM, pg_location)

            pg_element = Paragraph(
                num=pg_num,
                location=pg_location,
                body=self._parse_block_sentence(pg_node, pg_tag["wrapper_tag"]),
                items=items
            )
            paragraphs.append(pg_element)

        return Article(
            num=article_num,
            law_type=self.law_type,
            title=article_title,
            caption=article_caption,
            paragraphs=paragraphs
        )


    def _parse_list_tree(self,
                         parent_node: Tag,
                         current_depth: Optional[ArticleDepth],
                         current_loc: AbsoluteArticleLocation) -> List[Any]:
        """
        【SubDivisionBase 専用】
        号 ➔ 目1 ➔ 目2 へと、同じListItemの性質だけを例外処理ゼロで全自動回収する
        """
        if current_depth is None:
            return []

        elements: list[Any] = []
        # 外部化された定数マップから、現在の階層に対応するパース知識を完全ハッシュ引き
        meta: dict = get_xml_tag_meta_by_depth(current_depth)

        for child_node in parent_node.find_all(meta["tag_name"], recursive=False):
            elements.append(
                self._parse_list_element(
                    child_node=child_node,
                    current_depth=current_depth,
                    current_loc=current_loc,
                    meta=meta,
                )
            )

        return elements

    def _parse_block_sentence(self, element_node: Tag, wrapper_tag_name: str) -> BlockSentenceBase:
        """
        ParagraphSentenceやItemSentenceなどの境界（スコープ）を絶対に無視せず、
        Columnの有無によって『Plain』と『Column』の器へ完全分離して格納する。
        """
        # 1. 境界となるラッパータグ（例: ItemSentence）を特定
        wrapper_node: Tag = element_node.find(wrapper_tag_name, recursive=False)
        if not wrapper_node:
            return PlainBlockSentence()  # 存在しない場合は空のフラット容器を返す

        # 2. ラッパーの直下一親等に <Column> タグがあるかスキャン
        column_nodes = wrapper_node.find_all(TAG_COLUMN, recursive=False)

        if column_nodes:
            # 💡 【パターンA】本物の Column 構造がある場合（定義条文など）
            columns_map: Dict[int, List[Sentence]] = {}
            for col_node in column_nodes:
                col_idx = int(col_node.get(ATTR_NUM, '1'))

                # その Column の中にある Sentence だけを回収（他流の混入を防ぐため recursive=False）
                st_list: list[Sentence] = []
                for st_node in col_node.find_all(TAG_SENTENCE, recursive=False):
                    st_list.append(self._create_sentence(st_node))

                columns_map[col_idx] = st_list

            return ColumnBlockSentence(columns=columns_map)

        else:
            # 💡 【パターンB】Column が存在しない、普通の文章の場合
            plain_list: list[Sentence] = []
            # ラッパー直下の Sentence タグだけを素直に回収
            for st_node in wrapper_node.find_all(TAG_SENTENCE, recursive=False):
                plain_list.append(self._create_sentence(st_node))

            return PlainBlockSentence(sentences=plain_list)

    @staticmethod
    def _create_sentence(st_node: Tag) -> Sentence:
        """
        <Sentence> ノードから Sentence を生成し、物理レイヤの marked_text まで作る。
        """
        raw_text = st_node.get_text()
        return Sentence(
            num=st_node.get(ATTR_NUM, '1'),
            text=raw_text,
            marked_text=ReferenceChunker.to_chunked_str(raw_text),
        )

    def _parse_list_element(self, child_node: Tag, current_depth: ArticleDepth, current_loc: AbsoluteArticleLocation, meta: dict) -> Any:
        """
        Item / Subitem1 / Subitem2 のうち、現在階層に対応する1ノードを読み取り、
        本文・子要素・座標を含んだモデルへ変換する。
        """
        num_str = child_node.get(ATTR_NUM, '')
        next_loc = current_loc.update_inner_location(current_depth, num_str)
        self._current_element_locations.append(next_loc)

        # 次の階層のEnumを動的に進める（ITEM ➔ SUB_ITEM_1 ➔ SUB_ITEM_2 ➔ None）
        next_depth = self._next_depth(current_depth)

        # 再帰の力により、さらに深い下流階層の子供たちをドミノ式に自動回収
        children = self._parse_list_tree(child_node, next_depth, next_loc)

        title_node = child_node.find(meta["title_tag"], recursive=False)
        title_text = title_node.get_text() if title_node else ""

        body = self._parse_block_sentence(child_node, meta["wrapper_tag"])

        return self._create_list_element(
            depth=current_depth,
            num=num_str,
            title=title_text,
            location=next_loc,
            body=body,
            children=children,
        )

    @staticmethod
    def _next_depth(current_depth: ArticleDepth) -> Optional[ArticleDepth]:
        next_index = current_depth.index + 1
        if next_index >= len(ArticleDepth):
            return None
        return ArticleDepth.from_index(next_index)

    @staticmethod
    def _create_list_element(
            depth: ArticleDepth,
            num: str,
            title: str,
            location: AbsoluteArticleLocation,
            body: BlockSentenceBase,
            children: List[Any],
    ) -> Any:
        if depth == ArticleDepth.ITEM:
            return Item(num=num, title=title, location=location, body=body, children=children)

        if depth == ArticleDepth.SUB_ITEM_1:
            return Subitem1(num=num, title=title, location=location, body=body, children=children)

        if depth == ArticleDepth.SUB_ITEM_2:
            return Subitem2(num=num, title=title, location=location, body=body, children=children)

        raise ValueError(f"Unsupported list depth: {depth}")


"""
<Article Num="1_2">
  <ArticleCaption>（定義）</ArticleCaption>
  <ArticleTitle>第一条の二</ArticleTitle>
  <Paragraph Num="1">
    <ParagraphNum/>
    <ParagraphSentence>
      <Sentence Num="1" WritingMode="vertical">この法律において、次の各号に掲げる用語の意義は、それぞれ当該各号に定めるところによる。</Sentence>
    </ParagraphSentence>
    <Item Num="1">
      <ItemTitle>一</ItemTitle>
      <ItemSentence>
        <Column Num="1">
          <Sentence Num="1" WritingMode="vertical">登記簿</Sentence>
        </Column>
        <Column Num="2">
          <Sentence Num="1" WritingMode="vertical">商法、会社法その他の法律の規定により登記すべき事項が記録される帳簿であつて、磁気ディスク（これに準ずる方法により一定の事項を確実に記録することができる物を含む。）をもつて調製するものをいう。</Sentence>
        </Column>
      </ItemSentence>
    </Item>
    <Item Num="2">
      <ItemTitle>二</ItemTitle>
      <ItemSentence>
        <Column Num="1">
          <Sentence Num="1" WritingMode="vertical">変更の登記</Sentence>
        </Column>
        <Column Num="2">
          <Sentence Num="1" WritingMode="vertical">登記した事項に変更を生じた場合に、商法、会社法その他の法律の規定によりすべき登記をいう。</Sentence>
        </Column>
      </ItemSentence>
    </Item>
    <Item Num="3">
      <ItemTitle>三</ItemTitle>
      <ItemSentence>
        <Column Num="1">
          <Sentence Num="1" WritingMode="vertical">消滅の登記</Sentence>
        </Column>
        <Column Num="2">
          <Sentence Num="1" WritingMode="vertical">登記した事項が消滅した場合に、商法、会社法その他の法律の規定によりすべき登記をいう。</Sentence>
        </Column>
      </ItemSentence>
    </Item>
    <Item Num="4">
      <ItemTitle>四</ItemTitle>
      <ItemSentence>
        <Column Num="1">
          <Sentence Num="1" WritingMode="vertical">商号</Sentence>
        </Column>
        <Column Num="2">
          <Sentence Num="1" WritingMode="vertical">商法第十一条第一項又は会社法第六条第一項に規定する商号をいう。</Sentence>
        </Column>
      </ItemSentence>
    </Item>
  </Paragraph>
</Article>
</Chapter>
<Chapter Num="1_2">
<ChapterTitle>第一章の二　登記所及び登記官</ChapterTitle>
<Article Num="1_3">
  <ArticleCaption>（登記所）</ArticleCaption>
  <ArticleTitle>第一条の三</ArticleTitle>
  <Paragraph Num="1">
    <ParagraphNum/>
    <ParagraphSentence>
      <Sentence Num="1" WritingMode="vertical">登記の事務は、当事者の営業所の所在地を管轄する法務局若しくは地方法務局若しくはこれらの支局又はこれらの出張所（以下単に「登記所」という。）がつかさどる。</Sentence>
    </ParagraphSentence>
  </Paragraph>
</Article>
"""
