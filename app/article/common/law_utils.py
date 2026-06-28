# common/law_utiles.py
import re
from kanjize import kanji2number
import unicodedata
from app.article.models.article_loc import ArticleDepth

def to_hankaku(text: str) -> str:
    """全角文字を半角文字に変換する（NFKC正規化）"""
    return unicodedata.normalize('NFKC', text)

def to_zenkaku(s: str) -> str:
    """半角数字を全角数字に変換する"""
    return s.translate(str.maketrans('0123456789', '０１２３４５６７８９'))


# 1. 基準となる「第◯条」「第◯項」「第◯号」および「前◯条」「後◯条」
BASE_UNIT_RE = re.compile(r'([第前後])([一二三四五六七八九十百千万]+)([条項号])')

# 2. 直後に続く「の◯」
SUB_UNIT_RE = re.compile(r'([条項号]|(?<=[条項号０-９])の)([一二三四五六七八九十百千万]+)')

KANJI_NUMBER_RE = re.compile(r"[一二三四五六七八九十百千万]")


def convert_law_numbers(text: str) -> str:
    # ステップ1: 主番号の変換 (例: 第三十三条 -> 第３３条、前三条 -> 前３条)
    def replace_base(match):
        prefix = match.group(1)
        num = kanji2number(match.group(2))
        num_zen = to_zenkaku(str(num))
        unit = match.group(3)
        return f"{prefix}{num_zen}{unit}"

    processed_text = BASE_UNIT_RE.sub(replace_base, text)

    # ステップ2: 枝番の変換 (例: 条の十三 -> 条の１３)
    def replace_sub(match):
        unit_or_prefix = match.group(1)
        sub_num = kanji2number(match.group(2))
        sub_num_zen = to_zenkaku(str(sub_num))
        # 内部ID用ではなく、表示用なので「の」を維持する
        return f"{unit_or_prefix}{sub_num_zen}"

    # 枝番が連続する場合（の十三の二）に対応
    # 2回目以降の「の」にもマッチするように正規表現を調整しています
    while SUB_UNIT_RE.search(processed_text):
        new_text = SUB_UNIT_RE.sub(replace_sub, processed_text)
        if new_text == processed_text:
            break
        processed_text = new_text

    return processed_text


def try_kanji_to_id(value: str, level: ArticleDepth = None) -> tuple[str, bool]:
    """
    漢数字を含む文字列だけを kanji_to_id() でID用の半角数値・記号に変換する。

    :return: (変換後の文字列, 変換したかどうか)

    例:
        「第一条」 -> ("1", True)
        「前条」 -> ("前条", False)
    """
    if not KANJI_NUMBER_RE.search(value):
        return value, False

    return kanji_to_id(value, level), True


def kanji_to_id(value: str, level: ArticleDepth = None) -> str:
    """
    漢数字や記号をID用の半角数値・記号に変換する。
    例: 「第六条」 -> "6", 「第一項」 -> "1", 「イ」 -> "1"
    """
    # --- 1. 条・項・号 (None=ARTICLE, PARAGRAPH, ITEM) ---
    # ReferenceParser の定義上、ARTICLE は None で渡される
    if level in (None, ArticleDepth.PARAGRAPH, ArticleDepth.ITEM):
        # 「第」「条」「項」「号」を削る
        content = re.sub(r"[第条項号]", "", value)

        # 枝番（の二 など）が含まれている場合を考慮
        parts = content.split("の")
        id_list = []
        for p in parts:
            if p:
                try:
                    id_list.append(str(kanji2number(p)))
                except:
                    id_list.append(p)  # 数値化できない場合はそのまま
        return "_".join(id_list)

    # --- 2. 目 (SUB_ITEM_1: イ, ロ, ハ...) ---
    elif level == ArticleDepth.SUB_ITEM_1:
        iroha = "イロハニホヘトチリヌルヲワカヨタレソツネナラムウヰノオクヤマケフコエテアサキユメミシヱヒモセスン"
        index = iroha.find(value)
        return str(index + 1) if index != -1 else value

    # --- 3. 目2 (SUB_ITEM_2: （一）, （二）...) ---
    elif level == ArticleDepth.SUB_ITEM_2:
        # 括弧を除去
        content = value.replace("（", "").replace("）", "")
        try:
            # 漢数字であれば数値化
            return str(kanji2number(content))
        except:
            # 全角数字等の場合は半角化（to_hankakuの実装に依存）
            return to_hankaku(content)

    return value
