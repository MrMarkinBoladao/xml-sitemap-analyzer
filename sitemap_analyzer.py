#!/usr/bin/env python3
"""
sitemap_analyzer.py - Discover, collect and organize a site's public content.

Give it a domain and it will:
  1. Detect the platform (WordPress, Shopify, Next.js, Drupal, ...).
  2. Find the sitemap (from robots.txt, or by probing known paths).
  3. Walk nested sitemap indexes and gather every URL.
  4. Fall back to crawling internal links when there is no sitemap.
  5. Visit each page and pull title, description, h1, status and size.
  6. Organize everything and print it as a list (JSON/CSV export available).

Basic usage:
    python3 sitemap_analyzer.py example.com

No external dependencies: standard library only (Python 3.8+).
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple
from xml.etree import ElementTree

__version__ = "1.0"

DEFAULT_UA = "Mozilla/5.0 (compatible; sitemap-analyzer/%s; sitemap reader)" % __version__

# Most common sitemap locations, probed in order when robots.txt declares none.
CANDIDATE_SITEMAPS: Tuple[str, ...] = (
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/wp-sitemap.xml",
    "/sitemap-index.xml",
    "/sitemap/sitemap-index.xml",
    "/sitemap.xml.gz",
    "/sitemap.txt",
    "/sitemap1.xml",
    "/post-sitemap.xml",
    "/page-sitemap.xml",
)

CANDIDATE_FEEDS: Tuple[str, ...] = (
    "/feed/",
    "/rss.xml",
    "/feed.xml",
    "/atom.xml",
    "/index.xml",
    "/blog/feed/",
)

CANDIDATE_APIS: Tuple[str, ...] = (
    "/wp-json/wp/v2/posts",
    "/ghost/api/content/posts/",
    "/products.json",
)

# Byte ceiling per response. Plenty for metadata; stops us from accidentally
# downloading an 80 MB PDF.
MAX_BYTES = 600_000

XML_CONTENT_HINTS = ("xml", "text/plain", "gzip", "octet-stream")


# --------------------------------------------------------------------------
# Localization
# --------------------------------------------------------------------------

STRINGS: Dict[str, Dict[str, str]] = {
    "en": {
        # report sections
        "detection": "DETECTION",
        "sitemaps_read": "SITEMAPS READ ({n})",
        "feeds": "FEEDS",
        "apis": "APIS AVAILABLE",
        "summary": "SUMMARY",
        "problems": "PROBLEMS",
        "warnings": "WARNINGS",
        # detection rows
        "final_url": "Final URL",
        "status": "Status",
        "platform": "Platform",
        "generator": "Generator",
        "server": "Server",
        "language": "Language",
        "robots_txt": "robots.txt",
        "sitemap_via": "Sitemap via",
        "total_urls": "URLs in total",
        "not_identified": "not identified",
        "found": "found",
        "missing": "missing",
        # summary rows
        "urls_found": "URLs found",
        "pages_inspected": "Pages inspected",
        "ok_responses": "OK responses",
        "with_problems": "With problems",
        "groups": "Groups",
        "elapsed": "Time",
        # page entries
        "mod": "mod",
        "skipped": "skipped: {reason}",
        "blocked_robots": "blocked by robots.txt",
        "home_group": "(home)",
        "no_source": "(no source)",
        "and_more": "... and {n} more",
        # discovery methods
        "via_robots": "robots.txt",
        "via_candidates": "probing known paths",
        "via_not_found": "not found",
        "via_argument": "given via --sitemap",
        "via_crawl_none": "link crawl (no sitemap)",
        "via_crawl_failed": "link crawl (declared sitemap failed)",
        # warnings / errors
        "warn_invalid_sitemap": "{url} -> does not look like a valid sitemap",
        "warn_declared_failed": "declared sitemap ({urls}) returned no URLs; falling back to link crawl",
        "warn_no_sitemap": "no sitemap found; falling back to link crawl",
        "err_empty_domain": "empty domain",
        "err_bad_domain": "could not parse domain: {raw}",
        "err_prefix": "error: {message}",
        "interrupted": "interrupted.",
        "json_saved": "JSON saved to {path}",
        "csv_saved": "CSV saved to {path}",
        # argparse
        "help_description": "Detect a site's platform, find its sitemap and list every page with metadata.",
        "help_site": "domain or URL (e.g. example.com)",
        "help_limit": "maximum pages inspected (default: 200; 0 = no limit)",
        "help_max_urls": "stop reading sitemaps after N URLs (0 = no limit)",
        "help_no_meta": "do not visit pages; list only what the sitemap reports",
        "help_quick": "skip feed and API probing",
        "help_sitemap": "use this sitemap instead of detecting one",
        "help_include": "regex: keep only matching URLs",
        "help_exclude": "regex: drop matching URLs",
        "help_group_by": "how to group the list (default: auto)",
        "help_depth": "maximum sitemap index depth (default: 6)",
        "help_crawl_depth": "link crawl depth when there is no sitemap (default: 2)",
        "help_workers": "parallel requests (default: 8)",
        "help_timeout": "per-request timeout in seconds",
        "help_retries": "extra attempts per request",
        "help_delay": "pause in seconds before each request (be polite)",
        "help_ignore_robots": "ignore robots.txt Disallow rules",
        "help_user_agent": "custom User-Agent",
        "help_lang": "output language (default: en)",
        "help_json": "save the full report as JSON",
        "help_csv": "save the page list as CSV",
        "help_no_color": "disable colors",
        "help_epilog": """examples:
  python3 sitemap_analyzer.py example.com
  python3 sitemap_analyzer.py https://blog.example.com --limit 50
  python3 sitemap_analyzer.py example.com --no-meta          # URLs only, fast
  python3 sitemap_analyzer.py example.com --include '/blog/' --csv blog.csv
  python3 sitemap_analyzer.py example.com --sitemap https://example.com/custom.xml
  python3 sitemap_analyzer.py example.com --lang pt          # output in Portuguese
