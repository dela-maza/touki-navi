import os
from flask import Flask
from app.article.views import article_bp


def create_app():
    # 1. 実行ファイル(app.py)のあるディレクトリを取得
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. templatesフォルダの絶対パスを構築
    # 画像の通り、プロジェクトルート直下の templates フォルダを指すようにします
    template_dir = os.path.join(base_dir, 'templates')

    # 3. Flaskインスタンスの生成
    # template_folder を指定することで、Blueprint内からの呼び出しでもここを見に行くようになります
    app = Flask(__name__, template_folder=template_dir)

    # デバッグ用にパスをターミナルに表示（不要になれば消してOKです）
    print(f">>> Flask Root Path: {base_dir}")
    print(f">>> Template Dir: {template_dir}")

    # 4. Blueprintの登録
    # views.py で定義した article_bp を登録。url_prefixはお好みで調整してください
    app.register_blueprint(article_bp, url_prefix='/article/debug')

    return app


if __name__ == '__main__':
    app = create_app()
    # 5001番ポート、デバッグモードONで起動
    app.run(host='127.0.0.1', port=5001, debug=True)