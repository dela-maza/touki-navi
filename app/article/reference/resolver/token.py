# reference/resolver/token.py

import re
from app.article.common.law_utils import kanji_to_id
from app.article.models.article_loc import ArticleDepth, FullLocation


class Token:
    def __init__(self, tag: str, offset: str, label: str):
        self.tag = tag  # "a", "p", "i", "s1", "s2"
        self.offset = offset  # 全て文字列("1", "1_2", "-1", "0"など)で一貫管理
        self.label = label  # "前条", "第一項の二" など元の文字列

    @classmethod
    def parse(cls, raw_content: str) -> "Token":
        # --- 1. 相対指定（前条等）・複数指定の直値マッピング（新規表現を追加） ---
        fixed_tokens = {
            "前条": ("a", "-1"),
            "同条": ("a", "0"),
            "次条": ("a", "1"),
            "前項": ("p", "-1"),
            "同項": ("p", "0"),
            "次項": ("p", "1"),
            "前号": ("i", "-1"),
            "同号": ("i", "0"),
            "次号": ("i", "1"),
            "各号": ("i", "each"),  # 複数解決（各号）トークンとしての識別子
        }
        if raw_content in fixed_tokens:
            # fixed_tokens 例　"前条" が　raw_content　に含まれている場合
            tag, offset = fixed_tokens[raw_content]
            return cls(tag=tag, offset=offset, label=raw_content)

        # --- 2. 絶対指定（条番号・枝番対応含む） ---
        if "条" in raw_content:
            return cls(tag="a", offset=str(kanji_to_id(raw_content)), label=raw_content)

        # 階層定義Enumから動的にマッピング（返り値はstr型で確定させる）
        for depth in ArticleDepth:
            if depth.label_jp in raw_content:
                return cls(tag=depth.short_name, offset=str(kanji_to_id(raw_content)), label=raw_content)


        # --- 3. 目・細目（イロハ・数字） ---
        if re.fullmatch(r"[イロハニホヘトチリヌルヲ]+", raw_content):
            return cls(tag="s1", offset=raw_content, label=raw_content)

        if re.fullmatch(r"（[０-９]+）", raw_content):
            table = str.maketrans("０１２３４５６７８９", "0123456789", "（）")
            offset = raw_content.translate(table)
            return cls(tag="s2", offset=offset, label=raw_content)

        return cls(tag="unknown", offset="0", label=raw_content)

    def get_article_depth(self) -> ArticleDepth:
        mapping = {
            "p": ArticleDepth.PARAGRAPH,
            "i": ArticleDepth.ITEM,
            "s1": ArticleDepth.SUB_ITEM_1,
            "s2": ArticleDepth.SUB_ITEM_2
        }
        return mapping.get(self.tag, ArticleDepth.PARAGRAPH)


# reference/resolver/token.py

class TokenGroup:
    def __init__(self, raw_segment: str, cur_location: FullLocation, last_ref_location: FullLocation):
        """
        引数に「不変の現在地 (cur_location)」と「文脈で変動する直近参照 (last_ref_location)」の双方を受け取る。
        """
        # [[会社法][第一条][第一項][第一号][イ][（１）]] ->  会社法][第一条][第一項][第一号][イ][（１）
        clean_segment = raw_segment.replace("[[", "").replace("]]", "")
        # 会社法][一条][一項][一号][イ][（１） -> "会社法","第一条","第一項","第一号","イ","（１）"
        self.raw_contents: list[str] = clean_segment.split("][")
        self.tokens: list[Token] = [Token.parse(c) for c in self.raw_contents]

        # 💡【二軸化適応】それぞれの基準座標をベースに移動先を個別に計算
        self.location_via_cur: FullLocation = self._cul_last_ref_location(cur_location)
        self.location_via_ref: FullLocation = self._cul_last_ref_location(last_ref_location)

        # 次のTokenGroupへ文脈を引き継ぐための、変動後の最新参照座標
        self.final_last_ref: FullLocation = self.location_via_ref

    def _cul_last_ref_location(self, last_ref_loc: FullLocation) -> FullLocation:
        """
        簡易判定の役割を維持しつつ、LocationShiftResolver(shift.py)が
        本格稼働するまでの繋ぎとして型安全（str）に処理する。
        """
        loc = last_ref_loc
        for token in self.tokens:
            if token.tag == "a":
                # 相対指定（"0", "-1"など）は本来LocationShiftResolverで処理するため、
                # ここでは絶対指定の文字列番号（"111"など）が来たらそのまま条を上書きするガードを入れる
                if token.offset not in ("0", "-1", "1"):
                    loc = loc.update_article(token.offset)
            elif token.tag in ("p", "i", "s1", "s2"):
                depth = token.get_article_depth()
                # 💡【改善】int() キャストを完全撤廃し、文字列のままモデルへ引き渡す
                # 相対値（"-1", "0", "1"）でない具体的な番号が来たらその階層にセット
                if token.offset not in ("-1", "0", "1", "each"):
                    loc = loc.update_relative(depth, token.offset)
            elif token.offset == "each":
                # 各号トークン時のプレースホルダー挙動（必要に応じて拡張可能）
                pass
        return loc

    def to_resolved_string(self) -> str:
        """
        2つの座標軸のID（id_attr）をデータ属性として埋め込んだ
        曖昧さ対応のデバッグ用マークアップを生成する。
        """
        original_text = "".join([t.label for t in self.tokens])

        # 双方のロジックが弾き出したIDを取得
        id_cur = self.location_via_cur.id_attr
        id_ref = self.location_via_ref.id_attr

        # 同一のIDを指している場合は通常の表示、異なる場合は「候補が2つある」特殊表示にする
        is_ambiguous = (id_cur != id_ref)
        border_color = "#e74c3c" if is_ambiguous else "#f39c12"
        bg_color = "#fdf2e9" if is_ambiguous else "#fffdf0"

        debug_info = f"cur:[{id_cur}] | ref:[{id_ref}]" if is_ambiguous else f"[{id_cur}]"

        return (
            f'<span class="resolved-link-debug" '
            f'data-id-cur="{id_cur}" '
            f'data-id-ref="{id_ref}" '
            f'style="border: 1px solid {border_color}; padding: 0 4px; border-radius: 4px; background: {bg_color}; cursor: help;" '
            f'title="{debug_info}">'
            f'{original_text}'
            f'<span style="color: #e67e22; font-family: monospace; font-weight: bold; margin-left: 8px;">'
            f'[{debug_info}]'
            f'</span>'
            f'</span>'
        )