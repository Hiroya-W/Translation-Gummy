# coding: utf-8
import os
from . import gateways
from . import journals
from . import translators

from .journals import whichJournal
from .utils import tohtml, html2pdf
from .utils import get_driver
from .utils import GUMMY_DIR, TEMPLATES_DIR

class TranslationGummy():
    def __init__(self, chrome_options=None, gateway="utokyo", translator="deepl"):
        self.driver = get_driver(chrome_options=chrome_options)
        self.gateway = gateways.get(gateway)
        self.translator = translators.get(translator)

    def en2ja(self, query):
        return self.translator.en2ja(query=query, driver=self.driver)

    def get_contents(self, url, journal_type=None, **gatewaykwargs):
        if journal_type is None:
            journal_type = whichJournal(url)
        crawler = journals.get(journal_type, sleep_for_loading=3)
        self.gateway.passthrough(driver=self.driver, **gatewaykwargs)
        title, texts = crawler.get_contents(url=url, driver=self.driver)
        return title, texts

    def toHTML(self, url, path=None, journal_type=None, 
               searchpath=TEMPLATES_DIR, template="paper.tpl", 
               **gatewaykwargs):
        title, texts = self.get_contents(url=url, journal_type=journal_type, **gatewaykwargs)
        contents = []
        for (headline, text) in texts:
            ja = self.en2ja(query=text)
            content = dict(headline=headline, en=text, ja=ja)
            contents.append(content)
        if path is None:
            path = os.path.join(GUMMY_DIR, title + ".html")
        htmlpath = tohtml(path=path, title=title, contents=contents, searchpath=searchpath, template=template)
        return htmlpath

    def toPDF(self, url, path=None, journal_type=None, 
              searchpath=TEMPLATES_DIR, template="paper.tpl",
              delete_html=True, options=None, 
              **gatewaykwargs):
        htmlpath = self.toHTML(
            url=url, path=path, journal_type=journal_type,
            searchpath=searchpath, template=template,
            **gatewaykwargs
        )
        pdfpath = html2pdf(path=htmlpath, delete_html=delete_html, options=options)
        return pdfpath