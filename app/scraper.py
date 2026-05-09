from __future__ import annotations

import re
import shutil
import urllib.request
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from html import unescape
from time import sleep
from urllib.parse import quote_plus, urlparse

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

            body = self._read_article(driver)

            if not body or _is_security_check(body):
                return _rss_fallback(keyword)

            return Article(result_url, body)

        except WebDriverException:
            return _rss_fallback(keyword)

        finally:
            driver.quit()

    # =========================
    # BROWSER SETUP
    # =========================
    def _open_browser(self) -> webdriver.Chrome:
        options = Options()

        for arg in (
            "--headless=new",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1440,1100",
            "--lang=en-US",
        ):
            options.add_argument(arg)

        options.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36"
        )

        binary = _which("google-chrome", "chromium", "chromium-browser")
        if binary:
            options.binary_location = binary

        service = Service(shutil.which("chromedriver") or "")
        return webdriver.Chrome(service=service, options=options)

    # =========================
    # SEARCH LOGIC
    # =========================
    def _search(self, driver: webdriver.Chrome, keyword: str) -> str:
        keyword_lower = keyword.casefold()

        driver.get(POLITICO_SEARCH.format(query=quote_plus(keyword)))
        self._wait_for_body(driver)
        sleep(2)

        links = self._article_links(driver)

        best = self._rank_links(links, keyword_lower)
        if best:
            return best

        driver.get(POLITICO_HOME)
        self._wait_for_body(driver)

        links = self._article_links(driver)
        best = self._rank_links(links, keyword_lower)

        return best or ""

    # =========================
    # LINK EXTRACTION
    # =========================
    def _article_links(self, driver: webdriver.Chrome) -> list[str]:
        links = []

        for el in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
            href = el.get_attribute("href") or ""
            if not href:
                continue

            link = _normalize_politico_url(href)
            if not link:
                continue

            # STRICT FILTER: only real article URLs
            if not _is_article_url(link):
                continue

            links.append(link)

        return list(dict.fromkeys(links))

    # =========================
    # LINK RANKING
    # =========================
    def _rank_links(self, links: list[str], keyword_lower: str) -> str:
        if not links:
            return ""

        scored = []

        for link in links:
            score = 0
            link_lower = link.casefold()

            if keyword_lower in link_lower:
                score += 10

            for word in keyword_lower.split():
                if word in link_lower:
                    score += 3

            scored.append((score, link))

        scored.sort(reverse=True)

        return scored[0][1] if scored else ""

    # =========================
    # ARTICLE SCRAPING
    # =========================
    def _read_article(self, driver: webdriver.Chrome) -> str:
        script = """
        const text = [];

        const add = (t) => {
            if (t && t.trim().length > 0) text.push(t.trim());
        };

        add(document.querySelector('h1')?.innerText);

        document.querySelectorAll('article p').forEach(p => {
            if (p.innerText && p.innerText.length > 40) {
                add(p.innerText);
            }
        });

        return text.join("\\n\\n");
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
# RSS FALLBACK (FIXED)
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

    scored = sorted(
        candidates,
        key=lambda a: keyword_lower in a.body.casefold(),
        reverse=True
    )

    return scored[0]


# =========================
# URL VALIDATION
# =========================
def _normalize_politico_url(url: str) -> str:
    if not url:
        return ""

    parsed = urlparse(url)

    if parsed.netloc not in POLITICO_HOSTS:
        return ""

    return url.split("?")[0]


def _is_article_url(url: str) -> bool:
    return (
        "/news/" in url
        or "/story/" in url
        or "/playbook/" in url
        or "/analysis/" in url
        or re.search(r"/20\d{2}/", url) is not None
    )


# =========================
# HELPERS
# =========================
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
    t = text.lower()
    return "bot" in t or "security" in t
