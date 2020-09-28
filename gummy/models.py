# coding: utf-8
"""This file defines a model that integrates all of :mod:`journals <gummy.journals>`, 
:mod:`translators <gummy.translators>`, :mod:`gateways <gummy.gateways>`, and 
it is possible to do all of the following at once.

1. Determine the ``journal_type`` of paper from the ``url`` or file extension.
2. If necessary, use a ``GummyGateway`` to access non-open content of the journal.
3. Parse the paper using ``GummyJournals`` and obtain the contents.
4. Translate the English obtained using ``GummyTranslators`` to Japanese.
5. Arrange Japanese and English according to the `templates <https://github.com/iwasakishuto/Translation-Gummy/tree/master/gummy/templates>`_ .
6. Convert the obtained HTML to PDF.

You can get (import) ``TranslationGummy`` by the following 2 ways.

.. code-block:: python

    >>> from gummy.models import TranslationGummy
    >>> from gummy import TranslationGummy
"""

import os
import time

from . import gateways
from . import journals
from . import translators

from .utils._path import GUMMY_DIR, TEMPLATES_DIR
from .utils.coloring_utils import toACCENT, toBLUE, toGREEN
from .utils.driver_utils import get_driver
from .utils.journal_utils import whichJournal
from .utils.outfmt_utils import tohtml, html2pdf
from .utils.driver_utils import get_driver