""",
    },
    "pt": {
        "detection": "DETECCAO",
        "sitemaps_read": "SITEMAPS LIDOS ({n})",
        "feeds": "FEEDS",
        "apis": "APIS DISPONIVEIS",
        "summary": "RESUMO",
        "problems": "PROBLEMAS",
        "warnings": "AVISOS",
        "final_url": "URL final",
        "status": "Status",
        "platform": "Plataforma",
        "generator": "Generator",
        "server": "Servidor",
        "language": "Idioma",
        "robots_txt": "robots.txt",
        "sitemap_via": "Sitemap via",
        "total_urls": "URLs no total",
        "not_identified": "nao identificada",
        "found": "encontrado",
        "missing": "ausente",
        "urls_found": "URLs encontradas",
        "pages_inspected": "Paginas inspecionadas",
        "ok_responses": "Respostas OK",
        "with_problems": "Com problema",
        "groups": "Grupos",
        "elapsed": "Tempo",
        "mod": "mod",
        "skipped": "pulado: {reason}",
        "blocked_robots": "bloqueado no robots.txt",
        "home_group": "(home)",
        "no_source": "(sem origem)",
        "and_more": "... e mais {n}",
        "via_robots": "robots.txt",
        "via_candidates": "tentativa de caminhos conhecidos",
        "via_not_found": "nao encontrado",
        "via_argument": "informado via --sitemap",
        "via_crawl_none": "crawl de links (sem sitemap)",
        "via_crawl_failed": "crawl de links (sitemap declarado falhou)",
        "warn_invalid_sitemap": "{url} -> nao parece um sitemap valido",
        "warn_declared_failed": "sitemap declarado ({urls}) nao retornou URLs; usando crawl de links",
        "warn_no_sitemap": "nenhum sitemap encontrado; usando crawl de links",
        "err_empty_domain": "dominio vazio",
        "err_bad_domain": "nao consegui entender o dominio: {raw}",
        "err_prefix": "erro: {message}",
        "interrupted": "interrompido.",
        "json_saved": "JSON salvo em {path}",
        "csv_saved": "CSV salvo em {path}",
        "help_description": "Detecta a plataforma de um site, acha o sitemap e lista todas as paginas com metadados.",
        "help_site": "dominio ou URL (ex: exemplo.com)",
        "help_limit": "maximo de paginas inspecionadas (padrao: 200; 0 = sem limite)",
        "help_max_urls": "para de ler sitemaps depois de N URLs (0 = sem limite)",
        "help_no_meta": "nao visita as paginas; lista apenas o que o sitemap informa",
        "help_quick": "pula a sondagem de feeds e APIs",
        "help_sitemap": "usa este sitemap em vez de detectar",
        "help_include": "regex: so URLs que casarem",
        "help_exclude": "regex: descarta URLs que casarem",
        "help_group_by": "como agrupar a lista (padrao: auto)",
        "help_depth": "profundidade maxima de sitemap index (padrao: 6)",
        "help_crawl_depth": "profundidade do crawl quando nao ha sitemap (padrao: 2)",
        "help_workers": "requisicoes em paralelo (padrao: 8)",
        "help_timeout": "timeout por requisicao em segundos",
        "help_retries": "tentativas extras por requisicao",
        "help_delay": "pausa em segundos antes de cada requisicao (educacao com o servidor)",
        "help_ignore_robots": "ignora as regras Disallow do robots.txt",
        "help_user_agent": "User-Agent customizado",
        "help_lang": "idioma da saida (padrao: en)",
        "help_json": "salva o relatorio completo em JSON",
        "help_csv": "salva a lista de paginas em CSV",
        "help_no_color": "desliga as cores",
        "help_epilog": """exemplos:
  python3 sitemap_analyzer.py exemplo.com
  python3 sitemap_analyzer.py https://blog.exemplo.com --limit 50
  python3 sitemap_analyzer.py exemplo.com --no-meta          # so as URLs, rapido
  python3 sitemap_analyzer.py exemplo.com --include '/blog/' --csv blog.csv
  python3 sitemap_analyzer.py exemplo.com --sitemap https://exemplo.com/custom.xml
  python3 sitemap_analyzer.py exemplo.com --lang pt          # saida em portugues
