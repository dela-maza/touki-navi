# touki-navi/parser/article_xml.py
from bs4 import BeautifulSoup
from app.article.constants.enums import LawType, ArticleDepth
from app.article.models.article_loc import FullLocation, ArticleLocation
from app.article.models.sentence import Sentence
from app.article.models.article_element import ArticleElement
from app.article.models.article import Article


class ArticleXMLParser:
    @staticmethod
    def parse_file(xml_path: str, law_type: LawType) -> list[Article]:
        with open(xml_path, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f, 'xml')

        article_nodes = soup.find_all('Article')
        articles = []

        for node in article_nodes:
            # 条文の構築
            art = ArticleXMLParser._parse_single_article(node, law_type)
            # 解析が終わった後に「解決（Resolve）」を一気に実行
            # これにより、Viewでの使い回し汚染を防ぐ
            articles.append(art.resolve_all())

        return articles

    @staticmethod
    def _parse_single_article(node, law_type: LawType) -> Article:
        article_num = node.get('Num', '')
        article_title = node.find('ArticleTitle').get_text() if node.find('ArticleTitle') else ""

        base_location = FullLocation(
            law_type=law_type,
            article_num=article_num,
            relative_loc=ArticleLocation()
        )

        paragraphs = []
        for pg_node in node.find_all('Paragraph', recursive=False):
            pg_num = pg_node.get('Num', '1')
            pg_val = int(pg_num) if pg_num.isdigit() else 1
            pg_location = base_location.update_relative(ArticleDepth.PARAGRAPH, pg_val)

            sentences = []
            for st_node in pg_node.find_all('Sentence'):
                sentences.append(Sentence(
                    num=st_node.get('Num', '1'),
                    raw_text=st_node.get_text(),
                    resolved_text="",  # resolve_references() で後から埋める
                    sentence_node=st_node
                ))

            paragraphs.append(ArticleElement(
                depth=ArticleDepth.PARAGRAPH,
                num=pg_num,
                location=pg_location,
                title="",
                sentences=sentences
            ))

        return Article(
            num=article_num,
            law_type=law_type,
            title=article_title,
            caption="",
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