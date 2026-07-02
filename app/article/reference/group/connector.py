# app/article/reference/group/connector.py
from dataclasses import dataclass


@dataclass
class ReferenceConnector:
    """
    Reference と Reference の間に出現する通常の接続語。

    例:
        <c=及び>
        <c=並びに>

    次の Reference が直前の Reference を引き継げるかを判断するために使う。
    Reference そのものではない。
    """

    text: str


@dataclass
class ReferenceRangeConnector:
    """
    Reference と Reference の間に出現する range 用の接続語。

    例:
        <r=から>

    前後の Reference を範囲として解釈する可能性を残すために使う。
    Reference そのものではない。
    """

    text: str
