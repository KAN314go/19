import base64
import hashlib
import json
import time
import urllib.parse
import zlib

import requests

from base.spider import Spider as BaseSpider


FILM_FILTERS = {"3": "国产", "2": "日本", "1": "欧美", "4": "直播"}
FILM_ORDER = ("3", "2", "1", "4")
ONE_API = "https://api.em1oifd0.com/"
BOOTSTRAP_LINES = ("http://198.44.248.101:9672/", "http://198.44.248.102:9672/", "http://122.10.20.249:9672/")
BOX_KEY = b"dnf45as45fs1ace1"
BOX_IV = b"dn5as4fs1ac5f4e1"
ONE_KEY = b"l*bv%Ziq000Biaog"
ONE_IV = b"8597506002939249"
ONE_SIGN_SUFFIX = "m4n2hjPeYWkD6tFpqKF^3HO^h24P@idT"
ONE_IMAGE_KEY = b"saIZXc4yMvq0Iz56"
ONE_IMAGE_IV = b"kbJYtBJUECT0oyjo"
REQUEST_TIMEOUT = 15


def _pad(data):
    length = 16 - (len(data) % 16)
    return data + bytes([length]) * length


def _unpad(data):
    if not data:
        return data
    length = data[-1]
    if length < 1 or length > 16 or data[-length:] != bytes([length]) * length:
        raise ValueError("invalid cipher padding")
    return data[:-length]


