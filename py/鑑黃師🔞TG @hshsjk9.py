# -*- coding: utf-8 -*-
import html
import json
import re
import time
from html.parser import HTMLParser
from http.cookiejar import CookieJar, DefaultCookiePolicy
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlunparse

import requests

from base.spider import Spider as BaseSpider


BASE_URL = "https://www.javrate.com"
USER_AGENT = (
    "Mozilla/5.0 (Linux; Android 11; TVBoxSpider/1.0) "
    "AppleWebKit/537.36 Chrome/120 Safari/537.36"
)
MEDIA_EXTENSIONS = (".m3u8", ".mp4", ".m4v", ".webm", ".mkv", ".ts")
SIGNED_HLS_QUERY_KEYS = ("token", "expires", "token_path")
REJECTED_MEDIA_WORDS = (
    "advert",
    "commercial",
    "preview",
    "sample",
    "trailer",
)
CHALLENGE_MARKERS = (
    "cf-chl-",
    "challenge-platform",
    "cloudflare ray id",
    "just a moment",
    "cf-turnstile",
)


def _attrs(items):
    return {str(key).lower(): (value or "") for key, value in items}


def _class_tokens(value):
    return set(re.findall(r"[a-z0-9_-]+", (value or "").lower()))


def _clean_text(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


class _RejectAllCookies(DefaultCookiePolicy):
    def set_ok(self, cookie, request):
        return False

    def return_ok(self, cookie, request):
        return False


class _PageParser(HTMLParser):
    CONTAINER_WORDS = ("card", "entry", "item", "movie", "post", "thumb", "video", "vod")
    VOID_TAGS = ("area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr")

    def __init__(self, base_url):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.anchors = []
        self.images = []
        self.meta = {}
        self.sources = []
        self.iframes = []
        self.next_url = ""
        self.page_numbers = []
        self.page_urls = {}
        self.declared_page_count = 0
        self.json_ld = []
        self.title = ""
        self._stack = []
        self._anchor = None
        self._title_parts = []
        self._script_type = ""
        self._script_parts = []

    def _context(self):
        classes = set()
        in_nav = False
        in_card = False
        for tag, attrs in self._stack:
            tokens = _class_tokens(attrs.get("class", ""))
            identifier = attrs.get("id", "").lower()
            classes.update(tokens)
            if tag == "nav" or "nav" in identifier or "menu" in identifier:
                in_nav = True
            if tag == "article" or any(
                word in token for token in tokens for word in self.CONTAINER_WORDS
            ):
                in_card = True
        return classes, in_nav, in_card

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attributes = _attrs(attrs)
        classes, in_nav, in_card = self._context()
        page_info = _clean_text(attributes.get("data-page-info", ""))
        page_count_match = re.search(r"共\s*(\d+)\s*頁", page_info)
        if page_count_match:
            self.declared_page_count = int(page_count_match.group(1))
        if tag == "meta":
            key = (
                attributes.get("property")
                or attributes.get("name")
                or attributes.get("itemprop")
                or ""
            ).lower()
            if key and attributes.get("content") and key not in self.meta:
                self.meta[key] = attributes["content"]
        elif tag == "link":
            rel = _class_tokens(attributes.get("rel", ""))
            if "next" in rel and attributes.get("href"):
                self.next_url = urljoin(self.base_url, attributes["href"])
        elif tag == "a":
            href = urljoin(self.base_url, attributes.get("href", ""))
            self._anchor = {
                "href": href,
                "text": [],
                "title": attributes.get("title", ""),
                "image": "",
                "image_alt": "",
                "in_nav": in_nav,
                "in_card": in_card,
                "classes": sorted(classes | _class_tokens(attributes.get("class", ""))),
                "rel": attributes.get("rel", ""),
                "category": attributes.get("data-category-name", ""),
                "mobile_category": attributes.get("data-qingkong-category", ""),
                "movie_id": attributes.get("data-movie-id", ""),
                "actress_id": attributes.get("data-actress-id", ""),
                "actress_name": attributes.get("data-actress-name", ""),
                "issuer_id": attributes.get("data-issuer-id", ""),
                "issuer_name": attributes.get("data-issuer-name", ""),
                "keyword_name": attributes.get("data-keyword-name", ""),
                "keyword_type": attributes.get("data-keyword-type", ""),
            }
        elif tag == "img":
            source = (
                attributes.get("data-src")
                or attributes.get("data-lazy-src")
                or attributes.get("src")
            )
            image = {
                "src": urljoin(self.base_url, source),
                "alt": attributes.get("alt", ""),
            }
            self.images.append(image)
            if self._anchor is not None:
                self._anchor["image"] = image["src"]
                self._anchor["image_alt"] = image["alt"]
        elif tag == "source":
            source = attributes.get("src", "")
            if source:
                self.sources.append(
                    {
                        "url": urljoin(self.base_url, source),
                        "label": attributes.get("label") or attributes.get("size", ""),
                        "type": attributes.get("type", ""),
                        "title": attributes.get("title", ""),
                    }
                )
        elif tag == "video":
            source = attributes.get("src", "")
            if source:
                self.sources.append(
                    {
                        "url": urljoin(self.base_url, source),
                        "label": attributes.get("data-quality", ""),
                        "type": attributes.get("type", ""),
                        "title": attributes.get("title", ""),
                    }
                )
        elif tag == "iframe":
            source = attributes.get("src", "")
            if source:
                self.iframes.append(urljoin(self.base_url, source))
        elif tag == "script":
            self._script_type = attributes.get("type", "").lower()
            self._script_parts = []
        if tag not in self.VOID_TAGS:
            self._stack.append((tag, attributes))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag.lower() not in self.VOID_TAGS:
            self.handle_endtag(tag)

    def handle_data(self, data):
        if self._anchor is not None:
            self._anchor["text"].append(data)
        if any(tag == "title" for tag, _ in self._stack):
            self._title_parts.append(data)
        if self._script_type == "application/ld+json":
            self._script_parts.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "a" and self._anchor is not None:
            self._anchor["text"] = _clean_text("".join(self._anchor["text"]))
            self.anchors.append(self._anchor)
            page_number = 0
            if "pagination-btn" in self._anchor["classes"] and self._anchor["text"].isdigit():
                page_number = int(self._anchor["text"])
            page_match = re.search(r"(?:/page/|[?&](?:page|paged)=)(\d+)", self._anchor["href"])
            if page_match:
                page_number = int(page_match.group(1))
            elif "pagination-btn" in self._anchor["classes"]:
                path = urlparse(self._anchor["href"]).path
                route_match = re.search(r"/actor/movie/\d+-\d+-\d+-(\d+)/", path)
                if not route_match:
                    route_match = re.search(r"/actor/list/\d+-\d+-(\d+)\.html$", path)
                if not route_match:
                    route_match = re.search(r"/\d+-\d+-(\d+)$", path)
                if route_match:
                    page_number = int(route_match.group(1))
            if page_number:
                self.page_numbers.append(page_number)
                self.page_urls[page_number] = self._anchor["href"]
            title = _clean_text(self._anchor.get("title", ""))
            if "next" in _class_tokens(self._anchor.get("rel", "")) or title in ("下一頁", "下一页"):
                self.next_url = self._anchor["href"]
            self._anchor = None
        elif tag == "script":
            if self._script_type == "application/ld+json":
                payload = "".join(self._script_parts).strip()
                if payload:
                    try:
                        self.json_ld.append(json.loads(payload))
                    except (TypeError, ValueError):
                        pass
            self._script_type = ""
            self._script_parts = []
        if self._stack:
            for index in range(len(self._stack) - 1, -1, -1):
                if self._stack[index][0] == tag:
                    del self._stack[index:]
                    break
        if tag == "title":
            self.title = _clean_text("".join(self._title_parts))


class Spider(BaseSpider):
    def init(self, extend=""):
        self.base_url = BASE_URL
        self.timeout = 15
        self.session = requests.Session()
        self.session.cookies = CookieJar(policy=_RejectAllCookies())
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
            }
        )
        self.category_page_urls = {}
        self.directory_options = {}
        self._playback_cache = {}

    def getName(self):
        return "JAVRate"

    def isVideoFormat(self, url):
        path = urlparse(str(url or "")).path.lower()
        return any(path.endswith(extension) for extension in MEDIA_EXTENSIONS)

    def manualVideoCheck(self):
        return False

    def _safe_message(self, error):
        message = re.sub(r"https?://[^\s]+", "<url>", str(error or "network failure"))
        return _clean_text(message)[:160]

    def _same_site_url(self, value):
        url = urljoin(self.base_url + "/", str(value or ""))
        parsed = urlparse(url)
        origin = urlparse(self.base_url)
        if parsed.scheme not in ("http", "https") or parsed.hostname != origin.hostname:
            return ""
        return url

    def _same_site_https_url(self, value):
        url = self._same_site_url(value)
        return url if urlparse(url).scheme == "https" else ""

    def _is_challenge(self, response, text):
        lowered = (text or "")[:200000].lower()
        server = response.headers.get("Server", "").lower()
        challenge_title = bool(
            re.search(r"<title[^>]*>\s*(?:just a moment|attention required|access denied)", lowered)
        )
        marker_count = sum(marker in lowered for marker in CHALLENGE_MARKERS)
        if challenge_title and marker_count:
            return True
        return (
            response.status_code in (403, 429, 503)
            and "cloudflare" in server
            and marker_count > 0
        )

    def _request(self, url, referer=""):
        target = self._same_site_url(url)
        if not target:
            return None, "refused non-JAVRate page URL"
        headers = {"Referer": referer} if referer else None
        try:
            response = self.session.get(
                target,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=True,
            )
            if not self._same_site_url(response.url):
                return None, "refused cross-site redirect"
            text = response.text
            if self._is_challenge(response, text):
                return None, "Cloudflare/challenge page received"
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if "html" not in content_type and "json" not in content_type and not text.lstrip().startswith("<"):
                return None, "unexpected page content type"
            return text, ""
        except requests.RequestException as error:
            return None, self._safe_message(error)

    def _parse(self, text, base_url):
        parser = _PageParser(base_url)
        parser.feed(text or "")
        parser.close()
        return parser

    def _looks_like_detail(self, url):
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        if not path or path in ("/category", "/tag", "/page"):
            return False
        if re.search(r"/(?:category|genre|tag|page)/", path, re.I):
            return False
        return parsed.hostname == urlparse(self.base_url).hostname

    def _cards(self, parser):
        videos = []
        seen = set()
        has_primary_grid = any("movie-card-link" in anchor["classes"] for anchor in parser.anchors)
        for anchor in parser.anchors:
            url = self._same_site_url(anchor["href"])
            explicit_card = bool(anchor["movie_id"]) or "movie-card-link" in anchor["classes"]
            if has_primary_grid and "right-movie-card" in anchor["classes"]:
                continue
            if not url or url in seen or not explicit_card or not self._looks_like_detail(url):
                continue
            name = _clean_text(anchor["title"] or anchor["text"] or anchor["image_alt"])
            if not name:
                continue
            videos.append(
                {
                    "vod_id": url,
                    "vod_name": name,
                    "vod_pic": anchor["image"],
                    "vod_remarks": "",
                }
            )
            seen.add(url)
        return videos

    def _categories(self, parser):
        categories = []
        seen = set()
        category_paths = (
            "/menu/uncensored",
            "/menu/censored",
            "/menu/chinese",
            "/actor/list",
            "/issuer",
            "/keywords/movie",
            "/movie/subtitle",
            "/best",
        )
        for anchor in parser.anchors:
            if not anchor.get("mobile_category"):
                continue
            url = self._same_site_url(anchor["href"])
            if not url or urlparse(url).path.rstrip("/") not in category_paths:
                continue
            visible_name = _clean_text(anchor["text"])
            name = visible_name or _clean_text(anchor["title"])
            if not name:
                continue
            if url in seen:
                if visible_name:
                    next(item for item in categories if item["type_id"] == url)["type_name"] = visible_name
                continue
            categories.append({"type_id": url, "type_name": name})
            seen.add(url)
        return categories

    def _directory_entries(self, directory_url, parser):
        path = urlparse(directory_url).path.rstrip("/").lower()
        entries = []
        seen = set()
        for anchor in parser.anchors:
            classes = set(anchor["classes"])
            name = ""
            target = ""
            if path == "/actor/list" and "actress-card-link" in classes:
                actress_id = anchor.get("actress_id", "")
                name = anchor.get("actress_name", "") or anchor["title"]
                if actress_id:
                    target = self._same_site_url("/actor/movie/{}.html".format(actress_id))
            elif path == "/issuer" and "issuer-card-link" in classes:
                name = anchor.get("issuer_name", "") or anchor["title"]
                target = self._same_site_url(anchor["href"])
            elif path == "/keywords/movie" and "keyword-recommend-link" in classes:
                if anchor.get("keyword_type", "").lower() != "movie":
                    continue
                name = anchor.get("keyword_name", "") or anchor["title"]
                target = self._same_site_url(anchor["href"])
            name = _clean_text(name)
            if not name or not target or target in seen:
                continue
            entries.append({"n": name, "v": target})
            seen.add(target)
        return entries[:40]

    def _directory_values(self, directory_url):
        if directory_url in self.directory_options:
            return self.directory_options[directory_url], ""
        text, error = self._request(directory_url, referer=self.base_url + "/")
        if error:
            return [], error
        entries = self._directory_entries(directory_url, self._parse(text, directory_url))
        if not entries:
            return [], "directory exposed no movie-list entries"
        self.directory_options[directory_url] = entries
        return entries, ""

    def _home_filters(self, categories):
        filters = {}
        directory_paths = ("/actor/list", "/issuer", "/keywords/movie")
        for category in categories:
            category_url = category["type_id"]
            if urlparse(category_url).path.rstrip("/").lower() not in directory_paths:
                continue
            entries, _ = self._directory_values(category_url)
            if entries:
                filters[category_url] = [
                    {
                        "key": "entry",
                        "name": category["type_name"],
                        "init": entries[0]["v"],
                        "value": entries,
                    }
                ]
        return filters

    def _resolved_category(self, category_url, extend):
        path = urlparse(category_url).path.rstrip("/").lower()
        if path not in ("/actor/list", "/issuer", "/keywords/movie"):
            return category_url, ""
        entries, error = self._directory_values(category_url)
        if error:
            return "", error
        selected = str((extend or {}).get("entry", "")) if isinstance(extend, dict) else ""
        allowed = {item["v"] for item in entries}
        if selected and selected not in allowed:
            return "", "directory entry was not observed"
        return selected or entries[0]["v"], ""

    def _pagination(self, parser, requested_page, count):
        known_pages = [page for page in parser.page_numbers if page > 0]
        pagecount = parser.declared_page_count or (max(known_pages) if known_pages else requested_page)
        if parser.next_url and pagecount <= requested_page:
            pagecount = requested_page + 1
        result = {
            "page": requested_page,
            "pagecount": pagecount,
            "limit": count,
        }
        return result

    def _remember_pagination(self, category_url, parser, requested_page, target):
        page_urls = self.category_page_urls.setdefault(category_url, {})
        page_urls[requested_page] = target
        for page_number, page_url in parser.page_urls.items():
            safe_url = self._same_site_url(page_url)
            if safe_url:
                page_urls[page_number] = safe_url
        if parser.next_url:
            safe_next = self._same_site_url(parser.next_url)
            if safe_next:
                page_urls.setdefault(requested_page + 1, safe_next)

    def _page_url(self, category_url, page):
        if page <= 1:
            return category_url
        return self.category_page_urls.get(category_url, {}).get(page, "")

    def homeContent(self, filter=False):
        text, error = self._request(self.base_url + "/")
        if error:
            return {"class": [], "filters": {}, "msg": error}
        parser = self._parse(text, self.base_url + "/")
        categories = self._categories(parser)
        filters = self._home_filters(categories) if filter else {}
        return {"class": categories, "filters": filters}

    def homeVideoContent(self):
        text, error = self._request(self.base_url + "/")
        if error:
            return {"list": [], "msg": error}
        return {"list": self._cards(self._parse(text, self.base_url + "/"))}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        try:
            page = max(1, int(str(pg)))
        except (TypeError, ValueError):
            page = 1
        category_url = self._same_site_url(tid)
        if not category_url:
            return {"list": [], "page": page, "pagecount": page, "limit": 0, "msg": "invalid category URL"}
        resolved_url, resolution_error = self._resolved_category(category_url, extend)
        if resolution_error:
            return {"list": [], "page": page, "pagecount": page, "limit": 0, "msg": resolution_error}
        target = self._page_url(resolved_url, page)
        if not target:
            return {
                "list": [],
                "page": page,
                "pagecount": page,
                "limit": 0,
                "msg": "pagination URL not observed; request page 1 first",
            }
        text, error = self._request(target, referer=category_url)
        if error:
            return {"list": [], "page": page, "pagecount": page, "limit": 0, "msg": error}
        parser = self._parse(text, target)
        self._remember_pagination(resolved_url, parser, page, target)
        videos = self._cards(parser)
        result = {"list": videos}
        result.update(self._pagination(parser, page, len(videos)))
        return result

    def _json_ld_objects(self, value):
        if isinstance(value, list):
            for item in value:
                for nested in self._json_ld_objects(item):
                    yield nested
        elif isinstance(value, dict):
            yield value
            for key in ("@graph", "video"):
                if key in value:
                    for nested in self._json_ld_objects(value[key]):
                        yield nested

    def _video_object(self, parser):
        for payload in parser.json_ld:
            for item in self._json_ld_objects(payload):
                item_type = item.get("@type", "")
                types = item_type if isinstance(item_type, list) else [item_type]
                if "VideoObject" in types and item.get("contentUrl"):
                    return item
        return {}

    def _player_iframe_url(self, parser):
        candidates = []
        for url in parser.iframes:
            parsed = urlparse(url)
            if (
                parsed.scheme == "https"
                and parsed.hostname == urlparse(self.base_url).hostname
                and parsed.path.rstrip("/").lower() == "/player/v2"
                and [key for key, _ in parse_qsl(parsed.query, keep_blank_values=True)]
                == ["payload", "poster"]
            ):
                candidates.append(url)
        return candidates[0] if len(candidates) == 1 else ""

    def _new_player_session(self):
        session = requests.Session()
        session.cookies = CookieJar(policy=_RejectAllCookies())
        session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
            }
        )
        return session

    def _valid_signed_master(self, url):
        parsed = urlparse(url)
        query = parse_qsl(parsed.query, keep_blank_values=True)
        values = dict(query)
        path_parts = [part for part in parsed.path.split("/") if part]
        if (
            parsed.scheme != "https"
            or parsed.hostname != "videocdn.avking.xyz"
            or len(path_parts) != 2
            or path_parts[-1] != "playlist.m3u8"
            or [key for key, _ in query] != list(SIGNED_HLS_QUERY_KEYS)
            or len(values) != len(SIGNED_HLS_QUERY_KEYS)
            or not values.get("token", "").startswith("HS256-")
            or not values.get("token_path")
        ):
            return False
        try:
            return int(values["expires"]) > int(time.time())
        except (KeyError, TypeError, ValueError):
            return False

    def _signed_url_from_player(self, text):
        match = re.search(r"\bsignedUrl\s*:\s*(['\"])(.*?)\1", text or "", re.S)
        if not match:
            return ""
        url = html.unescape(match.group(2)).replace("\\/", "/")
        return url if self._valid_signed_master(url) else ""

    def _fresh_signed_master(self, detail_url):
        session = self._new_player_session()
        iframe_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Sec-Fetch-Dest": "iframe",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Upgrade-Insecure-Requests": "1",
        }
        try:
            detail = session.get(
                detail_url,
                headers={"Referer": self.base_url + "/"},
                timeout=self.timeout,
                allow_redirects=False,
            )
            detail.raise_for_status()
            if not self._same_site_https_url(detail.url) or self._is_challenge(detail, detail.text):
                return "", "", "detail request did not return JAVRate HTTPS HTML"
            iframe_url = self._player_iframe_url(self._parse(detail.text, detail.url))
            if not iframe_url:
                return "", detail.text, "detail did not expose one valid /Player/V2 iframe"
            iframe_headers["Referer"] = detail.url
            redirect = session.get(
                iframe_url,
                headers=iframe_headers,
                timeout=self.timeout,
                allow_redirects=False,
            )
            if redirect.status_code != 301 or not redirect.headers.get("Location"):
                return "", detail.text, "player iframe did not return the expected 301"
            player_url = urljoin(redirect.url, redirect.headers["Location"])
            if not self._same_site_https_url(player_url):
                return "", detail.text, "player iframe redirect left JAVRate HTTPS"
            player = session.get(
                player_url,
                headers=iframe_headers,
                timeout=self.timeout,
                allow_redirects=False,
            )
            player.raise_for_status()
            content_type = player.headers.get("Content-Type", "").lower()
            if (
                not self._same_site_https_url(player.url)
                or "html" not in content_type
                or self._is_challenge(player, player.text)
            ):
                return "", detail.text, "player redirect did not return JAVRate HTTPS HTML"
            signed_url = self._signed_url_from_player(player.text)
            if not signed_url:
                return "", detail.text, "player HTML did not expose a valid fresh signedUrl"
            return signed_url, detail.text, ""
        except requests.RequestException as error:
            return "", "", self._safe_message(error)

    def _fresh_signed_variants(self, master_url):
        headers = {
            "User-Agent": USER_AGENT,
            "Origin": self.base_url,
            "Referer": self.base_url + "/",
        }
        try:
            response = requests.get(
                master_url,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=False,
            )
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if (
                response.url != master_url
                or "mpegurl" not in content_type
                or not response.text.lstrip().startswith("#EXTM3U")
            ):
                return [], "signed master did not return HLS"
            variants = self._hls_variants(master_url, response.text)
            return variants, "" if variants else "signed master exposed no variants"
        except requests.RequestException as error:
            return [], self._safe_message(error)

    def _hls_variants(self, manifest_url, text):
        if not (text or "").lstrip().startswith("#EXTM3U"):
            return []
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        variants = []
        seen = set()
        for index, line in enumerate(lines):
            if not line.startswith("#EXT-X-STREAM-INF:"):
                continue
            attrs = line.split(":", 1)[1]
            resolution = re.search(r"(?:^|,)RESOLUTION=(\d+)x(\d+)(?:,|$)", attrs, re.I)
            bandwidth = re.search(r"(?:^|,)BANDWIDTH=(\d+)(?:,|$)", attrs, re.I)
            uri = next((item for item in lines[index + 1 :] if not item.startswith("#")), "")
            if not uri:
                continue
            url = self._hls_child_url(manifest_url, uri)
            if url in seen:
                continue
            if resolution:
                quality = "{}p".format(resolution.group(2))
            elif bandwidth:
                quality = "{}kbps".format(int(bandwidth.group(1)) // 1000)
            else:
                quality = "HLS"
            variants.append({"url": url, "quality": quality})
            seen.add(url)
        return variants

    def _hls_child_url(self, manifest_url, child_uri):
        child = urljoin(manifest_url, child_uri)
        master_parsed = urlparse(manifest_url)
        child_parsed = urlparse(child)
        explicit_child_query = bool(urlparse(child_uri).query)
        if (
            explicit_child_query
            or child_parsed.hostname != master_parsed.hostname
            or child_parsed.port != master_parsed.port
        ):
            return child
        inherited = [
            (key, value)
            for key, value in parse_qsl(master_parsed.query, keep_blank_values=True)
            if key in SIGNED_HLS_QUERY_KEYS
        ]
        if not inherited:
            return child
        return urlunparse(child_parsed._replace(query=urlencode(inherited)))

    def detailContent(self, ids):
        identifier = ids[0] if isinstance(ids, (list, tuple)) and ids else ""
        detail_url = self._same_site_https_url(identifier)
        if not detail_url:
            return {"list": [], "msg": "invalid detail URL"}
        master_url, text, error = self._fresh_signed_master(detail_url)
        if error:
            return {"list": [], "msg": error}
        parser = self._parse(text, detail_url)
        variants, variant_error = self._fresh_signed_variants(master_url)
        if variants:
            expires = int(dict(parse_qsl(urlparse(master_url).query)).get("expires", "0"))
            if expires > int(time.time()) + 5:
                self._playback_cache[detail_url] = {
                    "master": master_url,
                    "variants": variants,
                    "expires": expires,
                }
                if len(self._playback_cache) > 12:
                    self._playback_cache.pop(next(iter(self._playback_cache)))
        play_from = "$$$".join(item["quality"] for item in variants)
        play_url = "$$$".join(
            "{}${}".format(item["quality"], detail_url) for item in variants
        )
        video_object = self._video_object(parser)
        title = _clean_text(
            video_object.get("name")
            or parser.meta.get("og:title")
            or parser.meta.get("twitter:title")
            or parser.title
        )
        thumbnail = video_object.get("thumbnailUrl", "")
        if isinstance(thumbnail, list):
            thumbnail = thumbnail[0] if thumbnail else ""
        picture = urljoin(
            detail_url,
            thumbnail
            or parser.meta.get("og:image")
            or parser.meta.get("twitter:image", ""),
        )
        description = _clean_text(
            video_object.get("description")
            or parser.meta.get("og:description")
            or parser.meta.get("description", "")
        )
        actors = video_object.get("actor", [])
        if isinstance(actors, dict):
            actors = [actors]
        actor_names = []
        for actor in actors if isinstance(actors, list) else []:
            name = actor.get("name", "") if isinstance(actor, dict) else str(actor)
            if _clean_text(name):
                actor_names.append(_clean_text(name))
        video = {
            "vod_id": detail_url,
            "vod_name": title,
            "vod_pic": picture,
            "type_name": "",
            "vod_year": "",
            "vod_area": "",
            "vod_remarks": "" if variants else variant_error or "未发现已验证的正片源",
            "vod_actor": ", ".join(actor_names),
            "vod_director": "",
            "vod_content": description,
            "vod_play_from": play_from,
            "vod_play_url": play_url,
        }
        return {"list": [video]}

    def _proxy_playlist_url(self, playlist_url):
        base = self.getProxyUrl(True)
        separator = "&" if "?" in base else "?"
        return "{}{}url={}".format(base, separator, quote(playlist_url, safe=""))

    def _valid_signed_hls_url(self, url):
        parsed = urlparse(str(url or ""))
        if parsed.scheme != "https" or parsed.hostname != "videocdn.avking.xyz":
            return False
        if not (parsed.path.endswith("/playlist.m3u8") or re.search(r"/[^/]+/video\.m3u8$", parsed.path)):
            return False
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
        if [key for key, _ in pairs] != list(SIGNED_HLS_QUERY_KEYS):
            return False
        values = dict(pairs)
        try:
            fresh = int(values.get("expires", "0")) > int(time.time())
        except (TypeError, ValueError):
            return False
        return (
            values.get("token", "").startswith("HS256-")
            and fresh
            and values.get("token_path", "").startswith("/")
        )

    def playerContent(self, flag, id, vipFlags=None):
        detail_url = self._same_site_https_url(str(id or ""))
        if not detail_url or not self._looks_like_detail(detail_url):
            return {"parse": 1, "url": "", "header": {}, "msg": "invalid detail URL"}
        cached = self._playback_cache.get(detail_url, {})
        if cached.get("expires", 0) > int(time.time()) + 5:
            master_url = cached["master"]
            variants = cached["variants"]
        else:
            self._playback_cache.pop(detail_url, None)
            master_url, _, error = self._fresh_signed_master(detail_url)
            if error:
                return {"parse": 1, "url": "", "header": {}, "msg": error}
            variants = None
        url = master_url
        quality = str(flag or "")
        if quality and quality != "JAVRate":
            if variants is None:
                variants, error = self._fresh_signed_variants(master_url)
            else:
                error = ""
            url = next((item["url"] for item in variants if item["quality"] == quality), "")
            if error or not url:
                return {
                    "parse": 1,
                    "url": "",
                    "header": {},
                    "msg": error or "requested HLS quality unavailable",
                }
        return {"parse": 0, "url": self._proxy_playlist_url(url), "header": {}}

    def searchContent(self, key, quick=False, pg=1):
        try:
            page = max(1, int(str(pg)))
        except (TypeError, ValueError):
            page = 1
        term = str(key or "").strip()
        if len(term) < 2:
            return {
                "list": [],
                "page": page,
                "pagecount": page,
                "limit": 0,
                "msg": "search requires at least 2 characters",
            }
        query = quote(term, safe="-_.!~*'()")
        if page == 1:
            target = "{}/search/{}".format(self.base_url, query)
        else:
            target = "{}/search/a%E7%89%87/{}/?tab=movie&page={}".format(
                self.base_url, query, page
            )
        text, error = self._request(target, referer=self.base_url + "/")
        if error:
            return {"list": [], "page": page, "pagecount": page, "limit": 0, "msg": error}
        parser = self._parse(text, target)
        videos = self._cards(parser)
        result = {"list": videos}
        result.update(self._pagination(parser, page, len(videos)))
        return result

    def localProxy(self, param):
        target = str((param or {}).get("url", ""))
        if not self._valid_signed_hls_url(target):
            return [403, "text/plain; charset=utf-8", "invalid or expired JAVRate HLS URL"]
        headers = {
            "User-Agent": USER_AGENT,
            "Origin": self.base_url,
            "Referer": self.base_url + "/",
        }
        try:
            response = requests.get(
                target,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=False,
            )
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if (
                response.url != target
                or "mpegurl" not in content_type
                or not response.text.lstrip().startswith("#EXTM3U")
            ):
                return [502, "text/plain; charset=utf-8", "upstream did not return HLS"]
            lines = []
            for raw_line in response.text.splitlines():
                line = raw_line.strip()
                if line and not line.startswith("#"):
                    line = self._hls_child_url(target, line)
                lines.append(line if raw_line == raw_line.strip() else line)
            body = "\n".join(lines) + "\n"
            return [200, "application/vnd.apple.mpegurl", body]
        except requests.RequestException as error:
            return [502, "text/plain; charset=utf-8", self._safe_message(error)]
