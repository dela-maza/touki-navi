# app/article/reference/group/occurrence.py
from dataclasses import dataclass

from app.article.models.reference import Reference


@dataclass
class OccurrenceBase:
    """
    Sentence.marked_text を先頭から読んだときに出現する要素の共通インターフェイス。

    Reference だけでなく、connector、range connector、qualifier、通常テキストも、
    出現順を保ったまま同じ list に入れるための基底クラスである。
    """

    start_index: int
    end_index: int


@dataclass
class ReferenceOccurrence(OccurrenceBase):
    """
    Sentence 内に出現した Reference の位置情報と解析結果を保持する。

    Reference は TokenGroup に近い軽い器に留め、
    TokenGroup の前後関係から生じる情報はこのクラスで扱う。
    """

    reference: Reference
    base_axis: str | None = None
    semantic_mark_text: str | None = None


@dataclass
class ConnectorOccurrence(OccurrenceBase):
    """
    Reference 間に出現した通常 connector を表す。

    例:
        <c=及び>
        <c=並びに>

    この要素は、次に出現する Reference が last_reference_location を引き継げるかを判断する材料になる。
    """

    text: str


@dataclass
class RangeConnectorOccurrence(OccurrenceBase):
    """
    複数 Reference をまたぐ range connector を表す。

    例:
        <r=から>

    この要素は、前後の Reference を range として解釈する可能性を残すために保持する。
    """

    text: str


@dataclass
class QualifierOccurrence(OccurrenceBase):
    """
    Reference の直後に出現した location qualifier を表す。

    例:
        <q=ただし書>
        <q=本文>

    この要素は、直前の Reference の参照先を限定する情報として扱う。
    """

    text: str


@dataclass
class HintOccurrence(OccurrenceBase):
    """
    UI / semantic hint 用の mark を表す。

    location 解析では基本的に使わない。
    marked_text 全体を一度分解するときには出現しうるが、location 解析用 occurrences からは落とす予定である。
    """

    text: str


@dataclass
class TextOccurrence(OccurrenceBase):
    """
    Reference / inline mark ではない通常テキストを表す。

    この要素は、参照連鎖を切る本文が Reference 間に存在したことを示すために使う。
    """

    text: str
