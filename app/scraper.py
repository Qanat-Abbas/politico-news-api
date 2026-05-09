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
            fallback = _rss_fallback(keyword)
            if fallback.url:
                return fallback
            return Article("", f"Selenium failed while reading Politico: {exc.msg}")
        finally:
            driver.quit()

    def _open_browser(self) -> webdriver.Chrome:
        chrome_options = Options()
        for argument in (
            "--headless=new",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1440,1100",
            "--lang=en-US",
            "--disable-blink-features=AutomationControlled",
        ):
            chrome_options.add_argument(argument)

        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )

        binary = _which("google-chrome", "google-chrome-stable", "chromium-browser", "chromium")
        if binary:
            chrome_options.binary_location = binary

        chromedriver_path = shutil.which("chromedriver")
        service = Service(chromedriver_path) if chromedriver_path else Service()
        return webdriver.Chrome(service=service, options=chrome_options)

    def _search(self, driver: webdriver.Chrome, keyword: str) -> str:
        driver.get(POLITICO_SEARCH.format(query=quote_plus(keyword)))
        self._wait_for_body(driver)
        sleep(2)

        links = self._article_links(driver)
        if links:
            return links[0]

        driver.get(POLITICO_HOME)
        self._wait_for_body(driver)
        keyword_lower = keyword.casefold()

        homepage_links = self._article_links(driver, require_text=keyword_lower)
        if homepage_links:
            return homepage_links[0]

        all_homepage_links = self._article_links(driver)
        return all_homepage_links[0] if all_homepage_links else ""

    def _article_links(self, driver: webdriver.Chrome, require_text: str = "") -> list[str]:
        found: list[str] = []
        for element in driver.find_elements(By.CSS_SELECTOR, "a[href]"):
            if require_text and require_text not in (element.text or "").casefold():
                continue

            link = _normalize_politico_url(element.get_attribute("href") or "")
            if link and link not in found:
                found.append(link)

        return found

    def _read_article(self, driver: webdriver.Chrome) -> str:
        script = """
        const blocks = [];
        const seen = new Set();
        const add = (value) => {
          const text = (value || '').replace(/\\s+/g, ' ').trim();
          if (text.length > 0 && !seen.has(text)) {
            seen.add(text);
            blocks.push(text);
          }
        };

        add(document.querySelector('h1')?.innerText || document.title);
        add(document.querySelector('meta[name="description"]')?.content);
        add(document.querySelector('meta[property="og:description"]')?.content);

        const selectors = [
          'article p',
          'main p',
          '[data-testid*="article"] p',
          '[class*="story"] p',
          '[class*="article"] p'
        ];

        for (const selector of selectors) {
          for (const paragraph of document.querySelectorAll(selector)) {
            const text = paragraph.innerText || '';
            if (text.replace(/\\s+/g, ' ').trim().length >= 45) {
              add(text);
            }
          }
        }

        if (blocks.length < 3) {
          add(document.body?.innerText || '');
        }

        return blocks.join('\\n\\n');
        """
        return _clean(driver.execute_script(script) or "")

    def _wait_for_body(self, driver: webdriver.Chrome) -> None:
        try:
            WebDriverWait(driver, 20).until(
                expected.presence_of_element_located((By.CSS_SELECTOR, "body"))
            )
        except TimeoutException:
            pass


def _normalize_politico_url(raw_url: str) -> str:
    if not raw_url:
        return ""

    url_without_fragment, _fragment = urldefrag(raw_url)
    parsed = urlparse(url_without_fragment)
    if parsed.scheme not in {"http", "https"} or parsed.netloc not in POLITICO_HOSTS:
        return ""

    path = parsed.path.rstrip("/")
    if _looks_like_article(path):
        return f"https://www.politico.com{path}"

    return ""


def _looks_like_article(path: str) -> bool:
    blocked = (
        "/search",
        "/about",
        "/advertising",
        "/contact",
        "/events",
        "/privacy",
        "/staff",
        "/video",
    )
    if any(path.startswith(prefix) for prefix in blocked):
        return False

    has_story_area = bool(ARTICLE_SEGMENTS.search(path))
    has_year = bool(re.search(r"/20\d{2}/", path))
    return has_story_area and has_year


def _which(*commands: str) -> str:
    for command in commands:
        resolved = shutil.which(command)
        if resolved:
            return resolved
    return ""


def _clean(value: object) -> str:
    text = unescape(str(value))
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_security_check(text: str) -> bool:
    lowered = text.casefold()
    signals = (
        "performing security verification",
        "protect against malicious bots",
        "verifies you are not a bot",
        "cloudflare",
    )
    return any(signal in lowered for signal in signals)


def _rss_fallback(keyword: str) -> Article:
    try:
        request = urllib.request.Request(
            POLITICO_RSS,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
            },
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            xml_text = response.read().decode("utf-8", errors="replace")
    except Exception:
        return Article("", "")

    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return Article("", "")

    candidates = [_article_from_rss_item(item) for item in root.findall("./channel/item")]
    candidates = [article for article in candidates if article.url]
    if not candidates:
        return Article("", "")

    keyword_lower = keyword.casefold()
    for article in candidates:
        if keyword_lower in article.body.casefold():
            return article

    return candidates[0]


def _article_from_rss_item(item: ElementTree.Element) -> Article:
    title = item.findtext("title", default="")
    link = item.findtext("link", default="")
    description = item.findtext("description", default="")
    content = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", default="")
    body = _clean("\n\n".join(part for part in (title, description, content) if part))
    return Article(link.strip(), body)
