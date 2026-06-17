# touki-navi/parser/law_parser.py

from bs4 import BeautifulSoup


class LawParser:
    def __init__(self, xml_content):
        self.soup = BeautifulSoup(xml_content, "xml")
        self.law_title = self.soup.find("LawTitle").get_text() if self.soup.find("LawTitle") else ""

        # 各パートのルートを保持
        self.toc_root = self.soup.find("TOC")
        self.article_root = self.soup.find("MainProvision")
        # 附則は複数存在する場合があるためfind_all
        self.suppl_roots = self.soup.find_all("SupplProvision")