""",
    },
}

LANGUAGES: Tuple[str, ...] = tuple(STRINGS)


class Translator:
    """Tiny lookup helper. Falls back to English, then to the key itself."""

    def __init__(self, code: str = "en") -> None:
        self.code = code if code in STRINGS else "en"
        self._table = STRINGS[self.code]

    def __call__(self, key: str, **kwargs: object) -> str:
        text = self._table.get(key) or STRINGS["en"].get(key, key)
        return text.format(**kwargs) if kwargs else text


def language_from_argv(argv: Sequence[str]) -> str:
    """Peek at --lang before argparse runs, so help text is localized too."""
    for index, arg in enumerate(argv):
        if arg == "--lang" and index + 1 < len(argv):
            return argv[index + 1]
        if arg.startswith("--lang="):
            return arg.split("=", 1)[1]
    return "en"


# --------------------------------------------------------------------------
# URL helpers
# --------------------------------------------------------------------------


def normalize_site(raw: str, t: Optional[Translator] = None) -> str:
    """Accepts 'example.com', 'example.com/', 'http://example.com/blog' and
    returns the canonical origin: 'https://example.com'."""
    t = t or Translator()
    raw = raw.strip()
    if not raw:
        raise ValueError(t("err_empty_domain"))
    if "://" not in raw:
        raw = "https://" + raw
    parts = urllib.parse.urlsplit(raw)
    if not parts.netloc:
        raise ValueError(t("err_bad_domain", raw=raw))
    scheme = parts.scheme if parts.scheme in ("http", "https") else "https"
    return urllib.parse.urlunsplit((scheme, parts.netloc, "", "", ""))


def join(base: str, path: str) -> str:
    return urllib.parse.urljoin(base if base.endswith("/") else base + "/", path.lstrip("/"))


def registrable(host: str) -> str:
    """'www.example.com' -> 'example.com'. Rough, but good enough to decide
    whether a link is internal."""
    host = host.lower().split(":")[0]
    return host[4:] if host.startswith("www.") else host


def same_site(url: str, base_host: str) -> bool:
    try:
        host = urllib.parse.urlsplit(url).netloc
    except ValueError:
        return False
    return bool(host) and registrable(host) == registrable(base_host)


def clean_link(href: str, page_url: str) -> Optional[str]:
    """Resolve a relative href and drop anything not worth crawling."""
    href = (href or "").strip()
    if not href or href.startswith("#"):
        return None
    low = href.lower()
    for bad in ("javascript:", "mailto:", "tel:", "data:", "sms:", "ftp:"):
        if low.startswith(bad):
            return None
    absolute = urllib.parse.urljoin(page_url, href)
    parts = urllib.parse.urlsplit(absolute)
    if parts.scheme not in ("http", "https"):
        return None
    # Drop the fragment, keep the query (it can select distinct content).
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def path_section(url: str, t: Translator) -> str:
    """First path segment, used for grouping."""
    path = urllib.parse.urlsplit(url).path.strip("/")
    if not path:
        return t("home_group")
    return "/%s" % path.split("/")[0]


def pretty_size(n: Optional[int]) -> str:
    if n is None:
        return "-"
    if n < 1024:
        return "%d B" % n
    if n < 1024 * 1024:
        return "%.1f KB" % (n / 1024)
    return "%.1f MB" % (n / (1024 * 1024))


def short_date(value: Optional[str]) -> str:
    """'2026-09-30T14:46:33+00:00' -> '2026-09-30'."""
    if not value:
        return "-"
    match = re.match(r"(\d{4}-\d{2}-\d{2})", value.strip())
    return match.group(1) if match else value.strip()[:19]


def truncate(text: Optional[str], width: int) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    # ASCII '...' instead of the ellipsis character: survives any Windows code page.
    return text if len(text) <= width else text[: width - 3].rstrip() + "..."


# --------------------------------------------------------------------------
# HTTP layer
# --------------------------------------------------------------------------


@dataclass
class Response:
    url: str
    status: int
    headers: Dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    error: Optional[str] = None
    declared_length: Optional[int] = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    @property
    def content_type(self) -> str:
        return (self.headers.get("content-type") or "").lower()

    def text(self) -> str:
        charset = "utf-8"
        match = re.search(r"charset=([\w\-]+)", self.content_type)
        if match:
            charset = match.group(1)
        body = self.body
        if body[:2] == b"\x1f\x8b":  # gzip even when the header does not say so
            try:
                body = gzip.decompress(body)
            except OSError:
                pass
        try:
            return body.decode(charset, errors="replace")
        except LookupError:
            return body.decode("utf-8", errors="replace")


class HttpClient:
    """Minimal HTTP client: honest User-Agent, timeout, retry and gunzip."""

    def __init__(self, ua: str = DEFAULT_UA, timeout: float = 15.0,
                 retries: int = 1, delay: float = 0.0) -> None:
        self.ua = ua
        self.timeout = timeout
        self.retries = max(0, retries)
        self.delay = max(0.0, delay)
        self._opener = urllib.request.build_opener()

    def fetch(self, url: str, max_bytes: int = MAX_BYTES) -> Response:
        last_error = "unknown error"
        for attempt in range(self.retries + 1):
            if self.delay:
                time.sleep(self.delay)
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": self.ua,
                    "Accept": "*/*",
                    "Accept-Encoding": "gzip, identity",
                },
            )
            try:
                with self._opener.open(request, timeout=self.timeout) as raw:
                    return self._build(raw, url, max_bytes)
            except urllib.error.HTTPError as exc:
                # HTTPError is also a readable response object.
                try:
                    return self._build(exc, url, max_bytes)
                except Exception:
                    return Response(url=url, status=exc.code, error="HTTP %s" % exc.code)
            except urllib.error.URLError as exc:
                last_error = str(getattr(exc, "reason", exc))
            except Exception as exc:  # socket timeouts, broken XML, etc.
                last_error = "%s: %s" % (type(exc).__name__, exc)
            if attempt < self.retries:
                time.sleep(0.4 * (attempt + 1))
        return Response(url=url, status=0, error=last_error)

    def _build(self, raw, requested: str, max_bytes: int) -> Response:
        headers = {k.lower(): v for k, v in raw.headers.items()}
        body = raw.read(max_bytes)
        if headers.get("content-encoding", "").lower() == "gzip" or body[:2] == b"\x1f\x8b":
            try:
                body = gzip.decompress(body)
            except OSError:
                pass  # probably truncated; carry on with what we have
        declared = None
        if headers.get("content-length", "").isdigit():
            declared = int(headers["content-length"])
        return Response(
            url=raw.geturl() or requested,
            status=raw.status if hasattr(raw, "status") else raw.getcode(),
            headers=headers,
            body=body,
            declared_length=declared,
        )


# --------------------------------------------------------------------------
# HTML parsing (metadata + links)
# --------------------------------------------------------------------------


class HtmlScraper(HTMLParser):
    """Pulls title, meta description, h1, canonical, lang, generator and links."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: Optional[str] = None
        self.description: Optional[str] = None
        self.canonical: Optional[str] = None
        self.lang: Optional[str] = None
        self.generator: Optional[str] = None
        self.h1: Optional[str] = None
        self.og: Dict[str, str] = {}
        self.links: List[str] = []
        self.feeds: List[str] = []
        self._capturing: Optional[str] = None
        self._buffer: List[str] = []
        self._svg_depth = 0

    def _start_capture(self, name: str) -> None:
        self._capturing = name
        self._buffer = []

    def _finish_capture(self) -> None:
        text = re.sub(r"\s+", " ", "".join(self._buffer)).strip()
        if self._capturing == "title" and not self.title:
            self.title = text or None
        elif self._capturing == "h1" and not self.h1:
            self.h1 = text or None
        self._capturing = None
        self._buffer = []

    def handle_starttag(self, tag: str, attrs: Sequence[Tuple[str, Optional[str]]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "svg":
            self._svg_depth += 1
            return
        if tag == "html" and not self.lang:
            self.lang = a.get("lang") or None
        elif tag == "title" and not self._svg_depth and not self.title:
            self._start_capture("title")
        elif tag == "h1" and not self.h1:
            self._start_capture("h1")
        elif tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            content = a.get("content", "").strip()
            if not content:
                return
            if key == "description" and not self.description:
                self.description = content
            elif key == "generator" and not self.generator:
                self.generator = content
            elif key.startswith("og:"):
                self.og.setdefault(key, content)
        elif tag == "link":
            rels = (a.get("rel") or "").lower().split()
            href = a.get("href", "")
            if "canonical" in rels and href and not self.canonical:
                self.canonical = href
            if "alternate" in rels and href:
                if any(hint in (a.get("type") or "") for hint in ("rss", "atom", "xml")):
                    self.feeds.append(href)
        elif tag == "a":
            href = a.get("href")
            if href:
                self.links.append(href)

    def handle_startendtag(self, tag: str, attrs: Sequence[Tuple[str, Optional[str]]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag == "svg":
            self._svg_depth = max(0, self._svg_depth - 1)

    def handle_endtag(self, tag: str) -> None:
        if tag == "svg":
            self._svg_depth = max(0, self._svg_depth - 1)
        elif tag == self._capturing:
            self._finish_capture()

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._buffer.append(data)


def scrape_html(html: str) -> HtmlScraper:
    scraper = HtmlScraper()
    try:
        scraper.feed(html)
    except Exception:
        pass  # broken HTML: keep whatever was parsed before the failure
    return scraper


# --------------------------------------------------------------------------
# Sitemaps
# --------------------------------------------------------------------------


@dataclass
class SitemapEntry:
    loc: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[str] = None
    source: str = ""


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1].lower()


def _find_text(node: ElementTree.Element, wanted: str) -> Optional[str]:
    for child in node:
        if strip_ns(child.tag) == wanted:
            return (child.text or "").strip() or None
    return None


def parse_sitemap(body_text: str, source: str) -> Tuple[List[str], List[SitemapEntry]]:
    """Returns (child_sitemaps, url_entries).

    Understands <sitemapindex>, <urlset>, RSS/Atom feeds and plain-text sitemaps.
    """
    # A BOM is not whitespace to str.strip(), so without removing it explicitly
    # an XML sitemap served with a BOM (common on IIS) is read as plain text.
    text = body_text.lstrip("\ufeff\ufffe\x00").strip()
    if not text:
        return [], []

    # Plain-text sitemap: one URL per line.
    if not text.startswith("<"):
        entries = [
            SitemapEntry(loc=line.strip(), source=source)
            for line in text.splitlines()
            if line.strip().startswith(("http://", "https://"))
        ]
        return [], entries

    try:
        root = ElementTree.fromstring(text.encode("utf-8", errors="replace"))
    except ElementTree.ParseError:
        # Some servers prepend junk before the XML. Try to find the real start.
        start = text.find("<")
        if start <= 0:
            return [], []
        try:
            root = ElementTree.fromstring(text[start:].encode("utf-8", errors="replace"))
        except ElementTree.ParseError:
            return [], []

    name = strip_ns(root.tag)
    children: List[str] = []
    entries: List[SitemapEntry] = []

    if name == "sitemapindex":
        for node in root:
            loc = _find_text(node, "loc")
            if loc:
                children.append(loc)
        return children, entries

    if name == "urlset":
        for node in root:
            loc = _find_text(node, "loc")
            if not loc:
                continue
            entries.append(
                SitemapEntry(
                    loc=loc,
                    lastmod=_find_text(node, "lastmod"),
                    changefreq=_find_text(node, "changefreq"),
                    priority=_find_text(node, "priority"),
                    source=source,
                )
            )
        return children, entries

    if name == "rss":
        for item in root.iter():
            if strip_ns(item.tag) != "item":
                continue
            loc = _find_text(item, "link")
            if loc:
                entries.append(
                    SitemapEntry(loc=loc, lastmod=_find_text(item, "pubdate"), source=source)
                )
        return children, entries

    if name == "feed":
        for item in root.iter():
            if strip_ns(item.tag) != "entry":
                continue
            loc = None
            for child in item:
                if strip_ns(child.tag) == "link":
                    loc = child.attrib.get("href") or loc
            if loc:
                entries.append(
                    SitemapEntry(loc=loc.strip(), lastmod=_find_text(item, "updated"), source=source)
                )
        return children, entries

    return children, entries


class SitemapCollector:
    """Walks sitemaps recursively, with loop protection."""

    def __init__(self, client: HttpClient, t: Translator,
                 max_depth: int = 6, max_urls: Optional[int] = None) -> None:
        self.client = client
        self.t = t
        self.max_depth = max_depth
        self.max_urls = max_urls
        self.visited: List[str] = []
        self.errors: List[str] = []

    def collect(self, roots: Sequence[str]) -> List[SitemapEntry]:
        seen_sitemaps: Set[str] = set()
        seen_urls: Set[str] = set()
        entries: List[SitemapEntry] = []
        queue: List[Tuple[str, int]] = [(u, 0) for u in roots]

        while queue:
            url, depth = queue.pop(0)
            if url in seen_sitemaps or depth > self.max_depth:
                continue
            seen_sitemaps.add(url)

            response = self.client.fetch(url)
            if not response.ok:
                self.errors.append(
                    "%s -> %s" % (url, response.error or "HTTP %s" % response.status)
                )
                continue

            children, found = parse_sitemap(response.text(), url)
            if not children and not found:
                self.errors.append(self.t("warn_invalid_sitemap", url=url))
                continue

            self.visited.append(url)
            for child in children:
                if child not in seen_sitemaps:
                    queue.append((child, depth + 1))
            for entry in found:
                if entry.loc in seen_urls:
                    continue
                seen_urls.add(entry.loc)
                entries.append(entry)
                if self.max_urls and len(entries) >= self.max_urls:
                    return entries
        return entries


def discover_sitemaps(client: HttpClient, base: str,
                      t: Translator) -> Tuple[List[str], List[str], str, bool]:
    """Finds sitemaps. Returns (sitemaps, robots_declared, method, robots_exists)."""
    response = client.fetch(join(base, "robots.txt"))
    declared: List[str] = []
    robots_exists = response.ok and "html" not in response.content_type

    if robots_exists:
        for line in response.text().splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            if key.strip().lower() == "sitemap" and value.strip():
                candidate = value.strip()
                if candidate not in declared:
                    declared.append(candidate)

    if declared:
        return declared, declared, t("via_robots"), robots_exists

    # robots.txt declared nothing: probe the classic paths.
    found: List[str] = []
    for path in CANDIDATE_SITEMAPS:
        url = join(base, path)
        probe = client.fetch(url, max_bytes=8192)
        if not probe.ok:
            continue
        head = probe.text()[:400].lstrip("\ufeff").lstrip()
        looks_xml = head.startswith("<?xml") or "<urlset" in head or "<sitemapindex" in head
        looks_txt = path.endswith(".txt") and head.startswith(("http://", "https://"))
        if looks_xml or looks_txt:
            found.append(url)
            break

    method = t("via_candidates") if found else t("via_not_found")
    return found, declared, method, robots_exists


# --------------------------------------------------------------------------
# Platform detection
# --------------------------------------------------------------------------


PLATFORM_RULES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("WordPress", ("/wp-content/", "/wp-includes/", "wp-json", "wp-sitemap", "wordpress")),
    ("Yoast SEO", ("yoast", "sitemap_index.xml")),
    ("Shopify", ("cdn.shopify.com", "shopify", "myshopify.com")),
    ("Wix", ("wix.com", "wixstatic", "_partials/wix")),
    ("Squarespace", ("squarespace.com", "static1.squarespace")),
    ("Webflow", ("webflow.io", "assets.website-files.com", "webflow.js")),
    ("Drupal", ("/sites/default/files", "drupal.js", "drupal-settings-json")),
    ("Joomla", ("/media/jui/", "joomla", "com_content")),
    ("Plone/Zope", ("plone", "zserver", "zope")),
    ("Magento", ("/static/version", "mage/cookies", "magento")),
    ("PrestaShop", ("prestashop",)),
    ("Laravel", ("laravel_session", "xsrf-token")),
    ("Django", ("csrftoken", "django")),
    ("Ruby on Rails", ("csrf-param", "x-runtime", "rails")),
    ("Ghost", ("ghost-sdk", "/ghost/api/", "content-api")),
    ("Next.js", ("/_next/static", "__next_f", "__next_data__")),
    ("Nuxt", ("/_nuxt/", "__nuxt__")),
    ("Gatsby", ("/page-data/", "gatsby-", "___gatsby")),
    ("Astro", ("astro-island", "/_astro/")),
    ("Hugo", ("generator\" content=\"hugo",)),
    ("Jekyll", ("jekyll",)),
    ("Svelte/SvelteKit", ("__sveltekit", "/_app/immutable")),
    ("React", ("react", "reactroot")),
    ("Cloudflare", ("cloudflare", "cf-ray")),
    ("Vercel", ("x-vercel-id", "vercel")),
    ("Netlify", ("x-nf-request-id", "netlify")),
)

# Frameworks that already imply React; listing both is noise.
REACT_IMPLIED = ("Next.js", "Nuxt", "Gatsby", "Astro", "Svelte/SvelteKit")


def detect_platform(html: str, headers: Dict[str, str], robots: str,
                    sitemaps: Sequence[str], generator: Optional[str]) -> List[str]:
    """Fingerprint via HTML, headers, robots.txt and sitemap naming."""
    haystack = " ".join(
        [
            html[:200_000].lower(),
            " ".join("%s: %s" % (k, v) for k, v in headers.items()).lower(),
            robots.lower(),
            " ".join(sitemaps).lower(),
            (generator or "").lower(),
        ]
    )
    hits: List[str] = []
    for name, needles in PLATFORM_RULES:
        if any(needle.lower() in haystack for needle in needles):
            hits.append(name)
    if "React" in hits and any(name in hits for name in REACT_IMPLIED):
        hits.remove("React")
    return hits


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------


@dataclass
class Page:
    url: str
    lastmod: Optional[str] = None
    source: str = ""
    status: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    h1: Optional[str] = None
    lang: Optional[str] = None
    canonical: Optional[str] = None
    content_type: Optional[str] = None
    size: Optional[int] = None
    error: Optional[str] = None
    skipped: Optional[str] = None

    def label(self, t: Translator) -> str:
        if self.title:
            return self.title
        if self.h1:
            return self.h1
        # No metadata (e.g. --no-meta): derive a readable name from the path.
        path = urllib.parse.urlsplit(self.url).path.strip("/")
        if not path:
            return t("home_group")
        segments = [s for s in path.split("/") if s]
        slug = re.sub(r"\.\w{2,5}$", "", segments[-1])
        return slug.replace("-", " ").replace("_", " ") or path


def inspect_page(client: HttpClient, page: Page) -> Page:
    response = client.fetch(page.url)
    page.status = response.status or None
    page.content_type = (response.content_type.split(";")[0] or None) if response.headers else None
    page.size = (
        response.declared_length
        if response.declared_length is not None
        else (len(response.body) or None)
    )
    if response.error:
        page.error = response.error
        return page
    if not response.ok:
        page.error = "HTTP %s" % response.status
        return page
    if "html" not in (page.content_type or ""):
        return page  # PDF, image, etc.: status and size are enough
    meta = scrape_html(response.text())
    page.title = meta.title or meta.og.get("og:title")
    page.description = meta.description or meta.og.get("og:description")
    page.h1 = meta.h1
    page.lang = meta.lang
    page.canonical = meta.canonical
    return page


def inspect_all(client: HttpClient, pages: List[Page], workers: int) -> List[Page]:
    todo = [p for p in pages if not p.skipped]
    if not todo:
        return pages
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(lambda p: inspect_page(client, p), todo))
    return pages


# --------------------------------------------------------------------------
# Link crawl (fallback when there is no sitemap)
# --------------------------------------------------------------------------


def crawl_links(client: HttpClient, base: str, method_label: str,
                max_pages: int, max_depth: int = 2) -> List[SitemapEntry]:
    host = urllib.parse.urlsplit(base).netloc
    seen: Set[str] = set()
    ordered: List[str] = []
    queue: List[Tuple[str, int]] = [(base + "/", 0)]

    while queue and len(ordered) < max_pages:
        url, depth = queue.pop(0)
        key = url.rstrip("/") or url
        if key in seen:
            continue
        seen.add(key)

        response = client.fetch(url)
        if not response.ok or "html" not in response.content_type:
            continue

        # Also mark the final URL: redirects (/ -> /home, http -> https,
        # non-www -> www) would otherwise add the same page twice.
        final_key = response.url.rstrip("/") or response.url
        if final_key in seen and final_key != key:
            continue
        seen.add(final_key)
        ordered.append(response.url)

        if depth >= max_depth:
            continue
        meta = scrape_html(response.text())
        for href in meta.links:
            link = clean_link(href, response.url)
            if not link or not same_site(link, host):
                continue
            if (link.rstrip("/") or link) not in seen:
                queue.append((link, depth + 1))

    return [SitemapEntry(loc=u, source=method_label) for u in ordered[:max_pages]]


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


class Palette:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        return "\033[%sm%s\033[0m" % (code, text) if self.enabled else text

    def bold(self, t: str) -> str:
        return self._wrap("1", t)

    def dim(self, t: str) -> str:
        return self._wrap("2", t)

    def cyan(self, t: str) -> str:
        return self._wrap("36", t)

    def green(self, t: str) -> str:
        return self._wrap("32", t)

    def yellow(self, t: str) -> str:
        return self._wrap("33", t)

    def red(self, t: str) -> str:
        return self._wrap("31", t)


@dataclass
class Report:
    target: str
    base: str
    final_url: str
    home_status: Optional[int]
    server: Optional[str]
    platform: List[str]
    generator: Optional[str]
    title: Optional[str]
    description: Optional[str]
    language: Optional[str]
    robots_txt: bool
    sitemap_method: str
    declared_sitemaps: List[str]
    sitemaps_read: List[str]
    feeds: List[str]
    apis: List[str]
    total_urls: int
    pages: List[Page]
    warnings: List[str]
    seconds: float


def group_pages(pages: List[Page], mode: str, t: Translator) -> Dict[str, List[Page]]:
    sources = {p.source for p in pages if p.source}
    if mode == "auto":
        mode = "sitemap" if len(sources) > 1 else "section"
    groups: Dict[str, List[Page]] = {}
    for page in pages:
        if mode == "sitemap":
            key = page.source.rsplit("/", 1)[-1] or page.source or t("no_source")
        else:
            key = path_section(page.url, t)
        groups.setdefault(key, []).append(page)
    for bucket in groups.values():
        bucket.sort(key=lambda p: p.url)
    return dict(sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0])))


