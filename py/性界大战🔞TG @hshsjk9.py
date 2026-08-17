# -*- coding: utf-8 -*-
"""xjdzz3.sbs Spider - compatible with WebHomeTV / OK影视 / PickTV."""
import json
import re
import ssl
import time
try:
    from threading import Lock
except Exception:
    Lock = None
from urllib.parse import quote, unquote, urljoin, urlparse, parse_qs
try:
    from urllib.request import Request, build_opener, HTTPSHandler
except Exception:
    Request = None


class Spider:
    host = "https://e_pf_i.xjdzz3.sbs"
    name = "性界大战"
    ua = "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36"
    referer = host + "/"
    cats = [
        ("免费在线", "117"), ("女优系列", "121"), ("港台甜妹", "122"),
        ("韩国女团", "123"), ("国产探花", "124"), ("剧情演绎", "125"),
        ("网红流出", "126"), ("自拍偷拍", "127"), ("色情动漫", "128"),
        ("最新最热", "118"), ("性感丝袜", "129"), ("群P淫乱", "130"),
        ("极品学妹", "131"), ("国产传媒", "132"), ("中文字幕", "133"),
        ("绿帽淫妻", "134"), ("网曝泄密", "135"), ("户外露出", "136"),
        ("深夜福利", "119"), ("国产精品", "137"), ("主播大秀", "138"),
        ("女王调教", "139"), ("欺辱凌辱", "140"), ("恋足恋腿", "141"),
        ("口交深喉", "142"), ("素人自拍", "143"), ("Cosplay", "144"),
        ("必看撸片", "120"), ("强奸乱伦", "145"), ("日本精品", "146"),
        ("瑜伽牛仔", "147"), ("色情护士", "148"), ("女同磨B", "149"),
        ("萝莉少女", "150"), ("欧美洋妞", "151"), ("亚洲无码", "152"),
    ]

    def __init__(self):
        self.s = None
        self.session = None
        self.sess = None
        self._ctx = ssl._create_unverified_context()
        self._pic_cache = {}
        self._pic_lock = Lock() if Lock else None

    def getDependence(self):
        return []

    def init(self, extend=""):
        if isinstance(extend, str) and extend.strip():
            try:
                x = json.loads(extend)
                if isinstance(x, dict) and x.get("host"):
                    self.host = str(x["host"]).rstrip("/")
            except Exception:
                if extend.startswith("http"):
                    self.host = extend.rstrip("/")
        self.referer = self.host + "/"
        return None

    def homeVideoContent(self):
        return self._home()

    def homeContent(self, filter=None):
        return self._home()

    def _home(self):
        # 首页是静态推荐页；取页面中的第一批条目，避免详情模板故障影响首页。
        html = self._get(self.host + "/")
        return {"class": [{"type_id": tid, "type_name": name} for name, tid in self.cats],
                "list": self._parse_list(html)[:24], "parse": 0}

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        try:
            page = int(str(pg))
        except Exception:
            page = 1
        page = max(1, page)
        url = self.host + "/vodtype/%s%s.html" % (str(tid), ("-%d" % page if page > 1 else ""))
        html = self._get(url)
        items = self._parse_list(html)
        return {"page": page, "pagecount": 9999, "limit": 20, "total": 999999,
                "list": items, "parse": 0}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            page = int(str(pg))
        except Exception:
            page = 1
        suffix = "" if page <= 1 else "-%d" % page
        url = self.host + "/vodsearch/" + quote(str(key), safe="") + "-------------%s.html" % suffix
        html = self._get(url)
        return {"page": page, "pagecount": 9999, "list": self._parse_list(html), "parse": 0}

    def detailContent(self, ids):
        vid = self._id(ids)
        html = self._get(self.host + "/vodplay/%s-1-1.html" % vid)
        data = self._play_data(html, vid)
        if not data:
            data = {"vod_id": vid, "vod_name": "视频" + vid, "vod_pic": ""}
        data["vod_play_from"] = "slm3u8"
        data["vod_play_url"] = "在线播放$%s-1-1" % vid
        return {"list": [data], "parse": 0}

    def playerContent(self, flag, ids, vipFlags=None):
        vid = str(ids).split("-")[0]
        html = self._get(self.host + "/vodplay/%s-1-1.html" % vid)
        m = re.search(r'(["\'])url\1\s*:\s*(["\'])(https?[^"\']+?\.m3u8)', html, re.I)
        if not m:
            m = re.search(r'(["\'])url\1\s*:\s*(["\'])(https?[^"\']+)', html, re.I)
        url = m.group(3).replace("\\/", "/") if m else ""
        return {"parse": 0, "jx": 0, "url": url,
                "header": {"User-Agent": self.ua, "Referer": self.referer},
                "format": "application/x-mpegURL"}

    def localProxy(self, param):
        if isinstance(param, str):
            try:
                param = json.loads(param)
            except Exception:
                param = {}
        param = param or {}
        raw = param.get("url", "")
        if not raw:
            return [404, "text/plain", b"", {}]
        # 同一图片短时间内重复请求时直接复用 bytes，避免 CDN 偶发空响应。
        try:
            if self._pic_lock:
                self._pic_lock.acquire()
            hit = self._pic_cache.get(raw)
            if hit and time.time() - hit[0] < 300:
                return [200, hit[1], hit[2], {"Cache-Control": "max-age=300"}]
        finally:
            if self._pic_lock:
                self._pic_lock.release()
        last = None
        for _ in range(3):
            try:
                req = Request(raw, headers={"User-Agent": self.ua, "Referer": self.referer,
                                            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                                            "Connection": "close"})
                op = build_opener(HTTPSHandler(context=self._ctx))
                with op.open(req, timeout=25) as r:
                    body = r.read()
                    mime = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
                if len(body) < 100 or (body[:2] != b"\xff\xd8" and not body.startswith((b"\x89PNG", b"RIFF", b"GIF"))):
                    raise ValueError("invalid image body")
                if not mime.startswith("image/"):
                    mime = "image/jpeg"
                self._pic_cache[raw] = (time.time(), mime, body)
                return [200, mime, body, {"Cache-Control": "max-age=300"}]
            except Exception as e:
                last = e
                time.sleep(0.15)
        return [502, "image/jpeg", b"", {}]

    def _pic(self, url):
        if not url:
            return ""
        # 通过标准 TVBox 本地代理统一处理跨域、Referer 和 CDN 图片。
        try:
            from com.github.catvod import Proxy
            port = Proxy.getPort()
            return "http://127.0.0.1:%s/proxy?do=py&url=%s" % (port, quote(url, safe=""))
        except Exception:
            return "proxy://?do=py&url=%s" % quote(url, safe="")

    def manualVideoCheck(self):
        return False

    def isVideoFormat(self, url):
        return ".m3u8" in str(url).lower() or ".mp4" in str(url).lower()

    def action(self, action):
        return ""

    def destroy(self):
        return None

    def _get(self, url):
        req = Request(url, headers={"User-Agent": self.ua, "Referer": self.referer,
                                    "Accept": "text/html,application/xhtml+xml"})
        op = build_opener(HTTPSHandler(context=self._ctx))
        with op.open(req, timeout=20) as r:
            return r.read().decode("utf-8", "ignore")

    def _parse_list(self, html):
        out, seen = [], set()
        # 先按播放链接定位条目，再在后续片段中提取封面和标题。
        for z in re.finditer(r'/vodplay/(\d+-\d+-\d+)\.html', html, re.I):
            eid = z.group(1)
            vid = eid.split("-")[0]
            if vid in seen:
                continue
            block = html[z.start():z.start() + 1200]
            im = re.search(r'<img[^>]+src=["\']([^"\']+)', block, re.I)
            nm = re.search(r'<img[^>]+alt=["\']([^"\']*)', block, re.I)
            if not nm:
                nm = re.search(r'<h5[^>]*>\s*<a[^>]*>(.*?)</a>', block, re.S | re.I)
            seen.add(vid)
            out.append({"vod_id": vid, "vod_name": (re.sub(r'<[^>]+>', '', nm.group(1)).strip() if nm else "视频" + vid),
                        "vod_pic": self._pic(urljoin(self.host + "/", im.group(1))) if im else "", "vod_remarks": ""})
        return out

    def _play_data(self, html, vid):
        # 页面内 player_aaaa 对象是 JSON 风格，字段内容经 JS unicode 转义。
        m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*</script>', html, re.S)
        if not m:
            return None
        raw = m.group(1).replace("\\/", "/")
        try:
            x = json.loads(raw)
            v = x.get("vod_data") or {}
            return {"vod_id": str(v.get("vod_id") or vid),
                    "vod_name": v.get("vod_name") or ("视频" + vid),
                    "vod_pic": self._pic(urljoin(self.host + "/", v.get("vod_pic", ""))),
                    "vod_year": str(v.get("vod_year") or ""),
                    "vod_area": v.get("vod_area") or "", "vod_actor": v.get("vod_actor") or "",
                    "vod_director": v.get("vod_director") or "", "vod_content": v.get("vod_content") or ""}
        except Exception:
            return None

    @staticmethod
    def _id(ids):
        if isinstance(ids, (list, tuple)):
            ids = ids[0] if ids else ""
        return str(ids).strip().split("-")[0]
