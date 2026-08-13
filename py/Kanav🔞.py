# -*- coding: utf-8 -*-

import os
import re
import json
import time
import base64
import hmac
import hashlib
from urllib.parse import quote, unquote

try:
    from Crypto.Cipher import AES
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False

from base.spider import Spider as BaseSpider


APP_ID = "TSYH-003"
APP_SECRET = "8bba5b18911019d1b6f3492bb3b1227c7adb414d776b9c0692b374ddb87bee15"
VER = "1"
T2 = "A256GCM"
HOST = "https://kanav.com"
API = HOST  # 接口路径自带 /api, 已含在 path 中


class Spider(BaseSpider):
    def __init__(self):
        super().__init__()
        self._classes = None

    def getName(self):
        return "KanAV"

    def getDependence(self):
        return []

    def init(self, extend=""):
        self.extend = extend or ""

    # ───────── 解密 ─────────
    def _derive_key(self):
        return hmac.new(APP_SECRET.encode("utf-8"),
                        b"customer-enc-v1", hashlib.sha256).digest()[:32]

    def _decrypt(self, b64data, ts, ver):
        if not _HAS_CRYPTO:
            raise RuntimeError("pycryptodome 未安装, 无法解密")
        key = self._derive_key()
        raw = base64.b64decode(b64data)
        iv = raw[:12]
        tag = raw[-16:]
        ct = raw[12:-16]
        aad = f"{ver}:{ts}:{T2}".encode("utf-8")
        cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
        cipher.update(aad)
        pt = cipher.decrypt_and_verify(ct, tag)
        return json.loads(pt.decode("utf-8"))

    # ───────── 统一请求 ─────────
    def _req(self, path, params=None):
        """GET + query + appId, 最简 header。响应 data 为 str 时解密。"""
        p = {"appId": APP_ID}
        if params:
            p.update(params)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Referer": HOST + "/",
        }
        try:
            r = self.fetch(f"{API}{path}", params=p, headers=headers, timeout=20)
            if r is None:
                return None
            rt = r.headers.get("X-Enc-Ts") or str(int(time.time() * 1000))
            rv = r.headers.get("X-Enc-Ver") or VER
            j = r.json()
            if isinstance(j, dict) and isinstance(j.get("data"), str):
                return self._decrypt(j["data"], rt, rv)
            return j
        except Exception as e:
            self.log(f"[KanAV] 请求 {path} 失败: {e}")
            return None

    # ───────── 分类（两级：group 主导航，tag 子分类）─────────
    def _build_classes(self):
        if self._classes is not None:
            return self._classes
        groups = self._req("/api/tag/unique/list", {"page": 1, "pageSize": 200})
        classes = []
        filters = {}
        if isinstance(groups, list):
            for g in groups:
                if not isinstance(g, dict):
                    continue
                gname = (g.get("groupName") or "").strip()
                tags = g.get("tags") or []
                # group 作为主分类 type_id（用累加序号 + 名称，保证唯一）
                gid = "g_" + re.sub(r"\W+", "", gname) or f"g_{len(classes)}"
                if not gname:
                    continue
                classes.append({"type_id": gid, "type_name": gname})
                # 子分类 filters
                values = []
                for t in tags:
                    if not isinstance(t, dict):
                        continue
                    sid = str(t.get("tagSourceId") or "")
                    name = t.get("tagName") or sid
                    if sid:
                        values.append({"n": name, "v": sid})
                if values:
                    # 首项为空（全部）
                    values = [{"n": "全部", "v": ""}] + values
                    filters[gid] = [{
                        "key": "tagSourceId",
                        "name": gname,
                        "value": values,
                    }]
                    
        self._classes = classes
        self._filters = filters
        return self._classes

    # ───────── 首页 ─────────
    def homeContent(self, filter=False):
        classes = self._build_classes()
        d = self._req("/api/home/latest/list")
        items = self._parse_list(d)
        return {"list": items,"class": classes, "filters": getattr(self, "_filters", {})}

    def homeVideoContent(self):
        pass

    # ───────── 分类 ─────────
    def categoryContent(self, tid, pg, filter=False, extend={}):
        try:
            page = max(1, int(pg or "1"))
            params = {"page": page, "pageSize": 24}
            # 子分类筛选: extend 里的 tagSourceId (来自 filters)
            tag = (extend or {}).get("tagSourceId", "") if isinstance(extend, dict) else ""
            if tag:
                params["tagSourceId"] = str(tag)
            d = self._req("/api/video/list", params)
            items, total = self._parse_list_with_total(d)
            pagecount = (total + 23) // 24 if total else 99
            return {
                "list": items,
                "page": page,
                "pagecount": pagecount,
                "limit": 24,
                "total": total or len(items),
            }
        except Exception as e:
            self.log(f"[KanAV] 分类失败: {e}")
            return {"list": [], "page": int(pg or "1"), "pagecount": 0, "limit": 24, "total": 0}

    # ───────── 详情 ─────────
    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        result = {"list": []}
        for vid in ids:
            try:
                vid = str(vid).strip()
                if not vid.isdigit():
                    # 源返回的是数字 id; 若传入 sourceId 则先查一次列表拿到数字 id
                    vid = self._resolve_id(vid) or vid
                d = self._req("/api/video/detail", {"videoId": vid})
                info = d if isinstance(d, dict) else {}
                title = info.get("name") or info.get("title") or vid
                pic = self._pic(info.get("imgX") or info.get("imgY") or info.get("poster") or "")
                desc = info.get("description") or info.get("summary") or ""
                actor = info.get("actresses") or info.get("actor") or info.get("publisher") or ""
                if isinstance(actor, list):
                    actor = " ".join([a.get("name", "") if isinstance(a, dict) else str(a) for a in actor])
                # 播放地址
                play_urls = self._get_play_urls(vid)
                vod = {
                    "vod_id": vid,
                    "vod_name": str(title).strip(),
                    "vod_pic": pic,
                    "vod_content": str(desc).strip(),
                    "vod_actor": str(actor).strip(),
                    "vod_area": info.get("area") or "",
                    "vod_year": "",
                    "vod_remarks": self._dur(info.get("duration")),
                    "vod_play_from": "KanAV",
                    "vod_play_url": "#".join(play_urls) if play_urls else "",
                }
                result["list"].append(vod)
            except Exception as e:
                self.log(f"[KanAV] 详情失败 {vid}: {e}")
        return result

    def _resolve_id(self, source_id):
        """sourceId 字符串 -> 数字 id (通过列表接口反查)"""
        try:
            d = self._req("/api/video/list", {"page": 1, "pageSize": 24})
            lst = self._extract_list(d)
            for it in lst:
                if isinstance(it, dict) and str(it.get("sourceId")) == source_id:
                    return str(it.get("id"))
        except Exception:
            pass
        return None

    def _get_play_urls(self, vid):
        """play/source -> 拼接每路清晰度的 m3u8 直链"""
        out = []
        try:
            arr = self._req("/api/play/source", {"videoId": vid})
            if not isinstance(arr, list):
                return out
            for item in arr:
                if not isinstance(item, dict):
                    continue
                url = item.get("url") or item.get("m3c_url") or item.get("m3v_url") or ""
                if not url:
                    continue
                if url.startswith("/"):
                    url = HOST + url
                line = item.get("line") or item.get("quality") or str(len(out) + 1)
                out.append(f"{line}${url}")
        except Exception:
            pass
        return out

    # ───────── 搜索 ─────────
    def searchContent(self, key, quick=False, pg="1"):
        try:
            page = max(1, int(pg or "1"))
            d = self._req("/api/search/result",
                          {"keyword": key, "page": page, "pageSize": 24, "sort": "relevance"})
            items = self._parse_list(d, key="videos")
            return {"list": items, "page": page}
        except Exception as e:
            self.log(f"[KanAV] 搜索失败: {e}")
            return {"list": [], "page": int(pg or "1")}

    # ───────── 播放 ─────────
    def playerContent(self, flag, id, vipFlags=""):
        if not id:
            return {"parse": 1, "url": ""}
        if ".m3u8" in id.lower() or ".mp4" in id.lower():
            return {
                "parse": 0,
                "url": id,
                "header": json.dumps({"User-Agent": "Mozilla/5.0", "Referer": HOST + "/"}),
            }
        return {"parse": 1, "url": id, "header": json.dumps({"Referer": HOST + "/"})}

    # ───────── 解析工具 ─────────
    def _pic(self, url):
        """封面图转换: 接口给的 imgX 是失效的 cdn.g3ejjm8m.com/.jpg ,
        前端实际加载的是 ycuakooepej.cyou 的 .bnc 资源(已实测 200)。
        规则: 域名 m3f 段换 cyou CDN, 后缀 jpg/jpeg/png/webp 改 bnc。
        .bnc 为 AES-128-ECB(密钥 imageKey) 加密的 JPEG, TVBox 无法直接显示,
        故包成本地代理 URL, 由 localProxy 实时下载并解密后返回图片字节。"""
        if not url:
            return ""
        if url.startswith("//"):
            url = "https:" + url
        u = url.replace("https://cdn.g3ejjm8m.com/m3f/",
                        "https://ycuakooepej.cyou/")
        # jpg/jpeg/png/webp 统一改为 .bnc (实测所有后缀改 bnc 均可 200)
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            if u.endswith(ext):
                u = u[: -len(ext)] + ".bnc"
                break
        if u.endswith(".bnc"):
            return self.getProxyUrl() + "&type=pgg_img&url=" + quote(u, safe="")
        return u

    @staticmethod
    def _dur(sec):
        try:
            sec = int(sec)
            if sec <= 0:
                return ""
            h = sec // 3600
            m = (sec % 3600) // 60
            if h:
                return f"{h}时{m}分"
            return f"{m}分"
        except Exception:
            return ""

    def _extract_list(self, d):
        """从响应中提取视频列表数组"""
        if not d:
            return []
        # 加密接口: {"list":[...]}
        if isinstance(d, dict):
            for k in ("list", "videos", "items", "records"):
                v = d.get(k)
                if isinstance(v, dict):
                    inner = v.get("list") or v.get("records") or []
                    if isinstance(inner, list):
                        return inner
                elif isinstance(v, list):
                    return v
            # search/result: {"videos":{"list":[...]}}
            vids = d.get("videos")
            if isinstance(vids, dict) and isinstance(vids.get("list"), list):
                return vids["list"]
        return []

    def _parse_list(self, d, key=None):
        items = []
        lst = self._extract_list(d)
        if key:
            # 指定顶层 key 再提取 (search 用 videos)
            if isinstance(d, dict):
                sub = d.get(key)
                if isinstance(sub, dict):
                    lst = sub.get("list") or []
                elif isinstance(sub, list):
                    lst = sub
        seen = set()
        for it in lst:
            if not isinstance(it, dict):
                continue
            vid = str(it.get("id") or it.get("videoId") or it.get("sourceId") or "")
            if not vid or vid in seen:
                continue
            seen.add(vid)
            title = it.get("name") or it.get("title") or it.get("videoName") or ""
            pic = self._pic(it.get("imgX") or it.get("imgY") or it.get("cover") or it.get("poster") or "")
            items.append({
                "vod_id": vid,
                "vod_name": str(title).strip(),
                "vod_pic": pic,
                "vod_remarks": self._dur(it.get("duration")),
            })
        return items

    def _parse_list_with_total(self, d):
        items = self._parse_list(d)
        total = 0
        if isinstance(d, dict):
            data = d.get("data") if isinstance(d.get("data"), dict) else d
            if isinstance(data, dict):
                total = data.get("total") or data.get("totalCount") or 0
        return items, int(total) if total else 0

    # ───────── 图片代理 ─────────
    # kanav 封面为 .bnc 加密图片, 前端用 AES-128-ECB(密钥 imageKey) 解密后显示。
    # TVBox 无法解密, 故由 localProxy 在本地实时下载并解密返回图片字节。
    IMAGE_KEY = b"525202f9149e061d"  # 前端 imageKey (16字节 = AES-128)

    def _decrypt_bnc(self, raw):
        """AES-128-ECB(PKCS7) 解密 .bnc 字节 -> JPEG 字节。无 crypto 时原样返回。"""
        if not _HAS_CRYPTO or len(raw) == 0 or len(raw) % 16 != 0:
            return raw
        try:
            from Crypto.Util.Padding import unpad
            cipher = AES.new(self.IMAGE_KEY, AES.MODE_ECB)
            dec = cipher.decrypt(raw)
            try:
                dec = unpad(dec, 16)
            except Exception:
                pass
            return dec
        except Exception:
            return raw

    def localProxy(self, params):
        try:
            if params.get("type") != "pgg_img":
                return [404, "text/plain", "not found"]

            img_url = unquote(params.get("url", ""))
            if not img_url:
                return [400, "text/plain", "missing url"]

            is_bnc = img_url.endswith(".bnc")
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Referer": HOST + "/",
            }
            r = self.fetch(img_url, headers=headers, timeout=20)
            if r is None or getattr(r, "status_code", 0) != 200:
                return [404, "text/plain", "image not found"]

            data = r.content
            if is_bnc:
                data = self._decrypt_bnc(data)

            if data[:2] == b"\xff\xd8":
                return [200, "image/jpeg", data, {"Content-Length": str(len(data))}]
            elif data[:4] == b"\x89PNG":
                return [200, "image/png", data, {"Content-Length": str(len(data))}]
            elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
                return [200, "image/webp", data, {"Content-Length": str(len(data))}]
            else:
                mime = r.headers.get("Content-Type", "image/jpeg")
                if mime.startswith("image/"):
                    return [200, mime, data, {"Content-Length": str(len(data))}]
                return [404, "text/plain", "invalid image format"]
        except Exception:
            return [500, "text/plain", "proxy error"]
