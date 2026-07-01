# app/article/services/article_builder.py
from collections.abc import Iterator
from dataclasses import dataclass

from app.article.constants.enums import LawType
from app.article.models.article import Article, Item, Subitem1, Subitem2
from app.article.models.article_loc import FullLocation
from app.article.models.index import ArticleIndex
from app.article.models.reference_group import SentenceReferenceGroup
from app.article.models.sentence import BlockSentenceBase, ColumnBlockSentence, PlainBlockSentence, Sentence


@dataclass
class ArticleBuilder:
    """
    XMLから生成されたArticleモデルに対して、参照解決などの後続処理をまとめて適用し、
    表示や検索に使いやすいArticleリストへ整えるためのサービスクラス。

    現時点では Sentence ごとに SentenceReferenceGroup を作り、Reference の出現順だけを保持する。
    """

    law_type: LawType
    article_index: ArticleIndex

    def build(self) -> list[Article]:
        """ArticleIndex が保持する Article に references を埋めて、完成した list[Article] を返す。"""
        for article in self.article_index.articles:
            self._resolve_article_references(article)

        return self.article_index.articles

    def _resolve_article_references(self, article: Article) -> None:
        """Article 1個分の ArticleElementLocationIndex を作り、配下の Sentence.references を更新する。"""
        for sentence, owner_location in self._iter_article_sentences(article):
            reference_group = SentenceReferenceGroup.create_object(
                sentence=sentence,
                this_sentence_location=owner_location,
            )
            sentence.references = reference_group.references

    def _iter_article_sentences(self, article: Article) -> Iterator[tuple[Sentence, FullLocation]]:
        """Article 配下の Sentence を、Sentence を所有する location と一緒に上から順番に返す。"""
        for paragraph in article.paragraphs:
            yield from self._iter_block_sentences(paragraph.body, paragraph.location)
            yield from self._iter_item_sentences(paragraph.items)

    def _iter_item_sentences(self, items: list[Item]) -> Iterator[tuple[Sentence, FullLocation]]:
        """Item 以下の Sentence を、Item -> Subitem1 -> Subitem2 の順に返す。"""
        for item in items:
            yield from self._iter_block_sentences(item.body, item.location)
            yield from self._iter_subitem1_sentences(item.children)

    def _iter_subitem1_sentences(self, subitems: list[Subitem1]) -> Iterator[tuple[Sentence, FullLocation]]:
        """Subitem1 以下の Sentence を、Subitem1 -> Subitem2 の順に返す。"""
        for subitem in subitems:
            yield from self._iter_block_sentences(subitem.body, subitem.location)
            yield from self._iter_subitem2_sentences(subitem.children)

    def _iter_subitem2_sentences(self, subitems: list[Subitem2]) -> Iterator[tuple[Sentence, FullLocation]]:
        """Subitem2 が持つ Sentence を返す。"""
        for subitem in subitems:
            yield from self._iter_block_sentences(subitem.body, subitem.location)

    @staticmethod
    def _iter_block_sentences(
            body: BlockSentenceBase,
            owner_location: FullLocation,
    ) -> Iterator[tuple[Sentence, FullLocation]]:
        """Plain / Column の違いを隠して、BlockSentenceBase 内の Sentence を返す。"""
        if isinstance(body, PlainBlockSentence):
            for sentence in body.sentences:
                yield sentence, owner_location
            return

        if isinstance(body, ColumnBlockSentence):
            for column_num in sorted(body.columns):
                for sentence in body.columns[column_num]:
                    yield sentence, owner_location
            return

        raise TypeError(f"unsupported sentence block: {type(body).__name__}")
