class ReferenceMarker:
    """条文の参照解決（Reference Resolution）の文脈において、
    上流（chunker）から下流（shift）までのパース・計算を同期させるための識別子（マーク）の定義。
    """
    # 法律参照の識別子
    SAME_LAW = "same_law"
    LAW_SUFFIX = "law"

    # 範囲指定（前○条など）の識別子
    RANGE_SUFFIX = "_range"

    # 各号などのループ識別子
    EACH = "each"