def render(report: Report, group_mode: str, palette: Palette,
           t: Translator, width: int = 92) -> str:
    c = palette
    out: List[str] = []
    host = urllib.parse.urlsplit(report.base).netloc

    out.append(c.cyan("=" * width))
    out.append(c.cyan(c.bold("  %s" % host)))
    if report.title and report.title.strip().lower() != host.lower():
        out.append(c.cyan("  %s" % truncate(report.title, width - 4)))
    out.append(c.cyan("=" * width))
    out.append("")

    out.append(c.bold(t("detection")))
    rows: List[Tuple[str, str]] = [
        (t("final_url"), report.final_url),
        (t("status"), str(report.home_status or "-")),
        (t("platform"), ", ".join(report.platform) or t("not_identified")),
    ]
    if report.generator:
        rows.append((t("generator"), report.generator))
    if report.server:
        rows.append((t("server"), report.server))
    if report.language:
        rows.append((t("language"), report.language))
    rows.append((t("robots_txt"), t("found") if report.robots_txt else t("missing")))
    rows.append((t("sitemap_via"), report.sitemap_method))
    rows.append((t("total_urls"), str(report.total_urls)))
    for key, value in rows:
        out.append("  %s %s" % (c.dim((key + " ").ljust(18, ".")), value))
    out.append("")

    if report.sitemaps_read:
        out.append(c.bold(t("sitemaps_read", n=len(report.sitemaps_read))))
        for sitemap in report.sitemaps_read:
            out.append("  - %s" % sitemap)
        out.append("")

    if report.feeds:
        out.append(c.bold(t("feeds")))
        for feed in report.feeds:
            out.append("  - %s" % feed)
        out.append("")

    if report.apis:
        out.append(c.bold(t("apis")))
        for api in report.apis:
            out.append("  - %s" % api)
        out.append("")

    groups = group_pages(report.pages, group_mode, t)
    counter = 0
    for name, bucket in groups.items():
        out.append(c.bold("%s  (%d)" % (name, len(bucket))))
        for page in bucket:
            counter += 1
            out.append(
                "  %s %s" % (c.dim("%3d." % counter), c.bold(truncate(page.label(t), width - 10)))
            )
            out.append("       %s" % c.cyan(page.url))

            facts = ["%s: %s" % (t("mod"), short_date(page.lastmod))]
            # Status and size only exist if the page was actually visited.
            if page.skipped:
                facts.append(c.yellow(t("skipped", reason=page.skipped)))
            elif page.error:
                facts.append(c.red(page.error))
            elif page.status:
                if 200 <= page.status < 300:
                    facts.append(c.green(str(page.status)))
                elif 300 <= page.status < 400:
                    facts.append(c.yellow(str(page.status)))
                else:
                    facts.append(c.red(str(page.status)))
            if page.size is not None:
                facts.append(pretty_size(page.size))
            if page.content_type and "html" not in page.content_type:
                facts.append(page.content_type)
            out.append("       %s" % c.dim(" | ".join(facts)))
            if page.description:
                out.append("       %s" % c.dim(truncate(page.description, width - 10)))
        out.append("")

    ok = sum(1 for p in report.pages if p.status and 200 <= p.status < 300)
    broken = [p for p in report.pages if p.error or (p.status and p.status >= 400)]
    out.append(c.bold(t("summary")))
    summary: List[Tuple[str, str]] = [
        (t("urls_found"), str(report.total_urls)),
        (t("pages_inspected"), str(len(report.pages))),
        (t("ok_responses"), str(ok)),
        (t("with_problems"), str(len(broken))),
        (t("groups"), str(len(groups))),
        (t("elapsed"), "%.1fs" % report.seconds),
    ]
    for key, value in summary:
        out.append("  %s %s" % (c.dim((key + " ").ljust(25, ".")), value))

    if broken:
        out.append("")
        out.append(c.bold(t("problems")))
        for page in broken[:25]:
            out.append("  %s %s" % (c.red((page.error or str(page.status)).ljust(12)), page.url))
        if len(broken) > 25:
            out.append(c.dim("  " + t("and_more", n=len(broken) - 25)))

    if report.warnings:
        out.append("")
        out.append(c.bold(t("warnings")))
        for warning in report.warnings[:15]:
            out.append("  %s %s" % (c.yellow("!"), warning))

    return "\n".join(out)


