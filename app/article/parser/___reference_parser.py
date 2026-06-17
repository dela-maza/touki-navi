# parser/___reference_parser.py
from app.article.models.law import LawType

import re
from app.article.common.law_utils import kanji_to_id, law_to_id  # law_to_idを定義想定
from app.article.models.article_loc import ArticleDepth
from app.article.models.law import LawType


class ReferenceParser:
    # 栞（しおり）の初期状態 [法, 条, 項, 号, 目1, 目2]
    _loc = ["", "", "0", "0", "0", "0"]

    @classmethod
    def to_chunked_str(cls, text: str) -> str:
        # 処理ごとに栞をリセット（一文単位）
        cls._loc = ["", "", "0", "0", "0", "0"]

        processed = text

        # 1. 法律名（Law）のマークアップとID決定
        def _law_handler(match):
            law_name = match.group(0)
            law_id = law_to_id(law_name)  # '会社法' -> 'kai'
            cls._loc[0] = law_id
            cls._loc[1:] = ["", "0", "0", "0", "0"]  # 下位リセット
            return f"[[l-{law_id}:{law_name}]]"

        for law in LawType:
            processed = re.sub(rf"(?<!\[\[){re.escape(law.name_jp)}", _law_handler, processed)

        # 2. 条・項・号のマークアップとID決定
        def _unit_handler(match):
            tag = match.group(1)  # 'a', 'p', 'i'
            label = match.group(2)  # '第十一条' など

            if tag == 'a':
                val = kanji_to_id(label)
                cls._loc[1] = val
                cls._loc[2:] = ["0", "0", "0", "0"]
            elif tag == 'p':
                val = kanji_to_id(label, ArticleDepth.PARAGRAPH)
                cls._loc[2] = val
                cls._loc[3:] = ["0", "0", "0"]
            # ... 号も同様

            # この瞬間に ID を埋め込んでしまう
            full_id = f"{cls._loc[0]}.{cls._loc[1]}-{'.'.join(cls._loc[2:])}"
            return f"[[{tag}-{val}:{label}]]"  # ID付きの箱にする

        # まずは単純に囲う
        processed = re.sub(r"(第[一二三四五六七八九十百千万]+条)", r"[[a:\1]]", processed)
        processed = re.sub(r"(第[一二三四五六七八九十百千万]+項)", r"[[p:\1]]", processed)

        # コールバックでIDを付与していく
        processed = re.sub(r"\[\[([api]):([^\]]+)\]\]", _unit_handler, processed)

        # 3. 枝番の吸収（ここでもIDを更新）
        def _branch_merge(match):
            tag, current_id, label, branch = match.groups()
            new_label = label + branch
            new_id = kanji_to_id(new_label)  # '第十一条の二' -> '11_2'

            # 栞も更新しておく
            if tag == 'a': cls._loc[1] = new_id

            return f"[[{tag}-{new_id}:{new_label}]]"

        branch_pattern = r"\[\[([api])-([\d_]+):([^\]]+)\]\](の[一二三四五六七八九十]+)"
        while re.search(branch_pattern, processed):
            processed = re.sub(branch_pattern, _branch_merge, processed)

        return processed