# -*- coding: utf-8 -*-
# @Site: https://avday.app
# @Desc: AVDAY HTML source for TVBox / HKL (dr_py)
# @Note: adult site; age cookie avAgree=1 required.
#        Long videos can play via direct /video/{long|short}/{id}.m3u8.
#        Short / exclusive pages need login.
#        Credentials are embedded in this script; ext/auth file can still override.
from base.spider import Spider
import html as html_lib
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import quote, urljoin


class Spider(Spider):
    name = "AVDAY"
    host = "https://avday.app"
    base_url = host
    site_url = host
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
    page_size = 36
    # site login (short/exclusive)
    login_email = '普通账号'
    login_password = '密码'

    # free/public-friendly categories first; short may be empty without login
    class_name = ["長片最新", "長片無碼", "長片熱門", "獨家限定", "短片最新"]
    class_url = ["c1", "c3", "c4", "c5", "c2"]

    type_url_map = {
        "c1": "/list/long",
        "c2": "/list/short",
        "c3": "/long/uncensored",
        "c4": "/rank/long",
        "c5": "/exclusive/new",
    }

    long_tags = [
        "中文字幕", "無碼", "偷拍", "搭訕・約炮", "淫亂・重口味", "NTR", "百合", "女性向",
        "痴漢", "CCR", "偷情", "亂倫", "調教", "出汗", "主觀視角", "寫真影片",
        "攝像紀錄", "局部特寫", "特殊癖好", "粉絲感謝祭", "男同志", "歐美",
        "校園", "旅行", "洗澡", "浴室", "温泉", "車震", "野外・露出", "醫院・診所",
        "泳衣", "內衣", "絲襪", "激凸", "制服", "清涼穿著", "和服・浴衣", "情趣內褲",
        "裙底風光", "女僕", "體育服", "迷你裙", "眼鏡",
        "人妻", "熟女", "素人", "母", "蘿莉", "御姐", "孕婦", "寡婦", "痴女", "姐妹",
        "青梅竹馬", "護士", "上司", "學生", "老師", "空姐", "OL", "風俗娘", "角色扮演",
        "巨乳", "美乳", "貧乳・微乳", "美尻", "足控", "苗條身材", "肉感的",
        "身材高䠷", "嬌小系", "無毛", "動畫", "按摩",
    ]

    short_tags = [
        "直播主", "正妹", "素人", "情侶", "女優", "人妻", "熟女", "御姐", "蘿莉", "OL",
        "女友", "模特", "學生", "老師", "空姐", "上司", "護士", "角色扮演", "明星臉",
        "日本", "台灣", "本土", "歐美", "韓國", "亞洲", "香港", "泰國", "東南亞",
        "新加坡", "越南", "俄羅斯", "烏克蘭", "CCR",
        "偷拍", "自拍", "流出", "AI換臉", "AI破壞版", "FC2", "主觀視角", "局部特寫",
        "搭訕・約炮", "倫理", "偷情", "電影", "男同志", "百合", "女性向",
        "絲襪", "制服", "學生服", "內衣", "情趣內褲", "清涼穿著", "高跟鞋", "女僕",
        "泳衣", "睡衣", "眼鏡", "旅館", "洗澡", "車震", "浴室",
        "校園", "辦公室", "廁所", "野外・露出",
    ]

    def init(self, extend=""):
        self.extend = extend or ""
        self._cookie = "AVDAYRef=main; avAgree=1"
        self._auth = {}
        self._load_auth(self.extend)
        self._load_cookie_cache()
        # proactive login so short/exclusive groups have session immediately
        try:
            self._ensure_login(force=False)
        except Exception as exc:
            print("[AVDAY] init login error:", type(exc).__name__)
        return None

    def getName(self):
        return self.name

    def homeLayout(self):
        return {"typeListWidth": 2}

    def getHomeContent(self, filter=False):
        return self.homeContent(filter)

    def setExtendInfo(self, extend):
        self.extend = extend or ""
        self._load_auth(self.extend)

    def _base_dir(self):
        try:
            return os.path.dirname(os.path.abspath(__file__))
        except Exception:
            return os.getcwd()

    def _auth_paths(self):
        # only read auth file next to this source file
        return [os.path.join(self._base_dir(), "avday_auth.json")]


    def _load_auth(self, extend=""):
        # priority: extend JSON / auth file override > script constants
        auth = {}
        text = str(extend or getattr(self, "extend", "") or "").strip()
        if text.startswith("{"):
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    auth = data
            except Exception:
                auth = {}
        if not auth:
            for path in self._auth_paths():
                try:
                    if path and os.path.isfile(path):
                        data = json.loads(Path(path).read_text(encoding="utf-8"))
                        if isinstance(data, dict) and (data.get("email") or data.get("user") or data.get("username")):
                            auth = data
                            break
                except Exception as exc:
                    print("[AVDAY] auth file error:", type(exc).__name__)
        email = str(
            auth.get("email")
            or auth.get("user")
            or auth.get("username")
            or getattr(self, "login_email", "")
            or ""
        ).strip()
        password = str(
            auth.get("password")
            or auth.get("pass")
            or auth.get("pwd")
            or getattr(self, "login_password", "")
            or ""
        ).strip()
        self._auth = {"email": email, "password": password}
        return self._auth

    def _cookie_path(self):
        # cookie cache is stored next to this source file
        return os.path.join(self._base_dir(), "avday_cookie.txt")

    def _load_cookie_cache(self):
        path = self._cookie_path()
        try:
            if os.path.isfile(path) and (time.time() - os.path.getmtime(path) < 6 * 3600):
                raw = Path(path).read_text(encoding="utf-8").strip()
                if raw and "AVDAY_AUTH=" in raw:
                    self._cookie = raw
                    return True
        except Exception as exc:
            print("[AVDAY] cookie cache error:", type(exc).__name__)
        return False

    def _save_cookie_cache(self, cookie):
        path = self._cookie_path()
        try:
            parent = os.path.dirname(path)
            if parent and not os.path.isdir(parent):
                os.makedirs(parent, exist_ok=True)
            tmp = path + ".tmp"
            Path(tmp).write_text(str(cookie or ""), encoding="utf-8")
            os.replace(tmp, path)
            try:
                os.chmod(path, 0o666)
            except Exception:
                pass
        except Exception as exc:
            print("[AVDAY] cookie save error:", type(exc).__name__)

    def _clear_cookie_cache(self):
        path = self._cookie_path()
        try:
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass
        self._cookie = "AVDAYRef=main; avAgree=1"

    def _cookie_from_headers(self, header_text, names=None):
        found = {}
        text = header_text or ""
        # PHP style: match raw Set-Cookie lines, keep full NAME=value
        for m in re.finditer(r"(?im)^set-cookie:\s*([^=\r\n;]+)=([^;\r\n]*)", text):
            name = m.group(1).strip()
            value = m.group(2).strip()
            if names and name not in names:
                continue
            found[name] = value
        # also accept plain cookie header dumps
        if not found:
            for name in (names or ["AVDAY_AUTH", "XSRF-TOKEN", "avday_session", "avAgree", "AVDAYRef"]):
                m = re.search(r"(?:^|[;\s])" + re.escape(name) + r"=([^;\r\n\s]+)", text)
                if m:
                    found[name] = m.group(1).strip()
        return found

    def _merge_cookie(self, *parts):
        jar = {}
        for extra in parts:
            if not extra:
                continue
            if isinstance(extra, dict):
                for k, v in extra.items():
                    if k and v is not None and str(v) != "":
                        jar[str(k)] = str(v)
                continue
            for part in str(extra).split(";"):
                part = part.strip()
                if not part or "=" not in part:
                    continue
                k, v = part.split("=", 1)
                k = k.strip()
                v = v.strip()
                if k:
                    jar[k] = v
        order = ["AVDAYRef", "avAgree", "AVDAY_AUTH", "XSRF-TOKEN", "avday_session"]
        items = []
        for k in order:
            if k in jar and jar[k] != "":
                items.append(k + "=" + jar[k])
        for k, v in jar.items():
            if k not in order and v != "":
                items.append(k + "=" + v)
        return "; ".join(items)

    def _parse_header_body(self, raw):
        raw = raw or ""
        if not raw:
            return "", ""
        # split on first blank line
        parts = re.split(r"\r?\n\r?\n", raw, maxsplit=1)
        if len(parts) == 1:
            return "", parts[0]
        return parts[0], parts[1]

    def _http(self, method, url, headers=None, data=None, allow_redirects=True, raw_response=False):
        """Return dict: status/body/header/url/cookies. Prefer shell fetch, then urllib, then requests."""
        target = self._abs(url)
        headers = dict(headers or {})
        method_u = (method or "GET").upper()
        body = ""
        header_text = ""
        status = 0
        final_url = target
        jar = {}

        # Keep one session across login POST and protected list GET.
        # Short videos are returned only when the server sees the same session.
        try:
            import requests
            if not getattr(self, "_session", None):
                self._session = requests.Session()
                self._session.trust_env = False
            session = self._session
            response = session.request(
                method_u,
                target,
                headers=headers,
                data=data,
                timeout=25,
                verify=False,
                allow_redirects=allow_redirects,
            )
            status = int(response.status_code or 0)
            body = response.text or ""
            final_url = str(response.url or target)
            try:
                header_text = "\n".join("%s: %s" % (k, v) for k, v in response.headers.items())
            except Exception:
                header_text = ""
            for c in session.cookies:
                jar[c.name] = c.value
            jar.update(self._cookie_from_headers(header_text))
            if jar:
                self._cookie = self._merge_cookie(self._cookie, jar)
            return {"status": status, "body": body, "header": header_text, "url": final_url, "cookies": jar}
        except Exception as exc:
            print("[AVDAY] persistent session error:", type(exc).__name__)

        # Fallback for shells without requests: native fetch / urllib below.

        try:
            if method_u == "GET" and hasattr(self, "fetch"):
                response = self.fetch(target, headers=headers)
                if response is not None:
                    if isinstance(response, str):
                        body = response
                        status = 200
                    else:
                        body = getattr(response, "text", None) or ""
                        if not body:
                            content = getattr(response, "content", None)
                            if isinstance(content, bytes):
                                body = content.decode("utf-8", "ignore")
                            elif content is not None:
                                body = str(content)
                        status = int(getattr(response, "status_code", None) or getattr(response, "status", None) or 200)
                        # try headers/cookies if present
                        rh = getattr(response, "headers", None)
                        if rh:
                            try:
                                if hasattr(rh, "items"):
                                    header_text = "\n".join("%s: %s" % (k, v) for k, v in rh.items())
                                else:
                                    header_text = str(rh)
                            except Exception:
                                header_text = ""
                        rc = getattr(response, "cookies", None)
                        if rc:
                            try:
                                if hasattr(rc, "items"):
                                    jar = dict(rc.items())
                                else:
                                    for c in rc:
                                        jar[getattr(c, "name", "")] = getattr(c, "value", "")
                            except Exception:
                                pass
                        final_url = str(getattr(response, "url", target) or target)
                    if body or status:
                        jar.update(self._cookie_from_headers(header_text))
                        return {"status": status or 200, "body": body or "", "header": header_text, "url": final_url, "cookies": jar}
            if method_u == "POST":
                post_fn = getattr(self, "post", None)
                if callable(post_fn):
                    response = post_fn(target, data=data, headers=headers)
                    if response is not None:
                        if isinstance(response, str):
                            body = response
                            status = 200
                        else:
                            body = getattr(response, "text", None) or ""
                            status = int(getattr(response, "status_code", None) or getattr(response, "status", None) or 200)
                            rh = getattr(response, "headers", None)
                            if rh and hasattr(rh, "items"):
                                header_text = "\n".join("%s: %s" % (k, v) for k, v in rh.items())
                            rc = getattr(response, "cookies", None)
                            if rc and hasattr(rc, "get_dict"):
                                jar = rc.get_dict()
                            final_url = str(getattr(response, "url", target) or target)
                        jar.update(self._cookie_from_headers(header_text))
                        return {"status": status or 200, "body": body or "", "header": header_text, "url": final_url, "cookies": jar}
                # some shells: fetch(..., method='POST', data=...)
                if hasattr(self, "fetch"):
                    try:
                        response = self.fetch(target, headers=headers, method="POST", data=data)
                        if response is not None:
                            if isinstance(response, str):
                                body = response
                            else:
                                body = getattr(response, "text", None) or str(response or "")
                            return {"status": 200, "body": body or "", "header": "", "url": target, "cookies": {}}
                    except TypeError:
                        pass
                    except Exception as exc:
                        print("[AVDAY] fetch POST error:", type(exc).__name__)
        except Exception as exc:
            print("[AVDAY] shell http error:", type(exc).__name__)

        # 2) urllib (stdlib, good raw headers for login)
        try:
            import ssl
            from urllib.request import Request, build_opener, HTTPRedirectHandler, HTTPCookieProcessor, HTTPSHandler
            from urllib.parse import urlencode
            from http.cookiejar import CookieJar

            class NoRedirect(HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    if allow_redirects:
                        return HTTPRedirectHandler.redirect_request(self, req, fp, code, msg, headers, newurl)
                    return None

            jar_obj = CookieJar()
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            opener = build_opener(HTTPCookieProcessor(jar_obj), HTTPSHandler(context=ctx), NoRedirect)
            payload = None
            req_headers = dict(headers)
            if method_u == "POST":
                if isinstance(data, dict):
                    payload = urlencode(data).encode("utf-8")
                elif isinstance(data, str):
                    payload = data.encode("utf-8")
                elif isinstance(data, bytes):
                    payload = data
                else:
                    payload = b""
                req_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
            # seed cookie jar from Cookie header for better redirect continuity
            raw_cookie = req_headers.get("Cookie") or req_headers.get("cookie") or ""
            if raw_cookie:
                try:
                    from http.cookiejar import Cookie
                    import time as _t
                    for part in raw_cookie.split(";"):
                        part = part.strip()
                        if not part or "=" not in part:
                            continue
                        name, value = part.split("=", 1)
                        name = name.strip(); value = value.strip()
                        if not name:
                            continue
                        c = Cookie(0, name, value, None, False, "avday.app", True, True, "/", True, False, int(_t.time()) + 86400, False, None, None, {})
                        try:
                            jar_obj.set_cookie(c)
                        except Exception:
                            pass
                except Exception:
                    pass
            request = Request(target, data=payload, headers=req_headers, method=method_u)
            try:
                with opener.open(request, timeout=25) as resp:
                    status = getattr(resp, "status", None) or resp.getcode() or 200
                    final_url = resp.geturl()
                    try:
                        header_text = "\n".join("%s: %s" % (k, v) for k, v in resp.headers.items())
                    except Exception:
                        header_text = str(getattr(resp, "headers", "") or "")
                    # collect all set-cookie if possible
                    try:
                        scs = resp.headers.get_all("Set-Cookie") if hasattr(resp.headers, "get_all") else None
                        if scs:
                            header_text += "\n" + "\n".join("Set-Cookie: " + x for x in scs)
                    except Exception:
                        pass
                    raw = resp.read() or b""
                    body = raw.decode("utf-8", "ignore")
            except Exception as exc:
                resp = getattr(exc, "headers", None)
                if resp is not None:
                    try:
                        header_text = "\n".join("%s: %s" % (k, v) for k, v in resp.items())
                    except Exception:
                        header_text = str(resp)
                fp = getattr(exc, "fp", None) or getattr(exc, "file", None)
                if fp is not None:
                    try:
                        body = (fp.read() or b"").decode("utf-8", "ignore")
                    except Exception:
                        body = ""
                status = int(getattr(exc, "code", 0) or 0)
                final_url = target
                if status == 0 and not body and not header_text:
                    raise
            for c in jar_obj:
                jar[c.name] = c.value
            jar.update(self._cookie_from_headers(header_text))
            return {"status": status, "body": body or "", "header": header_text, "url": final_url, "cookies": jar}
        except Exception as exc:
            print("[AVDAY] urllib error:", type(exc).__name__, exc)

        # 3) requests last
        try:
            import requests
            from requests.adapters import HTTPAdapter
            from urllib3.util.retry import Retry
            session = requests.Session()
            session.trust_env = False  # avoid broken local proxy stripping auth cookies
            try:
                retry = Retry(total=2, backoff_factor=0.4, status_forcelist=[502, 503, 504])
                session.mount("https://", HTTPAdapter(max_retries=retry))
                session.mount("http://", HTTPAdapter(max_retries=retry))
            except Exception:
                pass
            resp = session.request(
                method_u,
                target,
                headers=headers,
                data=data,
                timeout=25,
                verify=False,
                allow_redirects=allow_redirects,
            )
            status = int(resp.status_code or 0)
            body = resp.text or ""
            final_url = str(resp.url or target)
            try:
                header_text = "\n".join("%s: %s" % (k, v) for k, v in resp.headers.items())
            except Exception:
                header_text = ""
            # include set-cookie list if available
            try:
                raw_sc = resp.raw.headers.getlist("Set-Cookie") if hasattr(resp.raw.headers, "getlist") else []
                if raw_sc:
                    header_text += "\n" + "\n".join("Set-Cookie: " + x for x in raw_sc)
            except Exception:
                pass
            for c in session.cookies:
                jar[c.name] = c.value
            jar.update(self._cookie_from_headers(header_text))
            return {"status": status, "body": body, "header": header_text, "url": final_url, "cookies": jar}
        except Exception as exc:
            print("[AVDAY] requests error:", type(exc).__name__)

        return {"status": status, "body": body, "header": header_text, "url": final_url, "cookies": jar}

    def _is_warn_page(self, body, url=""):
        text = body or ""
        u = str(url or "")
        if "/warn" in u:
            return True
        if 'id="btn-ok"' in text or "同意並進入" in text or "同意并进入" in text:
            return True
        if "warn-content" in text and "未滿18" in text:
            return True
        return False

    def _pass_age_gate(self, referer=None):
        # warn.js only sets avAgree=1; we set it directly and hit home once
        self._cookie = self._merge_cookie(self._cookie, {"AVDAYRef": "main", "avAgree": "1"})
        headers = {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
            "Accept-Language": "zh-TW,zh;q=0.9",
            "Referer": referer or (self.host + "/warn"),
            "Cookie": self._cookie,
        }
        try:
            self._http("GET", self.host + "/", headers=headers, allow_redirects=True)
        except Exception:
            pass
        return self._cookie

    def _needs_login(self, body, cards=None):

        text = body or ""
        if cards:
            return False
        markers = [
            'id="login-form"',
            "id='login-form'",
            "抱歉，没有影片",
            "抱歉，沒有影片",
            "請先登入",
            "请先登录",
            "請登入",
            "请登录",
            'name="password"',
            'name="email"',
            'action="/login"',
            'type="login"',
        ]
        if any(x in text for x in markers):
            return True
        # protected empty short/exclusive pages
        if re.search(r"/list/short|/exclusive/", text) or ("短片" in text and "watch/" not in text):
            if not re.search(r"/watch/(?:long|short)/[a-f0-9]{32}", text, re.I):
                return True
        return False

    def _extract_csrf(self, body):
        text = body or ""
        patterns = [
            r'<form[^>]*id=["\']login-form["\'][^>]*>[\s\S]*?<input[^>]*name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']',
            r'<input[^>]*name=["\']_token["\'][^>]*value=["\']([^"\']+)["\']',
            r'<input[^>]*value=["\']([^"\']+)["\'][^>]*name=["\']_token["\']',
            r'name=["\']csrf-token["\']\s+content=["\']([^"\']+)["\']',
            r'content=["\']([^"\']+)["\']\s+name=["\']csrf-token["\']',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.I)
            if m:
                return m.group(1).strip()
        return ""

    def _ensure_login(self, force=False):
        return self._login(force=force)

    def _login(self, force=False):
        # PHP: cache 6h and require AVDAY_AUTH
        if not force:
            if self._cookie and "AVDAY_AUTH=" in self._cookie:
                return True
            if self._load_cookie_cache() and "AVDAY_AUTH=" in (self._cookie or ""):
                return True

        auth = self._auth or self._load_auth(getattr(self, "extend", "") or "")
        email = (auth.get("email") or getattr(self, "login_email", "") or "").strip()
        password = (auth.get("password") or getattr(self, "login_password", "") or "").strip()
        if not email or not password:
            print("[AVDAY] login skipped: missing email/password")
            return False

        base_cookie = "AVDAYRef=main; avAgree=1"
        login_url = self.host + "/login"
        h1 = {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
            "Accept-Language": "zh-TW,zh;q=0.9",
            "Referer": self.host + "/",
            "Cookie": base_cookie,
        }
        page = self._http("GET", login_url, headers=h1, allow_redirects=True)
        body = page.get("body") or ""
        jar1 = dict(page.get("cookies") or {})
        jar1.update(self._cookie_from_headers(page.get("header") or "", ["XSRF-TOKEN", "avday_session", "AVDAY_AUTH", "avAgree", "AVDAYRef"]))
        # age wall may intercept /login -> /warn
        if self._is_warn_page(body, page.get("url") or ""):
            self._pass_age_gate(login_url)
            h1 = dict(h1)
            h1["Cookie"] = self._merge_cookie(base_cookie, self._cookie, jar1)
            page = self._http("GET", login_url, headers=h1, allow_redirects=True)
            body = page.get("body") or ""
            jar1.update(page.get("cookies") or {})
            jar1.update(self._cookie_from_headers(page.get("header") or "", ["XSRF-TOKEN", "avday_session", "AVDAY_AUTH", "avAgree", "AVDAYRef"]))
        token = self._extract_csrf(body)
        if not token:
            # one more age-pass + retry
            self._pass_age_gate(login_url)
            h1 = dict(h1)
            h1["Cookie"] = self._merge_cookie(base_cookie, self._cookie, jar1)
            page = self._http("GET", login_url, headers=h1, allow_redirects=True)
            body = page.get("body") or ""
            jar1.update(page.get("cookies") or {})
            jar1.update(self._cookie_from_headers(page.get("header") or "", ["XSRF-TOKEN", "avday_session", "AVDAY_AUTH", "avAgree", "AVDAYRef"]))
            token = self._extract_csrf(body)
        if not token:
            print("[AVDAY] login failed: csrf token missing; body_len=", len(body), "status=", page.get("status"), "url=", page.get("url"))
            return False

        cookie_post = self._merge_cookie(base_cookie, jar1)
        h2 = {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
            "Accept-Language": "zh-TW,zh;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": self.host,
            "Referer": login_url,
            "Cookie": cookie_post,
        }
        form = {
            "_token": token,
            "type": "login",
            "email": email,
            "password": password,
        }
        # PHP uses followlocation true on post
        resp = self._http("POST", login_url, headers=h2, data=form, allow_redirects=True)
        jar2 = dict(resp.get("cookies") or {})
        jar2.update(self._cookie_from_headers(resp.get("header") or "", ["XSRF-TOKEN", "avday_session", "AVDAY_AUTH", "avAgree", "AVDAYRef"]))

        # Sometimes auth cookie only appears after one more hop
        if "AVDAY_AUTH" not in jar2:
            home = self._http(
                "GET",
                self.host + "/",
                headers={
                    "User-Agent": self.ua,
                    "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
                    "Accept-Language": "zh-TW,zh;q=0.9",
                    "Referer": login_url,
                    "Cookie": self._merge_cookie(cookie_post, jar2),
                },
                allow_redirects=True,
            )
            jar2.update(home.get("cookies") or {})
            jar2.update(self._cookie_from_headers(home.get("header") or "", ["XSRF-TOKEN", "avday_session", "AVDAY_AUTH", "avAgree", "AVDAYRef"]))

        cookie2 = self._merge_cookie(base_cookie, jar2)
        if "AVDAY_AUTH=" not in cookie2:
            print("[AVDAY] login failed: AVDAY_AUTH missing; status=", resp.get("status"), "url=", resp.get("url"))
            # keep partial cookies for debug, but treat as fail like PHP when no atoken
            return False

        self._cookie = cookie2
        self._save_cookie_cache(cookie2)
        print("[AVDAY] login ok")
        return True

    def _headers(self, referer=None):
        if not getattr(self, "_cookie", None):
            self._cookie = "AVDAYRef=main; avAgree=1"
            self._load_cookie_cache()
        # PHP: every page request uses do_login() cookie when possible
        if "AVDAY_AUTH=" not in (self._cookie or ""):
            # non-blocking best effort; ignore failure here
            try:
                self._login(force=False)
            except Exception:
                pass
        return {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
            "Accept-Language": "zh-TW,zh;q=0.9",
            "Referer": referer or (self.host + "/"),
            "Cookie": self._cookie or "AVDAYRef=main; avAgree=1",
        }

    def _fetch_html(self, url, referer=None, auto_login=True):
        target = self._abs(url)
        # PHP http_get: always ensure login cookie first
        if auto_login:
            self._ensure_login(force=False)
        headers = self._headers(referer)
        data = self._http("GET", target, headers=headers, allow_redirects=True)
        body = data.get("body") or ""
        final_url = data.get("url") or target
        # age gate
        if self._is_warn_page(body, final_url):
            self._pass_age_gate(final_url)
            headers = self._headers(referer)
            data = self._http("GET", target, headers=headers, allow_redirects=True)
            body = data.get("body") or ""
            final_url = data.get("url") or target
        # PHP: login-form => clear cache, force login, retry once
        if auto_login:
            cards = self._cards(body)
            strong = (
                ('id="login-form"' in body)
                or ('name="password"' in body)
                or (not cards and self._needs_login(body, cards=None))
                or (not cards and ("/list/short" in target or "/exclusive/" in target))
            )
            if strong:
                self._clear_cookie_cache()
                if self._login(force=True):
                    headers = self._headers(referer)
                    data = self._http("GET", target, headers=headers, allow_redirects=True)
                    body = data.get("body") or ""
                    if self._is_warn_page(body, data.get("url") or ""):
                        self._pass_age_gate(data.get("url") or target)
                        headers = self._headers(referer)
                        data = self._http("GET", target, headers=headers, allow_redirects=True)
                        body = data.get("body") or ""
        return body


    def _abs(self, url):
        value = str(url or "").strip()
        if not value:
            return ""
        if value.startswith("//"):
            return "https:" + value
        if value.startswith("http://") or value.startswith("https://"):
            return value
        return urljoin(self.host + "/", value.lstrip("/"))

    def _clean(self, text):
        value = re.sub(r"<[^>]+>", " ", str(text or ""))
        value = html_lib.unescape(value)
        return re.sub(r"\s+", " ", value).strip()

    def _tag_row(self, key, name, kind, tags):
        values = [{"n": "全部", "v": ""}]
        for tag in tags:
            values.append({"n": tag, "v": kind + "/tag/" + quote(tag)})
        return {"key": key, "name": name, "value": values}

    def _filters(self):
        long_filter = [self._tag_row("tag", "標籤", "long", self.long_tags)]
        short_filter = [self._tag_row("tag", "標籤", "short", self.short_tags)]
        exclusive = [{
            "key": "sub",
            "name": "子分類",
            "value": [
                {"n": "最新", "v": "exclusive/new"},
                {"n": "麻豆", "v": "exclusive/madou"},
                {"n": "獨家台片", "v": "exclusive/ras"},
                {"n": "馬賽克破壞", "v": "exclusive/damage"},
            ],
        }]
        return {
            "c1": long_filter,
            "c2": short_filter,
            "c3": long_filter,
            "c4": long_filter,
            "c5": exclusive,
        }

    def _direct_m3u8(self, value):
        text = str(value or "").strip()
        match = re.search(r"/watch/(long|short)/([a-f0-9]{32})", text, re.I)
        if match:
            return self.host + "/video/" + match.group(1) + "/" + match.group(2) + ".m3u8"
        if re.fullmatch(r"[a-f0-9]{32}", text, re.I):
            return self.host + "/video/long/" + text + ".m3u8"
        if re.search(r"\.(?:m3u8|mp4)(?:\?|$)", text, re.I):
            return self._abs(text)
        return ""

    def _cards(self, text):
        html = text or ""
        rows, seen = [], set()

        def add_row(link, title, pic, remarks=""):
            link = self._abs(link)
            title = self._clean(title)
            if not link or not title or link in seen:
                return
            if not re.search(r"/watch/(?:long|short)/[a-f0-9]{32}", link, re.I):
                return
            seen.add(link)
            rows.append({
                "vod_id": link,
                "vod_name": title,
                "vod_pic": self._abs(pic) if pic else "",
                "vod_remarks": remarks or "",
            })

        # PHP style blocks
        blocks = html.split('<div class="mb-4">')
        if len(blocks) > 1:
            for block in blocks[1:]:
                hm = re.search(r'href=["\']([^"\']+/watch/(?:long|short)/[a-f0-9]{32})["\']', block, re.I)
                if not hm:
                    hm = re.search(r'href=["\'](https?://[^"\']+/watch/[^"\']+)["\']', block, re.I)
                if not hm:
                    continue
                title = ""
                tm = re.search(r'itemprop=["\']name["\'][^>]*>([^<]+)<', block, re.I)
                if tm:
                    title = tm.group(1)
                if not title:
                    tm = re.search(r'alt=["\']([^"\']+)["\']', block, re.I)
                    if tm:
                        title = tm.group(1)
                if not title:
                    continue
                pic = ""
                im = re.search(r'(?:data-src|data-original|src)=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', block, re.I)
                if im:
                    pic = im.group(1)
                remarks = ""
                rem = re.search(r'(\d{2}:\d{2}(?::\d{2})?|\d+[K萬万])', block)
                if rem:
                    remarks = rem.group(1)
                add_row(hm.group(1), title, pic, remarks)

        if not rows:
            pattern = re.compile(
                r'<a[^>]+href=["\']([^"\']+/watch/(?:long|short)/[a-f0-9]{32})["\'][^>]*>(.*?)</a>',
                re.I | re.S,
            )
            for href, block in pattern.findall(html):
                title = ""
                t1 = re.search(r'itemprop=["\']name["\'][^>]*>(.*?)</', block, re.I | re.S)
                if t1:
                    title = t1.group(1)
                if not title:
                    t2 = re.search(r'alt=["\']([^"\']+)["\']', block, re.I)
                    if t2:
                        title = t2.group(1)
                if not title:
                    continue
                pic = ""
                p1 = re.search(r'<img[^>]+(?:data-src|data-original|src)=["\']([^"\']+)["\']', block, re.I)
                if p1:
                    pic = p1.group(1)
                remarks = ""
                rem = re.search(r'(\d{2}:\d{2}(?::\d{2})?|\d+[K萬万])', block)
                if rem:
                    remarks = rem.group(1)
                add_row(href, title, pic, remarks)
        return rows

    def _pagecount(self, text, page):
        pages = [int(page)]
        for x in re.findall(r"[?&]page=(\d+)", text or ""):
            try:
                pages.append(int(x))
            except Exception:
                pass
        for x in re.findall(r">(\d{1,4})</a>", text or ""):
            try:
                n = int(x)
                if 1 <= n < 9999:
                    pages.append(n)
            except Exception:
                pass
        return max(pages) if pages else int(page or 1)

    def _extend(self, extend):
        if extend is None:
            return {}
        if isinstance(extend, dict):
            return extend
        text = str(extend or "").strip()
        if not text:
            return {}
        try:
            import json
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _list_url(self, tid, page, extend=None):
        page = max(1, int(page or 1))
        ext = self._extend(extend)
        # filter values from PHP-style: long/tag/xxx or exclusive/new
        chosen = ""
        for key in ("tag", "sub", "r1", "class", "type"):
            value = str(ext.get(key, "") or "").strip()
            if value:
                chosen = value
                break
        if not chosen:
            # some shells flatten first non-empty value
            for value in ext.values():
                text = str(value or "").strip()
                if text:
                    chosen = text
                    break
        if chosen:
            path = chosen if chosen.startswith("/") else "/" + chosen.lstrip("/")
            base = self.host + path
        else:
            base = self.host + self.type_url_map.get(str(tid), "/list/long")
        if page > 1:
            join = "&" if "?" in base else "?"
            return base + join + "page=" + str(page)
        return base

    def homeContent(self, filter=False):
        result = {
            "class": [
                {"type_id": x, "type_name": y}
                for x, y in zip(self.class_url, self.class_name)
            ],
            "filters": self._filters(),
            "list": [],
        }
        try:
            self._ensure_login(force=False)
            text = self._fetch_html(self.host + "/list/long", auto_login=True)
            result["list"] = self._cards(text)[: self.page_size]
            if not result["list"]:
                if self._login(force=True):
                    text = self._fetch_html(self.host + "/list/long", auto_login=False)
                    result["list"] = self._cards(text)[: self.page_size]
        except Exception as exc:
            print("[AVDAY] home error:", exc)
        return result

    def homeVideoContent(self):
        try:
            return {"list": self._cards(self._fetch_html(self.host + "/list/long"))[: self.page_size]}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        page = max(1, int(pg or 1))
        url = self._list_url(tid, page, extend)
        need_auth = str(tid) in ("c2", "c5") or "/list/short" in url or "/exclusive/" in url
        # short/exclusive: must have AVDAY_AUTH up front
        if need_auth:
            if "AVDAY_AUTH=" not in (self._cookie or ""):
                self._login(force=True)
            else:
                self._ensure_login(force=False)
        else:
            self._ensure_login(force=False)
        text = self._fetch_html(url, referer=self.host + "/", auto_login=True)
        cards = self._cards(text)
        if not cards:
            # empty list: force re-login once then retry
            self._clear_cookie_cache()
            if self._login(force=True):
                text = self._fetch_html(url, referer=self.host + "/", auto_login=False)
                cards = self._cards(text)
        # short sometimes serves alternate markup; try bare /list/short without query once
        if not cards and need_auth and "page=" in url:
            alt = re.sub(r"[?&]page=\d+", "", url).rstrip("?&")
            text2 = self._fetch_html(alt, referer=self.host + "/", auto_login=True)
            cards2 = self._cards(text2)
            if cards2:
                text, cards = text2, cards2
        pagecount = self._pagecount(text, page)
        if cards and pagecount <= page:
            pagecount = page + 1
        if not cards:
            pagecount = page
        return {
            "list": cards,
            "page": page,
            "pagecount": pagecount,
            "limit": self.page_size,
            "total": pagecount * self.page_size,
        }

    def detailContent(self, ids):
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0] if ids else "")
        else:
            vid = str(ids or "")
        if not vid:
            return {"list": []}
        url = self._abs(vid)
        text = self._fetch_html(url, referer=self.host + "/")
        title = ""
        for pattern in (
            r'property=["\']og:title["\']\s+content=["\']([^"\']+)["\']',
            r'content=["\']([^"\']+)["\']\s+property=["\']og:title["\']',
            r"<title[^>]*>(.*?)\|\s*AVDAY",
        ):
            match = re.search(pattern, text or "", re.I | re.S)
            if match:
                title = self._clean(match.group(1))
                title = re.sub(r"\s*\|\s*AVDAY.*$", "", title).strip()
                if title:
                    break
        if not title:
            title = self._clean(vid.rsplit("/", 1)[-1]) or "AVDAY"
        pic = ""
        for pattern in (
            r'property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
            r'content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
            r'<(?:video|img)[^>]+(?:poster|src)=["\']([^"\']+)["\']',
        ):
            match = re.search(pattern, text or "", re.I)
            if match:
                pic = self._abs(match.group(1))
                if pic:
                    break
        code = ""
        code_match = re.search(
            r"(?:影片番號|番號|識別碼)[\s\S]{0,120}?<(?:h2|div|span)[^>]*>([\s\S]*?)</(?:h2|div|span)>",
            text or "",
            re.I,
        )
        if code_match:
            code = self._clean(code_match.group(1))
        actors = " ".join(
            self._clean(x)
            for x in re.findall(r'class=["\'][^"\']*video-actor[^"\']*["\'][^>]*>([^<]+)', text or "", re.I)
        )
        year = ""
        year_match = re.search(
            r'(?:itemprop=["\']uploadDate["\']\s+content=["\']([^"\']+)["\']|"datePublished"\s*:\s*"([^"]+)")',
            text or "",
            re.I,
        )
        if year_match:
            year = (year_match.group(1) or year_match.group(2) or "")[:10]

        play = self._direct_m3u8(url)
        # prefer formal long m3u8 from page script, skip intro trailers
        page_links = re.findall(
            r"(https?://[^\"'\s]+/video/(?:long|short)/[a-f0-9]{32}\.m3u8[^\"'\s]*)",
            text or "",
            re.I,
        )
        page_links += re.findall(
            r'["\'](/video/(?:long|short)/[a-f0-9]{32}\.m3u8[^"\']*)["\']',
            text or "",
            re.I,
        )
        for link in page_links:
            abs_link = self._abs(link)
            if "intro" in abs_link.lower():
                continue
            play = abs_link
            break
        if not play:
            # last resort: any non-intro m3u8
            for link in re.findall(r"(https?://[^\"'\s]+\.m3u8[^\"'\s]*|/[^\"'\s]+\.m3u8[^\"'\s]*)", text or "", re.I):
                abs_link = self._abs(link)
                if "intro" in abs_link.lower():
                    continue
                play = abs_link
                break
        if not play:
            play = self._direct_m3u8(url) or url

        ep = re.sub(r"[$#]", "", code or title) or "播放"
        return {
            "list": [{
                "vod_id": url,
                "vod_name": title,
                "vod_pic": pic,
                "vod_year": year,
                "vod_actor": actors,
                "vod_remarks": code,
                "vod_content": code or title,
                "vod_play_from": "直链",
                "vod_play_url": ep + "$" + play,
            }]
        }

    def searchContent(self, key, quick=False, pg="1"):
        page = max(1, int(pg or 1))
        url = self.host + "/search?q=" + quote(str(key or ""))
        if page > 1:
            url += "&page=" + str(page)
        text = self._fetch_html(url, referer=self.host + "/")
        cards = self._cards(text)
        pagecount = self._pagecount(text, page)
        if cards and pagecount <= page:
            pagecount = page + 1
        return {
            "list": cards,
            "page": page,
            "pagecount": pagecount,
            "limit": self.page_size,
            "total": pagecount * self.page_size,
        }

    def playerContent(self, flag, id, vipFlags=None):
        value = str(id or "")
        media = self._direct_m3u8(value)
        if not media and re.search(r"\.(?:m3u8|mp4)(?:\?|$)", value, re.I):
            media = self._abs(value)
        if not media:
            media = value
        return {
            "parse": 0 if re.search(r"\.(?:m3u8|mp4)(?:\?|$)", media, re.I) else 1,
            "url": media,
            "header": self._headers(self.host + "/"),
        }

    def isVideoFormat(self, url):
        return bool(re.search(r"\.(?:m3u8|mp4)(?:\?|$)", str(url or ""), re.I))

    def manualVideoCheck(self):
        return False

    def localProxy(self, params):
        return None

    def destroy(self):
        return None