# --------------------------------------------------------------------------
# Exports
# --------------------------------------------------------------------------


def export_json(report: Report, path: str) -> None:
    payload = asdict(report)
    payload["pages"] = [asdict(p) for p in report.pages]
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def export_csv(report: Report, path: str) -> None:
    columns = [
        "url", "title", "description", "h1", "lastmod", "status",
        "content_type", "size", "lang", "canonical", "source", "error",
    ]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for page in report.pages:
            writer.writerow(asdict(page))


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def analyze(args: argparse.Namespace, t: Translator) -> Report:
    started = time.time()
    base = normalize_site(args.site, t)
    client = HttpClient(ua=args.user_agent, timeout=args.timeout,
                        retries=args.retries, delay=args.delay)

    # 1. Homepage: basis for fingerprinting and site-level metadata.
    home = client.fetch(base + "/")

    # If the homepage redirected to another host (example.com -> www.example.com),
    # everything else must use the final host or robots.txt and sitemap 404.
    if home.ok and home.url:
        final = urllib.parse.urlsplit(home.url)
        if final.netloc and final.netloc != urllib.parse.urlsplit(base).netloc:
            base = urllib.parse.urlunsplit((final.scheme or "https", final.netloc, "", "", ""))

    home_html = home.text() if home.ok and "html" in home.content_type else ""
    home_meta = scrape_html(home_html) if home_html else HtmlScraper()

    # 2. robots.txt + sitemap discovery.
    robots_response = client.fetch(join(base, "robots.txt"))
    robots_text = robots_response.text() if robots_response.ok else ""
    sitemaps, declared, method, robots_exists = discover_sitemaps(client, base, t)

    if args.sitemap:
        sitemaps = [args.sitemap]
        method = t("via_argument")

    # 3. URL collection.
    collector = SitemapCollector(client, t, max_depth=args.depth, max_urls=args.max_urls)
    entries = collector.collect(sitemaps) if sitemaps else []
    warnings = list(collector.errors)

    if not entries:
        # Never lie about provenance: if a sitemap was declared but yielded
        # nothing (403, 404, broken XML), say we fell back to crawling.
        if sitemaps:
            warnings.append(t("warn_declared_failed", urls=", ".join(sitemaps[:3])))
            method = t("via_crawl_failed")
        else:
            warnings.append(t("warn_no_sitemap"))
            method = t("via_crawl_none")
        entries = crawl_links(
            client, base, method,
            max_pages=args.limit or 60, max_depth=args.crawl_depth,
        )

    total_urls = len(entries)

    # 4. Filters: robots.txt, include/exclude regex, limit.
    robot_parser: Optional[urllib.robotparser.RobotFileParser] = None
    if robots_text and not args.ignore_robots:
        robot_parser = urllib.robotparser.RobotFileParser()
        robot_parser.parse(robots_text.splitlines())

    include = re.compile(args.include) if args.include else None
    exclude = re.compile(args.exclude) if args.exclude else None

    pages: List[Page] = []
    for entry in entries:
        if include and not include.search(entry.loc):
            continue
        if exclude and exclude.search(entry.loc):
            continue
        page = Page(url=entry.loc, lastmod=entry.lastmod, source=entry.source)
        if robot_parser and not robot_parser.can_fetch(args.user_agent, entry.loc):
            page.skipped = t("blocked_robots")
        pages.append(page)
        if args.limit and len(pages) >= args.limit:
            break

    # 5. Page inspection (parallel).
    if not args.no_meta:
        inspect_all(client, pages, args.workers)

    # 6. Feeds and APIs.
    feeds: List[str] = []
    for href in home_meta.feeds:
        resolved = urllib.parse.urljoin(base + "/", href)
        if resolved not in feeds:
            feeds.append(resolved)
    if not args.quick:
        for path in CANDIDATE_FEEDS:
            url = join(base, path)
            if url in feeds:
                continue
            probe = client.fetch(url, max_bytes=4096)
            head = probe.text()[:300].lower()
            if probe.ok and ("<rss" in head or "<feed" in head or "xml" in probe.content_type):
                feeds.append(url)

    apis: List[str] = []
    if not args.quick:
        for path in CANDIDATE_APIS:
            url = join(base, path)
            probe = client.fetch(url, max_bytes=2048)
            if probe.ok and "json" in probe.content_type:
                apis.append(url)

    platform = detect_platform(
        home_html, home.headers, robots_text,
        list(sitemaps) + collector.visited, home_meta.generator,
    )

    return Report(
        target=args.site,
        base=base,
        final_url=home.url,
        home_status=home.status or None,
        server=home.headers.get("server"),
        platform=platform,
        generator=home_meta.generator,
        title=home_meta.title,
        description=home_meta.description,
        language=home_meta.lang,
        robots_txt=robots_exists,
        sitemap_method=method,
        declared_sitemaps=declared,
        sitemaps_read=collector.visited,
        feeds=feeds,
        apis=apis,
        total_urls=total_urls,
        pages=pages,
        warnings=warnings,
        seconds=time.time() - started,
    )


