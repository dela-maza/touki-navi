# app/article/constants/xml_tags.py
import re
import unicodedata
from app.article.constants.enums import ArticleDepth, TocDepth

# =================================================================
# 1. 階層を問わず、法令XML全体で不動の「コア仕様」定数
# =================================================================
TAG_SENTENCE = "Sentence"
TAG_COLUMN = "Column"
ATTR_NUM = "Num"
TAG_TOC = "TOC"
TAG_TOC_LABEL = "TOCLabel"
TAG_TOC_SUPPL_PROVISION = "TOCSupplProvision"
TAG_SUPPL_PROVISION_LABEL = "SupplProvisionLabel"
TAG_ARTICLE_RANGE = "ArticleRange"

# =================================================================
# 1.5. 目・細目の参照表記ルール（実装は後で移行）
# =================================================================
class Subitem1Rule:
    """法令の「目（SUB_ITEM_1）」にあたるイロハ記号を管理・バリデーションするクラス"""

    # 💡 階層の深さを背骨のEnumと同期
    DEPTH: ArticleDepth = ArticleDepth.SUB_ITEM_1

    CHARS: str = "イロハニホヘトチリヌルヲ"
    MAP: dict[str, str] = {char: str(i + 1) for i, char in enumerate(CHARS)}

    # クラス読み込み時に一度だけコンパイルして高速化
    _PATTERN: re.Pattern = re.compile(rf"(?<![\[ァ-ヶー])([{CHARS}])(?![\]ァ-ヶー])")

    @classmethod
    def get_pattern(cls) -> re.Pattern:
        return cls._PATTERN


class Subitem2Rule:
    """法令の「細目（SUB_ITEM_2）」にあたるカッコ数字（（１）、（２）等）を管理・バリデーションするクラス"""

    DEPTH: ArticleDepth = ArticleDepth.SUB_ITEM_2

    # 正式な法令本文に出てくる全角カッコ数字のみを検知する
    CHARS_PATTERN: str = r"（[０-９]+）"
    _PATTERN: re.Pattern = re.compile(rf"({CHARS_PATTERN})")

    @classmethod
    def get_pattern(cls) -> re.Pattern:
        return cls._PATTERN

    @classmethod
    def to_normalized_arabic(cls, text: str) -> str:
        """生テキスト（例:「（１）」）を、標準ライブラリで綺麗な半角の「(1)」に正規化する"""
        # NFKCモードにより、全角の「（１）」は一発で半角の「(1)」に変換される
        return unicodedata.normalize("NFKC", text)

    @classmethod
    def to_id(cls, text: str) -> str:
        """生テキストからカッコを除外し、評価・検索用の純粋な半角数字ID（「1」）を文字列で返す"""
        # 1. ライブラリで一旦、綺麗な半角の "(1)" や "(2)" にする
        normalized = unicodedata.normalize("NFKC", text)

        # 2. カッコ数字であることは確定しているので、最初と最後のカッコを削って数字だけを取り出す
        # 例: "(1)" -> "1"
        return normalized[1:-1]


# =================================================================
# 2. 階層ごとに異なる「泥臭いドメイン知識」の完全一元管理マップ
# =================================================================
XML_TAG_MAP = {
    # 💡 Article（条）レベルのタグ知識もここに完全集約
    "article": {
        "tag_name": "Article",
        "caption_tag": "ArticleCaption",
        "title_tag": "ArticleTitle",
    },
    "paragraph": {
        "depth": ArticleDepth.PARAGRAPH,
        "tag_name": "Paragraph",
        "title_tag": "ParagraphNum",       # 項だけNumタグという歪み
        "wrapper_tag": "ParagraphSentence",
        "pattern": re.compile(r"第[一二三四五六七八九十百千万\d]+項")
    },
    "item": {
        "depth": ArticleDepth.ITEM,
        "tag_name": "Item",
        "title_tag": "ItemTitle",
        "wrapper_tag": "ItemSentence",
        "pattern": re.compile(r"第[一二三四五六七八九十百千万\d]+号")
    },
    "subitem1": {
        "depth": ArticleDepth.SUB_ITEM_1,
        "tag_name": "Subitem1",
        "title_tag": "Subitem1Title",
        "wrapper_tag": "Subitem1Sentence",
        "pattern": re.compile(r"(?:^|(?<=[^ァ-ヶー]))[イロハニホヘトチリヌルヲ](?=$|[^ァ-ヶー])")
    },
    "subitem2": {
        "depth": ArticleDepth.SUB_ITEM_2,
        "tag_name": "Subitem2",
        "title_tag": "Subitem2Title",
        "wrapper_tag": "Subitem2Sentence",
        "pattern": re.compile(r"（[０-９]+）")
    }
}


def get_xml_tag_meta_by_depth(depth: ArticleDepth) -> dict:
    for meta in XML_TAG_MAP.values():
        if meta.get("depth") == depth:
            return meta
    raise KeyError(depth)


# =================================================================
# 3. TOC階層ごとのXMLタグ知識
# =================================================================
TOC_XML_TAG_MAP = {
    "part": {
        "depth": TocDepth.PART,
        "tag_name": "TOCPart",
        "body_tag": TocDepth.PART.tag_name,
        "title_tag": "PartTitle",
    },
    "chapter": {
        "depth": TocDepth.CHAPTER,
        "tag_name": "TOCChapter",
        "body_tag": TocDepth.CHAPTER.tag_name,
        "title_tag": "ChapterTitle",
    },
    "section": {
        "depth": TocDepth.SECTION,
        "tag_name": "TOCSection",
        "body_tag": TocDepth.SECTION.tag_name,
        "title_tag": "SectionTitle",
    },
    "subsection": {
        "depth": TocDepth.SUB_SECTION,
        "tag_name": "TOCSubsection",
        "body_tag": TocDepth.SUB_SECTION.tag_name,
        "title_tag": "SubsectionTitle",
    },
    "division": {
        "depth": TocDepth.DIVISION,
        "tag_name": "TOCDivision",
        "body_tag": TocDepth.DIVISION.tag_name,
        "title_tag": "DivisionTitle",
    },
}


def get_toc_xml_tag_meta_by_depth(depth: TocDepth) -> dict:
    for meta in TOC_XML_TAG_MAP.values():
        if meta.get("depth") == depth:
            return meta
    raise KeyError(depth)


def get_toc_xml_tag_meta_by_toc_tag(tag_name: str) -> dict:
    for meta in TOC_XML_TAG_MAP.values():
        if meta.get("tag_name") == tag_name:
            return meta
    raise KeyError(tag_name)


def get_toc_xml_tag_meta_by_body_tag(tag_name: str) -> dict:
    for meta in TOC_XML_TAG_MAP.values():
        if meta.get("body_tag") == tag_name:
            return meta
    raise KeyError(tag_name)
