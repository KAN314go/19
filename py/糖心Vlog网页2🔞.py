# -*- coding: utf-8 -*-

import json
import re
import os
import sys
import base64
from urllib.parse import quote, unquote, urljoin

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        pass

try:
    import requests
except ImportError:
    requests = None

HOST = "https://tangxinvlog.pro"
UA = "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
REFERER = HOST + "/"


class Spider(BaseSpider):
    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass

    def init(self, extend=""):
        self.session = requests.Session() if requests else None
        if self.session:
            self.session.headers.update({"User-Agent": UA, "Referer": REFERER})

    def getName(self):
        return "糖心Vlog"

    # ─────────────── 工具 ───────────────

    def _get(self, url):
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code == 200:
                # The site omits/incorrectly declares charset on some HTML pages.
                r.encoding = "utf-8"
                return r.text
        except Exception:
            pass
        return ""

    def _proxy_url(self, url):
        """引擎标准 getProxyUrl()+localProxy 回调; 拿不到代理地址则原样返回"""
        base = self.getProxyUrl() if hasattr(self, "getProxyUrl") else ""
        if not base:
            return url
        b64 = base64.b64encode(url.encode("utf-8")).decode("utf-8")
        sep = "&" if "?" in base else "?"
        return base + sep + "type=stream&url=" + quote(b64, safe="")

    def _proxy_pic(self, url):
        """CDN 封面也要求 Referer，不能把原始 CDN URL 直接交给播放器。"""
        return self._proxy_url(url) if url else ""

    def _parse_cards(self, html):
        out = []
        for m in re.finditer(r'<a class="video-card" href="(/videos/[a-f0-9]+/)"[^>]*>(.*?)</a>', html, re.S):
            vid_url, inner = m.group(1), m.group(2)
            img = re.search(r'src="([^"]*)"', inner) or re.search(r'data-src="([^"]*)"', inner)
            title = re.search(r'class="title">([^<]*)</h3>', inner) or re.search(r'title="([^"]*)"', inner)
            if not title:
                continue
            pic = img.group(1) if img else ""
            out.append({
                "vod_id": vid_url,
                "vod_name": title.group(1).strip(),
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": "",
            })
        return out

    # ─────────────── TVBox 契约 ───────────────

    def homeContent(self, filter=False):
        return {"class": [{"type_id": "全部", "type_name": "全部"}]}

    def homeVideoContent(self):
        html = self._get(HOST + "/videos/")
        return {"list": self._parse_cards(html)}

    def categoryContent(self, tid, pg=1, filter=False, extend=None):
        page = int(pg)
        url = HOST + "/videos/" if page <= 1 else HOST + "/videos/%d/" % page
        html = self._get(url)
        return {"list": self._parse_cards(html)}

    def searchContent(self, key, quick=False, pg="1"):
        return {"list": []}

    def detailContent(self, ids):
        val = ids[0] if isinstance(ids, list) else ids
        url = HOST + val if val.startswith("/") else val
        html = self._get(url)
        m = re.search(r'data-src="([^"]*)"', html)
        if not m:
            return {"list": []}
        m3u8_src = m.group(1)
        title = re.search(r'<title>([^<]*)</title>', html)
        name = (title.group(1).replace(" · 糖心Vlog", "").strip()) if title else "糖心Vlog"
        return {
            "list": [{
                "vod_id": val,
                "vod_name": name,
                "vod_pic": self._proxy_pic(re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html).group(1) if re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html) else ""),
                "vod_play_from": "糖心",
                "vod_play_url": "正片$" + m3u8_src,
            }]
        }

    def playerContent(self, flag, id, vipFlags=None):
        try:
            val = str(id)
            if "$" in val:
                val = val.split("$")[-1]
            if ".m3u8" in val:
                url = self._proxy_url(val)
                header = json.dumps({"User-Agent": UA, "Referer": REFERER})
                return {"parse": 0, "url": url, "header": header}
            return {"parse": 0, "url": val, "header": json.dumps({"User-Agent": UA, "Referer": REFERER})}
        except Exception:
            return {"parse": 0, "url": str(id), "header": json.dumps({"User-Agent": UA, "Referer": REFERER})}

    def localProxy(self, param):
        try:
            if isinstance(param, dict):
                ptype = param.get("type", "")
                p_url = param.get("url", "")
            else:
                ptype = ""
                p_url = param or ""
            try:
                real = base64.b64decode(unquote(p_url)).decode("utf-8")
            except Exception:
                real = unquote(p_url) or p_url
            if not real:
                return [500, "text/plain", b"no url", {"Content-Length": "6"}]
            r = self.session.get(real, timeout=20)
            data = r.content
            ct = r.headers.get("Content-Type", "").split(";")[0] or "application/octet-stream"

            if not (".m3u8" in real or "mpegurl" in ct):
                if real.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')) or ct.startswith("image/"):
                    return [200, ct, data, {"Content-Length": str(len(data))}]

            # m3u8: key URI + 分片相对路径 -> 本机代理 (统一带 Referer)
            if ".m3u8" in real or "mpegurl" in ct:
                text = data.decode("utf-8", "ignore")
                base = real.rsplit("/", 1)[0] + "/"
                new_lines = []
                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        new_lines.append(line)
                        continue
                    km = re.match(r'#EXT-X-KEY:.*URI="([^"]+)"', line)
                    if km:
                        key_url = km.group(1)
                        if not key_url.startswith("http"):
                            key_url = base + key_url
                        new_key = self._proxy_url(key_url)
                        line = re.sub(r'URI="[^"]*"', 'URI="%s"' % new_key, line)
                        new_lines.append(line)
                        continue
                    if line.startswith("#"):
                        new_lines.append(line)
                        continue
                    seg_url = base + line if not line.startswith("http") else line
                    new_lines.append(self._proxy_url(seg_url))
                data = ("\n".join(new_lines)).encode("utf-8")
                ct = "application/vnd.apple.mpegurl"
            elif real.endswith(".ts"):
                ct = "video/mp2t"
            return [200, ct, data, {"Content-Length": str(len(data))}]
        except Exception as e:
            return [500, "text/plain", str(e).encode("utf-8"), {"Content-Length": str(len(str(e)))}]

    def isVideoFormat(self, url):
        return ".m3u8" in url or ".mp4" in url