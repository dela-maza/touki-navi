import os
from flask import Blueprint, render_template, abort, jsonify

# 自作クラス群のインポート
from app.article.constants.enums import LawType
from app.article.models.index import ArticleIndex
from app.article.parser.article_xml import ArticleXml
from app.article.parser.xml_loader import load_xml_soup
# --- テンプレートパスの物理解決 ---
current_dir = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.abspath(os.path.join(current_dir, "../templates"))

article_bp = Blueprint(
    'article',
    __name__,
    template_folder=template_path
)


@article_bp.route('/shoutouki')
def debug_shoutouki_all():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    xml_path = os.path.join(base_dir, 'data', 'xml', 'shoutouki.xml')

    if not os.path.exists(xml_path):
        abort(404)

    soup = load_xml_soup(xml_path)
    main_provision = soup.find("MainProvision")
    if not main_provision:
        abort(404)

    # XML解析は ArticleXml インスタンスに一任
    article_xml = ArticleXml(LawType.SHOU_TOU_KI)
    all_articles = article_xml.parse_articles(main_provision)

    return render_template(
        'debug_viewer.html',
        law_name="商業登記規則",
        articles=all_articles
    )


@article_bp.route('/db/init/<law>')
def init_law_articles(law: str):
    """
    db.init の入口候補。

    law short_name から XML を読み込み、list[Article] と ArticleIndex を生成する。
    DB保存と reference 解決は後続工程で実装する。
    """
    try:
        law_type = LawType.from_short_name(law)
    except ValueError:
        abort(404)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    xml_path = os.path.join(base_dir, 'data', 'xml', f'{law_type.short_name}.xml')

    if not os.path.exists(xml_path):
        abort(404)

    soup = load_xml_soup(xml_path)
    main_provision = soup.find("MainProvision")
    if not main_provision:
        abort(404)

    article_xml = ArticleXml(law_type)
    articles = article_xml.parse_articles(main_provision)
    article_index = ArticleIndex.from_articles(
        articles,
        element_locations_by_article=article_xml.element_locations_by_article,
    )

    return jsonify({
        "law": law_type.short_name,
        "law_name": law_type.name_jp,
        "xml_file": os.path.basename(xml_path),
        "article_count": len(articles),
        "article_index_count": len(article_index.id_list),
        "first_article_nums": article_index.id_list[:5],
        "last_article_nums": article_index.id_list[-5:],
    })