def build_parser(t: Translator) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sitemap_analyzer.py",
        description=t("help_description"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=t("help_epilog"),
    )
    parser.add_argument("site", help=t("help_site"))
    parser.add_argument("--limit", type=int, default=200, help=t("help_limit"))
    parser.add_argument("--max-urls", type=int, default=0, help=t("help_max_urls"))
    parser.add_argument("--no-meta", action="store_true", help=t("help_no_meta"))
    parser.add_argument("--quick", action="store_true", help=t("help_quick"))
    parser.add_argument("--sitemap", help=t("help_sitemap"))
    parser.add_argument("--include", help=t("help_include"))
    parser.add_argument("--exclude", help=t("help_exclude"))
    parser.add_argument("--group-by", choices=("auto", "sitemap", "section"),
                        default="auto", help=t("help_group_by"))
    parser.add_argument("--depth", type=int, default=6, help=t("help_depth"))
    parser.add_argument("--crawl-depth", type=int, default=2, help=t("help_crawl_depth"))
    parser.add_argument("--workers", type=int, default=8, help=t("help_workers"))
    parser.add_argument("--timeout", type=float, default=15.0, help=t("help_timeout"))
    parser.add_argument("--retries", type=int, default=1, help=t("help_retries"))
    parser.add_argument("--delay", type=float, default=0.0, help=t("help_delay"))
    parser.add_argument("--ignore-robots", action="store_true", help=t("help_ignore_robots"))
    parser.add_argument("--user-agent", default=DEFAULT_UA, help=t("help_user_agent"))
    parser.add_argument("--lang", choices=LANGUAGES, default="en", help=t("help_lang"))
    parser.add_argument("--json", dest="json_out", metavar="FILE", help=t("help_json"))
    parser.add_argument("--csv", dest="csv_out", metavar="FILE", help=t("help_csv"))
    parser.add_argument("--no-color", action="store_true", help=t("help_no_color"))
    parser.add_argument("--version", action="version", version="sitemap-analyzer %s" % __version__)
    return parser


