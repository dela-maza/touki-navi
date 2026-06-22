# touki-navi/parser/article_xml.py
from typing import Any
from bs4 import BeautifulSoup, Tag
from app.article.constants.enums import LawType, ArticleDepth
from app.article.models.article_loc import FullLocation, ArticleLocation
from app.article.models.sentence import Sentence
from app.article.models.article_element import ArticleElement
from app.article.models.article import Article
from app.article.constants.enums import SentenceType

class ArticleXMLParser:
    @staticmethod
    def parse_file(xml_path: str, law_type: LawType) -> list[Article]:
        with open(xml_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'xml')

        article_nodes = soup.find_all('Article')
        articles = []

        for node in article_nodes:
            # 条文の構築
            art: Article = ArticleXMLParser._parse_single_article(node, law_type)
            # 解析が終わった後に「解決（Resolve）」を一気に実行
            articles.append(art.resolve_all())

        return articles

    @staticmethod
    def _create_element(node: Tag, depth: ArticleDepth, location: FullLocation) -> ArticleElement:
        """
        各階層（項・号・目・目2）の共通パース処理。
        直下のSentenceを収集し、無ければColumn（表形式）を結合してArticleElementを生成する。
        （PyCharmの重複コード警告対策および可読性向上のための分離メソッド）
        """
        num_str = node.get('Num', '')  # 'イ' -> '1' , '（１）' ->'1'
        sentences :list[Sentence]= []

        # 1. 通常のSentenceをスキャン
        for st_node in node.find_all('Sentence', recursive=False):
            sentences.append(Sentence(
                num=st_node.get('Num', '1'),
                raw_text=st_node.get_text(),
                resolved_text="",
                sentence_node=st_node,
                sentence_type=SentenceType.SENTENCE
            ))

        # 2. Columnをスキャン（結合せず、バラのまま型を変えて追加する！）
        for col_node in node.find_all('Column', recursive=False):
            sentences.append(Sentence(
                num=col_node.get('Num', '1'),  # xmlからNum属性（1や2）をそのまま取得！
                raw_text=col_node.get_text(),
                resolved_text="",
                sentence_node=col_node,
                sentence_type=SentenceType.COLUMN  # ここでアイデンティティを確立
            ))

        return ArticleElement(
            depth=depth,
            num=num_str,
            location=location,
            title="",
            sentences=sentences
        )

    @staticmethod
    def _parse_single_article(node: Tag, law_type: LawType) -> Article:
        article_num = node.get('Num', '')

        # 見出し（ArticleCaption）とタイトル（ArticleTitle）の取得
        caption_node = node.find('ArticleCaption')
        article_caption = caption_node.get_text() if caption_node else ""

        article_title = node.find('ArticleTitle').get_text() if node.find('ArticleTitle') else ""

        base_location = FullLocation(
            law_type=law_type,
            article_num=article_num,
            relative_loc=ArticleLocation()
        )

        paragraphs = []

        # =================================================================
        # 1層目: 項 (Paragraph) のループ
        # =================================================================
        for pg_node in node.find_all('Paragraph', recursive=False):
            pg_num: Any = pg_node.get('Num', '1')
            pg_val: int = int(pg_num) if pg_num.isdigit() else 1
            pg_location: FullLocation = base_location.update_relative(ArticleDepth.PARAGRAPH, pg_val)

            # 共通メソッド化により1行でスッキリ生成
            pg_element = ArticleXMLParser._create_element(pg_node, ArticleDepth.PARAGRAPH, pg_location)

            # =============================================================
            # 2層目: 号 (Item) のループ
            # =============================================================
            for item_node in pg_node.find_all('Item', recursive=False):
                item_num = item_node.get('Num', '')
                item_val: int = int(item_num) if item_num.isdigit() else 1
                item_location: FullLocation = pg_location.update_relative(ArticleDepth.ITEM, item_val)

                item_element = ArticleXMLParser._create_element(item_node, ArticleDepth.ITEM, item_location)

                # =========================================================
                # 3層目: 目 (Subitem1) のループ
                # =========================================================
                for si1_node in item_node.find_all('Subitem1', recursive=False):
                    si1_num = si1_node.get('Num', '1')
                    # XML側がすでに Num="1" と数字で持ってくれているので、intにするだけでOK！
                    si1_val = int(si1_num) if si1_num.isdigit() else 1
                    si1_location: FullLocation = item_location.update_relative(ArticleDepth.SUB_ITEM_1, si1_val)

                    si1_element = ArticleXMLParser._create_element(si1_node, ArticleDepth.SUB_ITEM_1, si1_location)

                    # =====================================================
                    # 4層目: 目2 (Subitem2) のループ
                    # =====================================================
                    for si2_node in si1_node.find_all('Subitem2', recursive=False):
                        si2_num = si2_node.get('Num', '1')
                        # 目2（（一）（二）など）も同様にXML上は Num="1" になっているためint化
                        si2_val = int(si2_num) if si2_num.isdigit() else 1
                        si2_location: FullLocation = si1_location.update_relative(ArticleDepth.SUB_ITEM_2, si2_val)

                        si2_element = ArticleXMLParser._create_element(si2_node, ArticleDepth.SUB_ITEM_2, si2_location)

                        # 最下層（目2）を 目1 の子要素として追加
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
