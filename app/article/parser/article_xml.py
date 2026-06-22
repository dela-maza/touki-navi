# touki-navi/parser/article_xml.py
from typing import List, Optional
from bs4 import BeautifulSoup, Tag
from app.article.constants.enums import LawType, ArticleDepth, SentenceType
from app.article.models.article_loc import FullLocation, ArticleLocation
from app.article.models.sentence import Sentence
from app.article.models.subdivision import Paragraph, Item, Subitem1, Subitem2
from app.article.models.article import Article


class ArticleXMLParser:
    @staticmethod
    def parse_file(xml_path: str, law_type: LawType) -> List[Article]:
        with open(xml_path, 'r', encoding='utf-8') as f:
            soup: BeautifulSoup = BeautifulSoup(f, 'xml')

        article_nodes: List[Tag] = soup.find_all('Article')
        articles: List[Article] = []

        for node in article_nodes:
            art: Article = ArticleXMLParser._parse_single_article(node, law_type)
            # 解析終了後に参照解決を一気に実行
            articles.append(art.resolve_all())

        return articles

    @staticmethod
    def _create_sentences(node: Tag) -> List[Sentence]:
        """
        指定されたノード直下一親等のSentenceおよびColumnをスキャンし、
        Sentenceオブジェクトのリストを生成する共通メソッド。
        """
        sentences: List[Sentence] = []

        # 1. 通常のSentenceをスキャンし、SentenceType.SENTENCE を付与
        for st_node in node.find_all('Sentence', recursive=False):
            sentences.append(Sentence(
                num=st_node.get('Num', '1'),
                raw_text=st_node.get_text(),
                resolved_text="",
                sentence_node=st_node,
                sentence_type=SentenceType.SENTENCE
            ))

        # 2. Column（表形式）をスキャンし、SentenceType.COLUMN を付与
        for col_node in node.find_all('Column', recursive=False):
            sentences.append(Sentence(
                num=col_node.get('Num', '1'),
                raw_text=col_node.get_text(),
                resolved_text="",
                sentence_node=col_node,
                sentence_type=SentenceType.COLUMN
            ))

        return sentences

    @staticmethod
    def _parse_single_article(node: Tag, law_type: LawType) -> Article:
        article_num: str = node.get('Num', '')

        caption_node: Optional[Tag] = node.find('ArticleCaption')
        article_caption: str = caption_node.get_text() if caption_node else ""

        title_node: Optional[Tag] = node.find('ArticleTitle')
        article_title: str = title_node.get_text() if title_node else ""

        # 全てstr管理化された絶対住所オブジェクトを生成
        base_location: FullLocation = FullLocation(
            law_type=law_type,
            article_num=article_num,
            relative_loc=ArticleLocation()
        )

        paragraphs: List[Paragraph] = []

        # =================================================================
        # 1層目: 項 (Paragraph) のループ
        # =================================================================
        for pg_node in node.find_all('Paragraph', recursive=False):
            pg_num: str = pg_node.get('Num', '1')
            pg_location: FullLocation = base_location.update_relative(ArticleDepth.PARAGRAPH, pg_num)

            pg_element = Paragraph(
                num=pg_num,
                location=pg_location,
                sentences=ArticleXMLParser._create_sentences(pg_node)
            )

            # =============================================================
            # 2層目: 号 (Item) のループ
            # =============================================================
            for item_node in pg_node.find_all('Item', recursive=False):
                item_num: str = item_node.get('Num', '')
                item_location: FullLocation = pg_location.update_relative(ArticleDepth.ITEM, item_num)

                item_element = Item(
                    num=item_num,
                    location=item_location,
                    sentences=ArticleXMLParser._create_sentences(item_node)
                )

                # =========================================================
                # 3層目: 目 (Subitem1) のループ
                # =========================================================
                for si1_node in item_node.find_all('Subitem1', recursive=False):
                    si1_num: str = si1_node.get('Num', '')
                    si1_location: FullLocation = item_location.update_relative(ArticleDepth.SUB_ITEM_1, si1_num)

                    si1_element = Subitem1(
                        num=si1_num,
                        location=si1_location,
                        sentences=ArticleXMLParser._create_sentences(si1_node)
                    )

                    # =====================================================
                    # 4層目: 目2 (Subitem2) のループ
                    # =====================================================
                    for si2_node in si1_node.find_all('Subitem2', recursive=False):
                        si2_num: str = si2_node.get('Num', '')
                        si2_location: FullLocation = si1_location.update_relative(ArticleDepth.SUB_ITEM_2, si2_num)

                        si2_element = Subitem2(
                            num=si2_num,
                            location=si2_location,
                            sentences=ArticleXMLParser._create_sentences(si2_node)
                        )

                        # 目2 を 目1 の子要素として追加
                        si1_element.children.append(si2_element)

                    # 目1 を 号 の子要素として追加
                    item_element.children.append(si1_element)

                # 号 を 項 の子要素として追加
                pg_element.children.append(item_element)

            # 項 を 条文 の段落リストに追加
            paragraphs.append(pg_element)

        return Article(
            num=article_num,
            law_type=law_type,
            title=article_title,
            caption=article_caption,
            paragraphs=paragraphs
        )

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
