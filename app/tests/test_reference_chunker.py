import pytest
from app.article.reference.chunker import ReferenceChunker


class TestReferenceChunker:
    @pytest.mark.parametrize("input_text, expected", [
        # 1. 基本的な形
        (
                "会社法第十一条",
                "[[会社法][第十一条]]"
        ),
        # 2. 枝番（の）の吸い込み
        (
                "会社法第十一条の二の三",
                "[[会社法][第十一条の二の三]]"
        ),
        # 3. 複数の階層と連結
        (
                "商法第十一条の二第二項第一号",
                "[[商法][第十一条の二][第二項][第一号]]"
        ),
        # 4. 目（イロハ）と細目（（１））
        (
                "第百条第一項第三号イ（１）",
                "[[第百条][第一項][第三号][イ][（１）]]"
        ),
        # 5. 「同法」の処理
        (
                "同法第十条",
                "[[同法][第十条]]"
        ),
        # 6. 複雑な混在（一二の一）
        (
                "第一条の一二の一",
                "[[第一条の一二の一]]"
        ),
        # 7. 参照が複数ある一文
        (
                "会社法第六条及び商法第七条",
                "[[会社法][第六条]]及び[[商法][第七条]]"
        ),
    ])
    def test_to_chunked_str(self, input_text, expected):
        result = ReferenceChunker.to_chunked_str(input_text)
        assert result == expected
