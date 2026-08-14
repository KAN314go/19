# -*- coding: utf-8 -*-
#!/usr/bin/env python3

"""
4KPorno.XXX
"""

import sys
import os
import re
import json
import random
import html as html_module
import gzip
import base64
from urllib import parse, request

DEBUG = os.environ.get("SPIDER_DEBUG", "0") == "1"


def _log(msg):
    if DEBUG:
        print(f"[DEBUG] {msg}", file=sys.stderr)


class BaseSpider:
    UA_POOL = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_2 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
    ]

    def __init__(self):
        pass

    @classmethod
    def _random_ua(cls):
        return random.choice(cls.UA_POOL)

    @classmethod
    def _build_headers(cls, extra=None):
        h = {
            "User-Agent": cls._random_ua(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        if extra:
            h.update(extra)
        return h

    def fetch(self, url, headers=None, timeout=15):
        h = self._build_headers(headers)
        req = request.Request(url, headers=h, method="GET")
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                ce = resp.headers.get("Content-Encoding", "")
                if "gzip" in ce:
                    data = gzip.decompress(data)
                elif "br" in ce:
                    try:
                        import brotli
                        data = brotli.decompress(data)
                    except ImportError:
                        pass
                charset = "utf-8"
                ct = resp.headers.get("Content-Type", "")
                m = re.search(r"charset=([\w-]+)", ct, re.I)
                if m:
                    charset = m.group(1)
                try:
                    return data.decode(charset)
                except UnicodeDecodeError:
                    return data.decode("utf-8", errors="replace")
        except Exception as e:
            _log(f"fetch error: {e}")
            return ""

    def fetch_binary(self, url, headers=None, timeout=15):
        h = self._build_headers(headers)
        req = request.Request(url, headers=h, method="GET")
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                ce = resp.headers.get("Content-Encoding", "")
                if "gzip" in ce:
                    data = gzip.decompress(data)
                elif "br" in ce:
                    try:
                        import brotli
                        data = brotli.decompress(data)
                    except ImportError:
                        pass
                ct = resp.headers.get("Content-Type", "application/octet-stream")
                return resp.status, ct, data
        except Exception as e:
            _log(f"fetch_binary error: {e}")
            return 404, "text/plain", b""

    @staticmethod
    def clean_title(title):
        t = html_module.unescape(title or "")
        t = re.sub(r"<[^>]+>", "", t)
        return t.strip()

    @staticmethod
    def _proxy_pic_url(pic_url):
        if not pic_url:
            return ""
        # v16: @2x编码为%402x，避免TVBox对@字符解析bug
        # 实测medium@2x直接返回在TVBox裂图，%402x能正常显示
        return pic_url.replace("@2x", "%402x")

    def homeContent(self, filter=False):
        raise NotImplementedError

    def categoryContent(self, tid, pg, filter, extend):
        raise NotImplementedError

    def detailContent(self, ids):
        raise NotImplementedError

    def playerContent(self, flag, id, vipFlags):
        raise NotImplementedError

    def searchContent(self, key, quick, pg="1"):
        raise NotImplementedError

    def localProxy(self, param):
        return [404, "text/plain", "不支持本地代理"]

    def init(self, extend=""):
        return True

    def isVideoFormat(self, url):
        fmt = [".m3u8", ".mp4", ".flv", ".mkv", ".ts", ".avi", ".mov", ".webm"]
        return any(f in url.lower() for f in fmt)

    def manualVideoCheck(self):
        return False


class Spider(BaseSpider):
    realm_name = "4KPorno"
    realm_level = 1
    defense_level = 0

    siteUrl = "https://www.4kporno.xxx"
    lang = ""

    SORTS = {
        "latest-updates": "最新更新",
        "top-rated": "最高评分",
        "most-popular": "最受欢迎",
    }

    CATEGORIES = {
        "asian": "亚洲的", "big-ass": "大屁股", "big-tits": "大奶",
        "blonde": "金发女郎", "blowjob": "口交", "brunette": "黑发女郎",
        "creampie": "体内射精", "cumshot": "射精", "anal": "肛门",
        "ebony": "乌木色", "gangbang": "Gangbang", "hardcore": "硬核",
        "interracial": "跨种族", "japanese": "日本人", "korean": "韩国人",
        "lesbian": "女同性恋", "milf": "MILF", "pov": "POV",
        "redhead": "红发女郎", "teen": "青少年", "threesome": "三人行",
    }

    SITES = {
        "my-dirty-uncle": "My Dirty Uncle",
        "new-sensations": "New Sensations",
        "momswapped": "MomSwapped",
        "private": "Private",
    }

    NETWORKS = {}

    RE_ITEM = re.compile(
        r'<div class="item">\s*<a href="(https?://[^"]+/videos/(\d+)/[^"]*/?)"[^>]*title="([^"]*)"[^>]*>'
        r'.*?<img[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>.*?</a>',
        re.S
    )

    def _extract_list(self, html):
        videos = []
        seen = set()
        for match in self.RE_ITEM.finditer(html):
            full_url, vid, title, pic, alt = match.groups()
            if vid in seen:
                continue
            seen.add(vid)
            path = full_url.replace(self.siteUrl, "")
            videos.append({
                "vod_id": path,
                "vod_name": self.clean_title(title or alt),
                "vod_pic": self._proxy_pic_url(pic),
                "vod_remarks": "",
            })
        return videos

    def _build_url(self, path):
        if path.startswith("http"):
            return path
        return f"{self.siteUrl}{path}"

    def homeContent(self, filter=False):
        classes = []
        for sort_id, sort_name in self.SORTS.items():
            classes.append({"type_name": sort_name, "type_id": f"sort:{sort_id}"})
        for cat_id, cat_name in self.CATEGORIES.items():
            classes.append({"type_name": cat_name, "type_id": f"cat:{cat_id}"})
        for site_id, site_name in self.SITES.items():
            classes.append({"type_name": site_name, "type_id": f"site:{site_id}"})
        for net_id, net_name in self.NETWORKS.items():
            classes.append({"type_name": net_name, "type_id": f"net:{net_id}"})
        return {"class": classes}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if str(pg).isdigit() else 1

        if tid.startswith("sort:"):
            sort_id = tid.replace("sort:", "")
            if sort_id == "latest":
                sort_id = "latest-updates"
            path = f"/{sort_id}/{page}/" if page > 1 else f"/{sort_id}/"
        elif tid.startswith("search:"):
            kw = tid.replace("search:", "")
            kw = parse.quote(kw)
            path = f"/search/{kw}/{page}/" if page > 1 else f"/search/{kw}/"
        elif tid.startswith("cat:"):
            cat_id = tid.replace("cat:", "")
            path = f"/categories/{cat_id}/{page}/" if page > 1 else f"/categories/{cat_id}/"
        elif tid.startswith("site:"):
            site_id = tid.replace("site:", "")
            path = f"/sites/{site_id}/{page}/" if page > 1 else f"/sites/{site_id}/"
        elif tid.startswith("net:"):
            net_id = tid.replace("net:", "")
            path = f"/networks/{net_id}/{page}/" if page > 1 else f"/networks/{net_id}/"
        else:
            path = f"/categories/{tid}/{page}/" if page > 1 else f"/categories/{tid}/"

        url = self._build_url(path)
        html = self.fetch(url, timeout=15)
        videos = self._extract_list(html)

        if not videos and page > 1 and tid.startswith("cat:"):
            cat_id = tid.replace("cat:", "")
            path = f"/categories/{cat_id}/latest-updates/{page}/"
            html = self.fetch(self._build_url(path), timeout=15)
            videos = self._extract_list(html)

        has_next = len(videos) >= 20
        return {
            "list": videos,
            "page": page,
            "pagecount": 999 if has_next else page,
            "limit": len(videos),
            "total": 999 * len(videos) if has_next else page * len(videos),
        }

    def detailContent(self, ids):
        vid = ids[0]
        if vid.startswith("/"):
            url = self._build_url(vid)
        elif "/videos/" in vid:
            url = vid if vid.startswith("http") else self._build_url(vid)
        else:
            url = f"{self.siteUrl}/videos/{vid}/"

        html = self.fetch(url, timeout=15)
        if not html:
            return {"list": []}

        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S | re.I)
        title = self.clean_title(title_match.group(1)) if title_match else "未知"

        pic_match = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]+)"', html, re.I)
        pic = pic_match.group(1) if pic_match else ""

        desc_match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]+)"', html, re.I)
        desc = desc_match.group(1) if desc_match else ""

        play_url = ""
        video_block = re.search(r'<video[^>]*>.*?</video>', html, re.S | re.I)
        if video_block:
            block = video_block.group(0)
            sources = re.findall(r'''<source[^>]*src=['"]([^'"]*)['"][^>]*label=['"]([^'"]*)['"]''', block)
            if sources:
                # v19: 2160p放第一个（用户要求），但文件近1GB加载慢是物理限制
                # 建议TVBox播放界面手动切换720p（约150MB，快3倍）
                priority = ["2160p", "1080p", "720p", "480p", "360p"]
                sources.sort(key=lambda x: priority.index(x[1]) if x[1] in priority else 99)
                play_parts = []
                for src, label in sources:
                    pass  # keep trailing slash
                    play_parts.append(f"{label}${src}")
                play_url = "#".join(play_parts)
            else:
                mp4s = re.findall(r'''https?://[^\s"'<>]+\.mp4/?''', html)
                real_mp4s = [u for u in mp4s if "preview" not in u and "screenshot" not in u]
                if real_mp4s:
                    play_url = f"正片${real_mp4s[0].rstrip('/')}"
        else:
            mp4s = re.findall(r'''https?://[^\s"'<>]+\.mp4/?''', html)
            real_mp4s = [u for u in mp4s if "preview" not in u and "screenshot" not in u]
            if real_mp4s:
                play_url = f"正片${real_mp4s[0].rstrip('/')}"

        if not play_url:
            play_url = f"正片${url}"

        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": self._proxy_pic_url(pic),
                "vod_content": desc,
                "vod_play_from": "4KPorno",
                "vod_play_url": play_url,
            }]
        }

    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {"parse": 1, "url": "", "header": ""}

        real_url = id
        if "$" in id:
            real_url = id.split("$")[1]
            if "#" in real_url:
                real_url = real_url.split("#")[0]
                if "$" in real_url:
                    real_url = real_url.split("$")[1]

        if not real_url.startswith("http"):
            real_url = self._build_url(real_url)

        return {
            "parse": 0,
            "url": real_url,
            "header": json.dumps({
                "Referer": self.siteUrl + "/",
                "User-Agent": self._random_ua(),
                "Accept": "*/*",
                "Accept-Encoding": "identity",
                "Connection": "keep-alive",
            }),
        }

    def searchContent(self, key, quick, pg="1"):
        return self.categoryContent(tid=f"search:{key}", pg=pg, filter=False, extend={})

    def localProxy(self, param):
        return [404, "text/plain", "不支持本地代理"]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="4KPorno.XXX 爬虫源 v13")
    parser.add_argument("--test", choices=["home", "category", "detail", "player", "search"], help="测试接口")
    parser.add_argument("--id", default="/zh/videos/93817649/hotel-vixen-season-3-episode-2-unparalleled-customer-service/", help="视频路径")
    parser.add_argument("--cat", default="site:my-dirty-uncle", help="分类ID")
    parser.add_argument("--kw", default="lesbian", help="搜索关键词")
    args = parser.parse_args()

    spider = Spider()

    if args.test == "home" or not args.test:
        result = spider.homeContent()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.test == "category":
        result = spider.categoryContent(tid=args.cat, pg="1", filter=False, extend={})
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.test == "detail":
        result = spider.detailContent([args.id])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.test == "player":
        detail = spider.detailContent([args.id])
        play_url = detail["list"][0]["vod_play_url"] if detail.get("list") else ""
        result = spider.playerContent(flag="4KPorno", id=play_url, vipFlags="")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.test == "search":
        result = spider.searchContent(key=args.kw, quick="1", pg="1")
        print(json.dumps(result, ensure_ascii=False, indent=2))

