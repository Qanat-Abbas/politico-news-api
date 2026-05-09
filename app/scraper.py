from __future__ import annotations

import re
import shutil
import urllib.request
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from html import unescape
from time import sleep
from urllib.parse import quote_plus, urldefrag, urlparse

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as expected
from selenium.webdriver.support.ui import WebDriverWait

POLITICO_HOSTS = {"www.politico.com", "politico.com"}
POLITICO_HOME = "https://www.politico.com/"
POLITICO_SEARCH = "https://www.politico.com/search?q={query}"
POLITICO_RSS = "https://rss.politico.com/politics-news.xml"
ARTICLE_SEGMENTS = re.compile(
    r"^/(news|story|magazine|live-updates|newsletter|playbook|analysis)/",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Article:
    url: str
    body: str


class PoliticoBrowser:
    def first_result_for(self, keyword: str) -> Article:
        driver = self._open_browser()
        try:
            result_url = self._search(driver, keyword)

            if not result_url:
                return _rss_fallback(keyword)

            driver.get(result_url)
            self._wait_for_body(driver)
            sleep(1)

            article = Article(result_url, self._read_article(driver))

            if _is_security_check(article.body):
                return _rss_fallback(keyword)

            return article

        except WebDriverException as exc:
            return _rss_fallback(keyword)

        finally:
            driver.quit()

    def _open_browser(self) -> webdriver.Chrome:
        chrome_options = Options()

        for arg in (
            "--headless=new",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1440,1100",
            "--lang=en-US",
        ):
            chrome_options.add_argument(arg)

        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36"
        )

        binary = _which("google-chrome", "chromium", "chromium-browser")
        if binary:
            chrome_options.binary_location = binary

        service = Service(shutil.which("chromedriver") or "")
        return webdriver.Chrome(service=service, options=chrome_options)

    def _search(self, driver: webdriver.Chrome, keyword: str) -> str:
        keyword_lower = keyword.casefold()

        driver.get(POLITICO_SEARCH.format(query=quote_plus(keyword)))
        self._wait_for_body(driver)
        sleep(2)

        links = self._article_links(driver)

        # ✅ FIX: rank instead of returning first
        best = self._rank_links(links, keyword_lower)
        if best:
            return best

        driver.get(POLITICO_HOME)
        self._wait_for_body(driver)

        links = self._article_links(driver)
        best = self._rank_links(links, keyword_lower)
        if best:
            return best

        return ""

    def _rank_links(self, links: list[str], keyword_lower: str) -> str:
        if not links:
            return ""

        # prioritize keyword match in URL
        for link in links:
            if keyword_lower in link.casefold():
                return link

        return links[0]

    def _article_links(self, driver: webdriver.Chrome) -> list[str]:
        found = []

        for el in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
            href = el.get_attribute("href") or ""
            text = (el.text or "").casefold()

            if not href:
                continue

            link = _normalize_politico_url(href)
            if not link:
                continue

            found.append(link)

        return list(dict.fromkeys(found))  # remove duplicates

    def _read_article(self, driver: webdriver.Chrome) -> str:
        script = """
        const blocks = [];
        const add = (t) => {
          if (t && t.trim().length > 0) blocks.push(t.trim());
        };

        add(document.querySelector('h1')?.innerText);
        add(document.querySelector('meta[name="description"]')?.content);

        document.querySelectorAll('article p').forEach(p => {
            if (p.innerText && p.innerText.length > 40) {
                add(p.innerText);
            }
        });

        return blocks.join("\\n\\n");
        """
        return _clean(driver.execute_script(script) or "")

    def _wait_for_body(self, driver: webdriver.Chrome) -> None:
        try:
            WebDriverWait(driver, 10).until(
                expected.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
        except TimeoutException:
            pass


# =========================
# HELPERS (FIXED)
# =========================

def _rss_fallback(keyword: str) -> Article:
    try:
        req = urllib.request.Request(POLITICO_RSS)
        with urllib.request.urlopen(req, timeout=10) as res:
            xml_text = res.read().decode("utf-8", errors="ignore")
    except Exception:
        return Article("", "")

    try:
        root = ElementTree.fromstring(xml_text)
    except Exception:
        return Article("", "")

    items = root.findall("./channel/item")

    candidates = []
    for item in items:
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        desc = item.findtext("description", "")

        body = _clean(title + " " + desc)

        candidates.append(Article(link, body))

    if not candidates:
        return Article("", "")

    keyword_lower = keyword.casefold()

    # ✅ FIX: rank RSS results
    scored = sorted(
        candidates,
        key=lambda a: keyword_lower in a.body.casefold(),
        reverse=True
    )

    return scored[0]


def _normalize_politico_url(url: str) -> str:
    if not url:
        return ""

    parsed = urlparse(url)
    if parsed.netloc not in POLITICO_HOSTS:
        return ""

    return url.split("?")[0]


def _clean(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _which(*cmds):
    for c in cmds:
        path = shutil.which(c)
        if path:
            return path
    return ""


def _is_security_check(text: str) -> bool:
    return "bot" in text.lower() or "security" in text.lower()
