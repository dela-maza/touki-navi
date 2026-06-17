# test_utils.py
from app.article.common.law_utils import convert_law_numbers, kanji_to_id
from app.article.models.article_loc import ArticleDepth


def test_law_utils():
    print("=== Law Utils 検認開始 ===")

    # 1. 表示用変換のテスト (convert_law_numbers)
    test_cases_display = {
        "第百十条の二十二": "第１１０条の２２",
        "第百十一条の二の三": "第１１１条の２の３",
        "第一条の二第三項": "第１条の２第３項",
        "商法第十一条": "商法第１１条"
    }

    print("\n[1] 表示用変換 (漢数字 -> 全角数字):")
    for k, v in test_cases_display.items():
        result = convert_law_numbers(k)
        status = "OK" if result == v else f"NG (結果: {result})"
        print(f"  {k} -> {result} [{status}]")

    # 2. ID用変換のテスト (kanji_to_id)
    print("\n[2] ID用変換 (漢数字/記号 -> 半角ID):")

    # 条・項・号
    print(f"  条: 第百十一条の二 -> {kanji_to_id('第百十一条の二')} (期待: 111_2)")
    print(f"  項: 第五項 -> {kanji_to_id('第五項', ArticleDepth.PARAGRAPH)} (期待: 5)")
    print(f"  号: 第百二号 -> {kanji_to_id('第百二号', ArticleDepth.ITEM)} (期待: 102)")

    # 目 (イロハ)
    print(f"  目1: ハ -> {kanji_to_id('ハ', ArticleDepth.SUB_ITEM_1)} (期待: 3)")
    print(f"  目1: ヌ -> {kanji_to_id('ヌ', ArticleDepth.SUB_ITEM_1)} (期待: 10)")

    # 目2 (（一）（二）)
    print(f"  目2: （十二） -> {kanji_to_id('（十二）', ArticleDepth.SUB_ITEM_2)} (期待: 12)")


if __name__ == "__main__":
    test_law_utils()