# app/article/constants/inline_marks.py

# Sentence 内に埋め込む、location token ではない半角ASCII mark の種類。
# 例: <q=ただし書>
INLINE_MARK_QUALIFIER = "q"
# 例: <h=law:kai>
INLINE_MARK_HINT = "h"
# 例: <c=及び>
INLINE_MARK_CONNECTOR = "c"
# 例: <r=から>
INLINE_MARK_RANGE_CONNECTOR = "r"

# location に近い修飾語。3枠 reference mark の直後に続く場合だけ <q=...> にする。
REFERENCE_QUALIFIER_TEXTS = (
    "ただし書き",
    "ただし書",
    "本文",
    "前段",
    "後段",
)

# Reference 同士の連鎖を維持しうる接続語。
CONNECTOR_TEXTS = (
    "若しくは",
    "並びに",
    "及び",
    "又は",
    "、",
)

# 複数 Reference をまたいで range を作りうる接続語。
RANGE_CONNECTOR_TEXTS = (
    "から",
)

# gap 判定で、参照連鎖を切らない語として扱う全 connector。
REFERENCE_CHAIN_TEXTS = CONNECTOR_TEXTS + RANGE_CONNECTOR_TEXTS

# UI / semantic hint 用の mark key。
# 例: <h=law:kai>
HINT_KEY_LAW = "law"