def _aes(data, key, iv, decrypt=False):
    try:
        from Crypto.Cipher import AES
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return cipher.decrypt(data) if decrypt else cipher.encrypt(_pad(data))
    except ImportError:
        import subprocess
        command = ["openssl", "enc", "-aes-128-cbc"]
        if decrypt:
            command.append("-d")
        command.extend(["-nopad", "-K", key.hex(), "-iv", iv.hex()])
        source = data if decrypt else _pad(data)
        process = subprocess.run(command, input=source, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return process.stdout


def _decrypt_one_image(data):
    return _unpad(_aes(data, ONE_IMAGE_KEY, ONE_IMAGE_IV, decrypt=True))


def _image_kind(data):
    if data.startswith(b"\xff\xd8\xff") and data.endswith(b"\xff\xd9"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n") and data.endswith(b"IEND\xaeB`\x82"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")) and data.endswith(b";"):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP" and len(data) >= 12 and int.from_bytes(data[4:8], "little") == len(data) - 8:
        return "image/webp"
    return None


def _choose_media(item):
    if not isinstance(item, dict):
        return None
    for field in ("video_hls", "video_hls_h265", "video_file", "video"):
        value = item.get(field)
        if isinstance(value, str) and value and not Spider._is_audio_path(value) and not any(word in field.lower() for word in ("preview", "trailer", "sample")):
            return field, value
    return None


def _diagnostic(message, detail=None):
    safe = str(message).replace("\n", " ")[:180]
    if detail:
        safe += ": " + str(detail).replace("\n", " ")[:180]
    return {"error": safe}


class Spider(BaseSpider):
    def __init__(self):
        super().__init__()
        self._ready = False
        self._config = None
        self._token = None
        self._hosts = {}
        self._pagination = {}
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "Dart/3.4 (dart:io)"})

    def init(self, extend=""):
        self.extend = extend or ""
        self._ready = False

    def _ensure_ready(self):
        if self._ready:
            return None
        try:
            self._bootstrap()
            self._ready = True
            return None
        except Exception as error:
            return _diagnostic("初始化失败", type(error).__name__)

    def _bootstrap(self):
        last = None
        for line in BOOTSTRAP_LINES:
            try:
                response = self._session.post(line + "box/api/config", params={"channel": "Channel"}, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
                config = self._decode_box(response.content)
                if not isinstance(config.get("data"), dict):
                    raise ValueError("invalid config shape")
                self._config = config
                self._token = next(item["token"] for item in config["data"].get("token", []) if item.get("name") == "token_one")
                self._hosts = {item.get("name"): item.get("host", "") for item in config["data"].get("api", [])}
                return
            except Exception as error:
                last = error
        raise RuntimeError(type(last).__name__ if last else "bootstrap unavailable")

    @staticmethod
    def _decode_box(body):
        raw = _unpad(_aes(body, BOX_KEY, BOX_IV, decrypt=True))
        return json.loads(zlib.decompress(raw).decode("utf-8"))

    def _one_headers(self):
        timestamp = str(int(time.time()))
        uuid = getattr(self, "_uuid", None) or "48b067ec-6cfd-3491-84f5-023eb1e7d562"
        user_key = getattr(self, "_user_key", None) or "563e8eeef42931cc858dc0d1080f4f6f"
        platform = "3"
        ip = "0.0.0.0"
        first = hashlib.md5(".".join((ip, platform, timestamp, user_key, uuid)).encode()).hexdigest()
        sign = hashlib.md5((first + ONE_SIGN_SUFFIX).encode()).hexdigest()
        return {"ip": ip, "uuid": uuid, "timestamp": timestamp, "platform": platform, "token": self._token, "sign": sign, "user-key": user_key, "app-version": "2.6.3.1", "Content-Type": "application/x-www-form-urlencoded"}

    def _request(self, endpoint, params):
        query = "&".join("{}={}".format(key, params[key]) for key in sorted(params))
        encoded = base64.b64encode(_aes(query.encode(), ONE_KEY, ONE_IV)).decode()
        response = self._session.post(self._hosts.get("one", ONE_API).rstrip("/") + "/" + endpoint.lstrip("/"), data=encoded, headers=self._one_headers(), timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        decoded = _aes(base64.b64decode(response.text.strip()), ONE_KEY, ONE_IV, decrypt=True)
        return json.loads(_unpad(decoded).decode("utf-8"))

    def _one_url(self, name, path):
        prefix = self._hosts.get(name, "")
        if not prefix:
            return ""
        return urllib.parse.urljoin(prefix, path.lstrip("/"))

    def _proxy_url(self, url):
        return self.getProxyUrl() + "&url=" + urllib.parse.quote(url, safe="")

    @staticmethod
    def _is_audio_path(path):
        return isinstance(path, str) and path.lower().split("?", 1)[0].endswith((".mp3", ".m4a", ".aac", ".wav", ".flac"))

    def _item(self, item):
        media = _choose_media(item)
        cover = item.get("thumb") or item.get("thumbnail") or ""
        if cover and not cover.startswith(("http://", "https://")):
            cover = self._one_url("one_img", cover)
        if cover:
            cover = self._proxy_url(cover)
        playable = media and not self._is_audio_path(media[1])
        return {"vod_id": str(item.get("id", "")), "vod_name": item.get("title", ""), "vod_pic": cover, "vod_remarks": item.get("video_length", ""), "vod_year": str(item.get("published_at", ""))[:4], "vod_content": item.get("description", ""), "vod_play_from": "One" if playable else "", "vod_play_url": "正片$" + str(item.get("id")) if playable else ""}

    def homeContent(self, filter):
        error = self._ensure_ready()
        if error:
            return error
        classes = [{"type_id": key, "type_name": FILM_FILTERS[key]} for key in FILM_ORDER]
        return {"class": classes, "filters": {}, "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        error = self._ensure_ready()
        if error:
            return error
        demand_tag_id = str(tid)
        if demand_tag_id not in FILM_FILTERS:
            demand_tag_id = FILM_ORDER[0]
        page = max(1, int(pg))
        params = {"demand_tag_id": int(demand_tag_id), "model_id": 6, "page": page, "published_at": time.strftime("%Y-%m"), "size": 20, "sort": "published_at"}
        try:
            result = self._request("v2.5/article/discovery", params)
            items = result.get("data", []) if isinstance(result, dict) else []
            seen = set()
            rows = []
            for item in items:
                identity = item.get("id")
                if identity in seen:
                    continue
                seen.add(identity)
                rows.append(self._item(item))
            state = self._pagination.setdefault(demand_tag_id, {})
            state[page] = len(rows)
            if len(rows) == 20 and page + 1 not in state:
                lookahead_params = dict(params)
                lookahead_params["page"] = page + 1
                lookahead = self._request("v2.5/article/discovery", lookahead_params)
                state[page + 1] = len(lookahead.get("data", [])) if isinstance(lookahead, dict) else 0
            terminal = min((number for number, count in state.items() if count < 20), default=page + 1)
            page_count = terminal
            total = sum(state.get(number, 20) for number in range(1, terminal + 1))
            return {"page": page, "pagecount": page_count, "limit": 20, "total": total, "list": rows}
        except Exception as error:
            return _diagnostic("分类请求失败", type(error).__name__)

    def detailContent(self, ids):
        error = self._ensure_ready()
        if error:
            return error
        try:
            item_id = int(ids[0] if isinstance(ids, (list, tuple)) else ids)
            result = self._request("v2.5/article/detail", {"id": item_id})
            item = result.get("data", {})
            media = _choose_media(item)
            play_entries = [("正片", item_id)] if media else []
            series_id = item.get("series_id")
            if series_id and media:
                chapters = self._request("v2.5/series/chapters", {"series_id": int(series_id)}).get("data", {}).get("chapters", [])
                play_entries = [(chapter.get("title") or "第{}集".format(chapter.get("chapter", "")), chapter.get("id")) for chapter in chapters if chapter.get("id")]
            play_url = "#".join("{}${}".format(title.replace("#", " ").replace("$", " "), chapter_id) for title, chapter_id in play_entries)
            detail = self._item(item)
            detail.update({"vod_id": str(item_id), "vod_play_from": "One" if play_entries else "", "vod_play_url": play_url})
            return {"list": [detail]}
        except Exception as error:
            return _diagnostic("详情请求失败", type(error).__name__)

    def searchContent(self, key, quick, pg="1"):
        return {"list": [], "page": int(pg), "pagecount": 1, "limit": 0, "total": 0, "error": "第一分类未证实搜索语义，安全返回空结果"}

    def playerContent(self, flag, id, vipFlags):
        error = self._ensure_ready()
        if error:
            return error
        try:
            item_id = int(str(id).split("$")[-1])
            result = self._request("v2.5/article/detail", {"id": item_id})
            item = result.get("data", {})
            media = _choose_media(item)
            if not media:
                return {"parse": 0, "playUrl": "", "url": "", "header": {}, "error": "无已证实正片源，未将试看或预览标为正片"}
            field, path = media
            if field.startswith("video_hls"):
                url = self._one_url("one_video", path)
                return {"parse": 0, "playUrl": "", "url": url, "header": {"User-Agent": "Dart/3.4 (dart:io)"}, "media_field": field}
            return {"parse": 0, "playUrl": "", "url": self._one_url("one_video", path), "header": {"User-Agent": "Dart/3.4 (dart:io)"}, "media_field": field}
        except Exception as error:
            return _diagnostic("播放请求失败", type(error).__name__)

    def localProxy(self, param):
        if not isinstance(param, dict):
            return [400, "text/plain", b"invalid proxy parameters"]
        url = param.get("url", "")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return [400, "text/plain", b"invalid proxy URL"]
        try:
            parsed = urllib.parse.urlparse(url)
            configured = urllib.parse.urlparse(self._hosts.get("one_img", ""))
            if not configured.hostname or parsed.hostname != configured.hostname or parsed.netloc.lower() != configured.netloc.lower():
                return [403, "text/plain", b"proxy host is not allowed"]
            if parsed.query or parsed.fragment or parsed.username or parsed.password:
                return [400, "text/plain", b"proxy query is not allowed"]
            response = self._session.get(url, headers={"User-Agent": "Dart/3.4 (dart:io)"}, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            content = _decrypt_one_image(response.content)
            content_type = _image_kind(content)
            if not content_type:
                return [502, "text/plain", b"proxy image integrity check failed"]
            return [200, content_type, content]
        except Exception as error:
            return [502, "text/plain", ("proxy error: " + type(error).__name__).encode()]
