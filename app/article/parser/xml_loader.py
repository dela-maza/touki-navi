# app/article/parser/xml_loader.py
from bs4 import BeautifulSoup


def load_xml_soup(xml_path: str) -> BeautifulSoup:
    with open(xml_path, "r", encoding="utf-8") as f:
        return BeautifulSoup(f, "xml")
