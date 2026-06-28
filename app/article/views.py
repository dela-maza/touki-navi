import os
from flask import Blueprint, render_template, abort

# 自作クラス群のインポート
from app.article.constants.enums import LawType
from app.article.parser.article_xml import ArticleXMLParser
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

    # XML解析と参照解決をパーサーに一任
    all_articles = ArticleXMLParser.parse_articles(main_provision, LawType.SHOU_TOU_KI)

    return render_template(
        'debug_viewer.html',
        law_name="商業登記規則",
        articles=all_articles
    )