class TranslationGummy():
    """This class integrates all of the followings
    
    - :mod:`journals <gummy.journals>`
    - :mod:`translators <gummy.translators>`
    - :mod:`gateways <gummy.gateways>`

    Args:
        chrome_options (ChromeOptions)    : Instance of ChromeOptions. (default= :meth:`get_chrome_options() <gummy.utils.driver_utils.get_chrome_options>` ) 
        browser (bool)                    : Whether you want to run Chrome with GUI browser. (default= ``False`` ) 
        driver (WebDriver)                : Selenium WebDriver.
        gateway (str, GummyGateWay)       : identifier of the Gummy Gateway Class. See :mod:`gateways <gummy.gateways>`. (default= `"useless"`)
        translator (str, GummyTranslator) : identifier of the Gummy Translator Class. See :mod:`translators <gummy.translators>`. (default= `"deepl"`)
        maxsize (int)                     : Number of English characters that we can send a request at one time. (default= ``5000``)
        verbose (bool)                    : Whether you want to print output or not. (default= ``True`` ) 
        translator_verbose (bool)         : Whether you want to print translator’s output or not. (default= ``False`` ) 
    """
    def __init__(self, chrome_options=None, browser=False, driver=None, 
                 gateway="useless", translator="deepl", maxsize=5000, 
                 verbose=True, translator_verbose=False):
        if driver is None: driver = get_driver(chrome_options=chrome_options, browser=browser)
        self.driver = driver
        self.gateway = gateway
        self.translator = translators.get(translator, maxsize=maxsize, verbose=translator_verbose)
        self.verbose = verbose

    def en2ja(self, query, barname=None):
        """Translate English into Japanese. See :meth:`en2ja <gummy.translators.en2ja>`.

        Args:
            query (str)        : English to be translated.
            barname (str)      : Bar name for :meth:`ProgressMonitor <gummy.utils.monitor_utils.ProgressMonitor>`.

        Examples:
            >>> from gummy import TranslationGummy
            >>> model = TranslationGummy()
            >>> ja = model.en2ja("This is a pen.")
            DeepLTranslator (query1) 03/30 [##------------------] 10.00% - 3.243[s]
            >>> ja
            'これはペンです。'
        """
        return self.translator.en2ja(query=query, driver=self.driver, barname=barname)

    def get_contents(self, url, journal_type=None, crawl_type=None, gateway=None, **gatewaykwargs):
        """Get contents of the journal.

        Args:
            url (str)                   : URL of a paper or ``path/to/local.pdf``.
            journal_type (str)          : Journal type, if you not specify, judge by analyzing from ``url``.
            crawl_type (str)            : Crawling type, if you not specify, use recommended crawling type.
            gateway (str, GummyGateWay) : identifier of the Gummy Gateway Class. See :mod:`gateways <gummy.gateways>`. (default= ``None``)
            gatewaykwargs (dict)        : Gateway keywargs. See :meth:`passthrough <gummy.gateways.GummyAbstGateWay.passthrough>`.

        Returns:
            tuple (str, dict) : (title, content)

        Examples:
            >>> from gummy import TranslationGummy
            >>> model = TranslationGummy()
            >>> title, texts = model.get_contents("https://www.nature.com/articles/ncb0800_500")
            Estimated Journal Type : Nature
            Crawling Type: soup
                :
            >>> print(title)
            Formation of the male-specific muscle in female by ectopic expression
            >>> print(texts[:1])
            [{'head': 'Abstract', 'en': 'The  () gene product Fru has been ... for the sexually dimorphic actions of the gene.'}]
        """
        if journal_type is None:
            if os.path.exists(url):
                journal_type = "pdf"
            else:
                journal_type = whichJournal(url, driver=self.driver, verbose=self.verbose)
        gateway = gateway or self.gateway
        crawler = journals.get(journal_type, gateway=gateway, sleep_for_loading=3, verbose=self.verbose)
        title, texts = crawler.get_contents(url=url, driver=self.driver, crawl_type=crawl_type, **gatewaykwargs)
        return title, texts

    def toHTML(self, url, path=None, out_dir=GUMMY_DIR,
               journal_type=None, crawl_type=None, gateway=None,
               searchpath=TEMPLATES_DIR, template="paper.html", 
               **gatewaykwargs):
        """Get contents from URL and create a HTML.

        Args:
            url (str)                   : URL of a paper or ``path/to/local.pdf``.
            path/out_dir (str)          : Where you save a created HTML. If path is None, save at ``<out_dir>/<title>.html`` (default= `GUMMY_DIR`)
            journal_type (str)          : Journal type, if you specify, use ``journal_type`` journal crawler. (default= `None`)
            crawl_type (str)            : Crawling type, if you not specify, use recommended crawling type. (default= `None`)
            gateway (str, GummyGateWay) : identifier of the Gummy Gateway Class. See :mod:`gateways <gummy.gateways>`. (default= `None`)
            searchpath/template (str)   : Use a ``<searchpath>/<template>`` tpl for creating HTML. (default= `TEMPLATES_DIR/paper.html`)
            gatewaykwargs (dict)        : Gateway keywargs. See :meth:`passthrough <gummy.gateways.GummyAbstGateWay.passthrough>`.
        """
        title, contents = self.get_contents(
            url=url, journal_type=journal_type, crawl_type=crawl_type, 
            gateway=gateway, **gatewaykwargs
        )
        print(f"\nTranslation: {toACCENT(self.translator.name)}\n{'='*30}")
        len_contents = len(contents)
        for i,content in enumerate(contents):
            barname = f"[{i+1:>0{len(str(len_contents))}}/{len_contents}] " + toACCENT(content.get("head","\t"))            
            if "en" in content:
                # ===== TRANSLATION ======
                ja = self.en2ja(query=content["en"], barname=barname)
                content["ja"] = ja
                # ========================
            elif "img" in content and self.verbose:
                print(barname + "<img>")
        if path is None:
            path = os.path.join(out_dir, title)
        htmlpath = tohtml(
            path=path, title=title, contents=contents, 
            searchpath=searchpath, template=template, verbose=self.verbose
        )
        return htmlpath

    def toPDF(self, url, path=None, out_dir=GUMMY_DIR,
              journal_type=None, crawl_type=None, gateway=None, 
              searchpath=TEMPLATES_DIR, template="paper.html",
              delete_html=True, options={}, 
              **gatewaykwargs):
        """Get contents from URL and create a PDF.

        Args:
            url (str)                   : URL of a paper or ``path/to/local.pdf``.
            path/out_dir (str)          : Where you save a created HTML. If path is None, save at ``<out_dir>/<title>.html`` (default= `GUMMY_DIR`)
            journal_type (str)          : Journal type, if you specify, use ``journal_type`` journal crawler. (default= `None`)
            crawl_type (str)            : Crawling type, if you not specify, use recommended crawling type. (default= `None`)
            gateway (str, GummyGateWay) : identifier of the Gummy Gateway Class. See :mod:`gateways <gummy.gateways>`. (default= `None`)
            searchpath/template (str)   : Use a ``<searchpath>/<template>`` tpl for creating HTML. (default= `TEMPLATES_DIR/paper.html`)
            delete_html (bool)          : Whether you want to delete an intermediate html file. (default= `True`) 
            options (dict)              : Options for wkhtmltopdf. See https://wkhtmltopdf.org/usage/wkhtmltopdf.txt (default= `{}`)
            gatewaykwargs (dict)        : Gateway keywargs. See :meth:`passthrough <gummy.gateways.GummyAbstGateWay.passthrough>`.
        """
        htmlpath = self.toHTML(
            url=url, path=path, out_dir=out_dir,
            journal_type=journal_type, crawl_type=crawl_type, gateway=gateway, 
            searchpath=searchpath, template=template,
            **gatewaykwargs
        )
        if self.verbose: print(f"\nConvert from HTML to PDF\n{'='*30}")
        pdfpath = html2pdf(path=htmlpath, delete_html=delete_html, verbose=self.verbose, options=options)
        return pdfpath