def setup_console() -> None:
    """Prepare the terminal, mostly for Windows.

    Two concrete problems this solves:
      1. Colors: the Windows console does not interpret ANSI escapes by
         default, so output would be littered with '\\033[36m'.
      2. Encoding: when redirecting to a file ('... > out.txt'), Python on
         Windows uses cp1252 and mangles accented characters, en dashes and
         ellipses. Forcing UTF-8 avoids the corruption.
    """
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            # -11 = STD_OUTPUT_HANDLE, 7 = ENABLE_VIRTUAL_TERMINAL_PROCESSING
            # combined with the default output modes.
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass  # old console: no colors, not fatal

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass  # Python < 3.7 or a replaced stream


def main(argv: Optional[Sequence[str]] = None) -> int:
    setup_console()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    t = Translator(language_from_argv(raw_argv))

    args = build_parser(t).parse_args(raw_argv)
    if args.limit == 0:
        args.limit = None
    if args.max_urls == 0:
        args.max_urls = None

    try:
        report = analyze(args, t)
    except ValueError as exc:
        print(t("err_prefix", message=exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\n" + t("interrupted"), file=sys.stderr)
        return 130

    use_color = (
        not args.no_color
        and sys.stdout.isatty()
        and not os.environ.get("NO_COLOR")
    )
    print(render(report, args.group_by, Palette(use_color), t))

    if args.json_out:
        export_json(report, args.json_out)
        print("\n" + t("json_saved", path=args.json_out))
    if args.csv_out:
        export_csv(report, args.csv_out)
        print(t("csv_saved", path=args.csv_out))

    if report.home_status in (None, 0):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
