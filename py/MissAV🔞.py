# coding: utf-8
import json
import re
from html import unescape
from urllib.parse import quote, urljoin
from base.spider import Spider


class Spider(Spider):
    host = "https://missav123.com"
    lang = "cn"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36",
        "Referer": "https://missav123.com/",
    }
    categories = [
        ("最近更新", "dm539/cn/new"),
        ("新作上市", "dm635/cn/release"),
        ("无码流出", "dm817/cn/uncensored-leak"),
        ("中文字幕", "dm278/cn/chinese-subtitle"),
    ]

    def init(self, extend=''):
        self.host = "https://missav123.com"

    def _get(self, url):
        try:
            r = self.fetch(url, headers=self.headers)
            if isinstance(r, str):
                return r
            text = getattr(r, "text", None)
            if text is not None:
                return text
            content = getattr(r, "content", None)
            if isinstance(content, bytes):
                return content.decode("utf-8", "ignore")
            return str(content or r)
        except Exception:
            return ""

    @staticmethod
    def _clean(s):
        return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

    def _cards(self, html):
        result, seen = [], set()
        for cm in re.finditer(r'data-src="(https://fourhoi\.com/([^/" ]+)/cover-[nt]\.jpg)"', html or '', re.I):
            pic, slug = cm.group(1), cm.group(2)
            if slug in seen or not re.search(r'\d', slug):
                continue
            window = (html or '')[cm.start():cm.start() + 1800]
            link = re.search(r'href="(?:https://[^/]+)?/cn/' + re.escape(slug) + r'"[^>]*>(.*?)</a>', window, re.S | re.I)
            title = self._clean(link.group(1)) if link else ''
            alt = re.search(r'\balt="([^"]+)"', window, re.I)
            if alt and (not title or re.fullmatch(r"\d+:\d{2}:\d{2}", title)):
                title = self._clean(alt.group(1))
            if not title:
                continue
            seen.add(slug)
            result.append({"vod_id": slug, "vod_name": slug.upper() + ' ' + title, "vod_pic": pic})
        return result

    def _unpack(self, html):
        text = html or ''
        pos = text.find("return p}('")
        if pos >= 0:
            start = pos + len("return p}('")
            end = text.find("',16,16,'", start)
            table_end = text.find("'.split", end + 10)
            if end > start and table_end > end:
                payload = text[start:end].replace("\\'", "'")
                table = text[end + 9:table_end].split('|')
                if table and table[0] == '':
                    table = table[1:]
                # 采用 Packer 的边界替换，避免短 token 污染长 UUID。
                for i in range(15, -1, -1):
                    token = self._base36(i)
                    value = table[i] if i < len(table) and table[i] else token
                    payload = re.sub(r'(?<![A-Za-z0-9_$])' + re.escape(token) + r'(?![A-Za-z0-9_$])', value, payload)
                payload = payload.replace("\\'", "'")
                found = re.search(r"https?://[^'\" ]+\.m3u8", payload)
                if found:
                    return found.group(0)
        return ''

    @staticmethod
    def _base36(n):
        chars = '0123456789abcdefghijklmnopqrstuvwxyz'
        if n < 36:
            return chars[n]
        out = ''
        while n:
            out = chars[n % 36] + out
            n //= 36
        return out or '0'

    def homeContent(self, filter):
        return {"class": [{"type_id": x[1], "type_name": x[0]} for x in self.categories], "list": []}

    def homeVideoContent(self):
        html = self._get(self.host + '/dm247/cn')
        return {"list": self._cards(html)}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg or 1)
        url = self.host + '/' + tid.strip('/')
        if page > 1:
            url += ('&' if '?' in url else '?') + 'page=%d' % page
        html = self._get(url)
        items = self._cards(html)
        return {"list": items, "page": page, "pagecount": 2000, "limit": len(items), "total": 0}

    def searchContent(self, key, quick, pg='1'):
        page = int(pg or 1)
        url = self.host + '/search/' + quote(key)
        if page > 1:
            url += '?page=%d' % page
        html = self._get(url)
        items = self._cards(html)
        return {"list": items, "page": page, "pagecount": 999, "limit": len(items), "total": 0}

    def detailContent(self, ids):
        slug = str(ids[0] if isinstance(ids, list) else ids).strip('/')
        html = self._get(self.host + '/cn/' + slug)
        title = slug.upper()
        tm = re.search(r'<title[^>]*>(.*?)</title>', html or '', re.S | re.I)
        if tm:
            title = self._clean(tm.group(1))
        pic = 'https://fourhoi.com/%s/cover-n.jpg' % slug
        dm = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]*)"', html or '', re.I)
        desc = unescape(dm.group(1)) if dm else ''
        stream = self._unpack(html)
        play = '播放$' + stream if stream else ''
        if not play:
            return {"list": [{"vod_id": slug, "vod_name": title, "vod_pic": pic,
                "vod_content": desc, "vod_play_from": "MissAV",
                "vod_play_url": ""}]}
        return {"list": [{"vod_id": slug, "vod_name": title, "vod_pic": pic,
            "vod_content": desc, "vod_play_from": "MissAV",
            "vod_play_url": play}]}

    def playerContent(self, flag, id, vipFlags):
        if str(id).startswith('http') and '.m3u8' in str(id):
            return {"parse": 0, "url": id, "header": json.dumps(self.headers, ensure_ascii=False)}
        slug = str(id).strip('/').split('/')[-1]
        stream = self._unpack(self._get(self.host + '/cn/' + slug))
        if not stream:
            return {"parse": 0, "url": "", "header": json.dumps(self.headers, ensure_ascii=False)}
        return {"parse": 0, "url": stream, "header": json.dumps(self.headers, ensure_ascii=False)}

    def isVideoFormat(self, url):
        return '.m3u8' in str(url) or '.mp4' in str(url)
