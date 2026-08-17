# coding=utf-8
import sys
import json
import re
import base64
from urllib.parse import unquote, quote, urljoin, urlparse

try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider():
        def fetch(self, url, headers=None, timeout=10):
            try:
                import requests
                res = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
                res.encoding = 'utf-8'
                return res
            except Exception as e:
                print(f"fetch error: {e}")
                return None


class Spider(BaseSpider):
    def getName(self):
        return "超人在线"

    def init(self, extend=""):
        self.host = "https://aadd.cr888.sbs"
        print(f"[init] host: {self.host}")
        self.session = requests.Session() if 'requests' in sys.modules else None
        if self.session:
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'keep-alive'
            })

    def homeVideoContent(self):
        result = {"list": []}
        try:
            res = self.fetch(self.host + '/', headers={'Referer': self.host})
            if res:
                result['list'] = self._parse_list_html(res.text)
        except Exception as e:
            print(f"[homeVideoContent] error: {e}")
        return result

    def homeContent(self, filter):
        classes = [
            {"type_name": "国产自拍", "type_id": "34fds"},
            {"type_name": "网曝门事件", "type_id": "sdsf4"},
            {"type_name": "网红主播", "type_id": "sdffs"},
            {"type_name": "日本无码", "type_id": "sdfsd2"},
            {"type_name": "魔镜系列", "type_id": "sadas34"},
            {"type_name": "三级电影", "type_id": "sdfsd4"},
            {"type_name": "欧美精品", "type_id": "sdfsds11"},
            {"type_name": "人妻熟女", "type_id": "sdfsd45"},
            {"type_name": "淫欲痴女", "type_id": "%e6%b7%ab%e6%ac%b2%e7%97%b4%e5%a5%b3"},
            {"type_name": "美乳巨乳", "type_id": "asda3"},
            {"type_name": "无码", "type_id": "tag/%e6%97%a0%e7%a0%81"},
            {"type_name": "探花", "type_id": "tag/%e6%8e%a2%e8%8a%b1"},
            {"type_name": "母狗", "type_id": "tag/%e6%af%8d%e7%8b%97"},
            {"type_name": "高潮", "type_id": "tag/%e9%ab%98%e6%bd%ae"},
        ]
        return {'class': classes, 'filters': {}}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg)
        result = {"list": [], "page": pg, "pagecount": 999, "limit": 24, "total": 9999}
        try:
            if tid.startswith("tag/"):
                base = f"{self.host}/{tid}"
                url = f"{base}/page/{pg}/" if pg > 1 else f"{base}/"
            else:
                base = f"{self.host}/{tid}"
                url = f"{base}/page/{pg}/" if pg > 1 else f"{base}/"
            print(f"[categoryContent] {url}")
            res = self.fetch(url, headers={'Referer': self.host})
            if res:
                html = res.text
                result['list'] = self._parse_list_html(html)
                has_next = re.search(r'<a[^>]*class=["\']next\s+page-numbers["\']', html, re.I | re.S)
                if not has_next:
                    result['pagecount'] = pg if result['list'] else (pg - 1 if pg > 1 else 1)
        except Exception as e:
            print(f"[categoryContent] error: {e}")
        return result

    def _parse_list_html(self, html):
        vod_list = []
        try:
            items = re.findall(
                r'gridsoul-grid-post-(\d+)[^<]*<div[^>]*class=["\']gridsoul-grid-post-inside["\'][^>]*>'
                r'.*?href=["\']([^"\']+)["\'][^>]*title=["\']([^"\']*)["\'][^>]*>'
                r'.*?src=["\']([^"\']+)["\'][^>]*class=["\']gridsoul-grid-post-thumbnail-img["\']'
                r'.*?<h3[^>]*class=["\']gridsoul-grid-post-title["\'][^>]*>.*?<a[^>]*>(.*?)</a>.*?</h3>'
                r'.*?themesdna-views[^>]*>(\d+)</span>',
                html, re.DOTALL | re.I
            )
            if items:
                for item in items:
                    vid, href, title, pic, name, views = item
                    name = re.sub(r'<[^>]+>', '', name).strip()
                    vod_list.append({
                        "vod_id": vid,
                        "vod_name": name or title.strip(),
                        "vod_pic": pic.strip(),
                        "vod_remarks": f"{views}次观看"
                    })
            if not vod_list:
                items = re.findall(
                    r'gridsoul-grid-post-(\d+)[^<]*<div[^>]*class=["\']gridsoul-grid-post-inside["\'][^>]*>'
                    r'.*?href=["\']([^"\']+)["\'][^>]*title=["\']([^"\']*)["\'][^>]*>'
                    r'.*?src=["\']([^"\']+)["\'][^>]*class=["\']gridsoul-grid-post-thumbnail-img["\']'
                    r'.*?<h3[^>]*class=["\']gridsoul-grid-post-title["\'][^>]*>.*?<a[^>]*>(.*?)</a>.*?</h3>',
                    html, re.DOTALL | re.I
                )
                for item in items:
                    vid, href, title, pic, name = item
                    name = re.sub(r'<[^>]+>', '', name).strip()
                    vod_list.append({
                        "vod_id": vid,
                        "vod_name": name or title.strip(),
                        "vod_pic": pic.strip(),
                        "vod_remarks": ""
                    })
            if not vod_list:
                items = re.findall(
                    r'gridsoul-grid-post-(\d+)[^>]*>.*?<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)<img[^>]*src=["\']([^"\']+)["\'][^>]*>.*?<h3[^>]*>(.*?)</h3>',
                    html, re.DOTALL | re.I
                )
                for item in items:
                    vid, href, pic, name = item[0], item[1], item[3], item[4]
                    name = re.sub(r'<[^>]+>', '', name).strip()
                    vod_list.append({
                        "vod_id": vid,
                        "vod_name": name,
                        "vod_pic": pic.strip(),
                        "vod_remarks": ""
                    })
        except Exception as e:
            print(f"[_parse_list_html] error: {e}")
        seen = set()
        deduped = []
        for vod in vod_list:
            if vod['vod_id'] not in seen:
                seen.add(vod['vod_id'])
                deduped.append(vod)
        return deduped

    def _extract_title(self, html):
        try:
            m = re.search(r'<title>(.*?)</title>', html, re.I | re.S)
            if m:
                raw = m.group(1)
                for sep in ['|', '-', '_', '—']:
                    if sep in raw:
                        raw = raw.split(sep)[0]
                        break
                t = raw.strip()
                if t and t not in ['', '超人在线']:
                    return t
            m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.I | re.S)
            if m:
                t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                if t:
                    return t
            m = re.search(r'<h3[^>]*class=["\']gridsoul-grid-post-title["\'][^>]*>(.*?)</h3>', html, re.I | re.S)
            if m:
                t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
                if t:
                    return t
        except:
            pass
        return ""

    def detailContent(self, ids):
        vid = ids[0] if ids else ""
        title = ""
        desc = "资源来自于网络"
        pic = ""
        try:
            detail_url = f"{self.host}/{vid}.html"
            res = self.fetch(detail_url, headers={'Referer': self.host})
            if res:
                html = res.text
                title = self._extract_title(html)
                m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', html, re.I)
                if m:
                    desc = m.group(1)
                m = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
                if m:
                    pic = m.group(1)
        except Exception as e:
            print(f"[detailContent] error: {e}")
        if not title:
            title = f"视频{vid}"
        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_type": "视频",
                "vod_content": desc,
                "vod_play_from": "超人在线",
                "vod_play_url": f"播放${vid}"
            }]
        }

    def searchContent(self, key, quick, pg=1):
        result = {"list": []}
        try:
            url = f"{self.host}/?s={quote(key)}"
            if pg > 1:
                url += f"&paged={pg}"
            res = self.fetch(url, headers={'Referer': self.host})
            if res:
                result['list'] = self._parse_list_html(res.text)
        except Exception as e:
            print(f"[searchContent] error: {e}")
        return result

    def playerContent(self, flag, id, vipFlags=None):
        vid = str(id) if id else ""
        play_url = f"{self.host}/{vid}.html"
        print(f"[playerContent] vid={vid}")
        try:
            res = self.fetch(play_url, headers={'Referer': self.host}, timeout=8)
            if not res:
                return self._fail(play_url)
            html = res.text
            m3u8_url = self._find_m3u8(html, play_url)
            if not m3u8_url:
                print("[playerContent] m3u8 not found, use web parse")
                return self._fail(play_url)
            m3u8_url = self._sanitize_m3u8_url(m3u8_url)
            if m3u8_url.startswith('//'):
                m3u8_url = 'https:' + m3u8_url
            elif not m3u8_url.startswith('http'):
                m3u8_url = urljoin(self.host, m3u8_url)
            print(f"[playerContent] m3u8={m3u8_url}")
            proxy_url = self._proxy_m3u8_url(m3u8_url, play_url)
            header = {
                "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                "Referer": play_url,
                "Origin": self.host
            }
            return {
                "parse": 0,
                "jx": 0,
                "playUrl": "",
                "url": proxy_url,
                "header": json.dumps(header, ensure_ascii=False)
            }
        except Exception as e:
            print(f"[playerContent] error: {e}")
            return self._fail(play_url)

    def _fail(self, play_url):
        return {
            "parse": 1,
            "jx": 0,
            "playUrl": "",
            "url": play_url,
            "header": "{}"
        }

    def _find_m3u8(self, html, referer):
        # 1. direct m3u8
        m = re.search(r'(https?://[^\s"\'<>]+\.m3u8(?:\?[^"\s\'<>&]*)?)', html, re.I)
        if m:
            return m.group(1)
        # 2. player_aaaa
        cfg = self._extract_player_config(html)
        if cfg and cfg.get('url'):
            return cfg.get('url')
        # 3. iframe
        m = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
        if m:
            iframe_url = m.group(1)
            if iframe_url.startswith('//'):
                iframe_url = 'https:' + iframe_url
            elif not iframe_url.startswith('http'):
                iframe_url = urljoin(self.host, iframe_url)
            print(f"[iframe] {iframe_url}")
            res = self.fetch(iframe_url, headers={'Referer': referer}, timeout=8)
            if res:
                ih = res.text
                m = re.search(r'(https?://[^\s"\'<>]+\.m3u8(?:\?[^"\s\'<>&]*)?)', ih, re.I)
                if m:
                    return m.group(1)
                cfg = self._extract_player_config(ih)
                if cfg and cfg.get('url'):
                    return cfg.get('url')
        # 4. video/source
        for pat in [r'<video[^>]+src=["\']([^"\']+)["\']', r'<source[^>]+src=["\']([^"\']+\.m3u8[^"\']*)["\']']:
            m = re.search(pat, html, re.I)
            if m and '.m3u8' in m.group(1):
                return m.group(1)
        # 5. js decode
        d = self._js_decode(html)
        if d and '.m3u8' in d:
            return d
        # 6. xhr sniff
        d = self._sniff_xhr(html, referer)
        if d and '.m3u8' in d:
            return d
        return None

    def _extract_player_config(self, html):
        try:
            m = re.search(r'var\s+player_aaaa\s*=\s*\{', html or '', re.I)
            if not m:
                return {}
            start = m.end() - 1
            depth = 0
            in_str = ''
            esc = False
            for i in range(start, len(html)):
                ch = html[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == '\\\\':
                        esc = True
                    elif ch == in_str:
                        in_str = ''
                    continue
                if ch in ('"', "'"):
                    in_str = ch
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        return json.loads(html[start:i + 1])
        except Exception as e:
            print(f"[_extract_player_config] error: {e}")
        return {}

    def _js_decode(self, js_str):
        try:
            m = re.search(r'atob\s*\(\s*["\']([^"\']+)["\']\s*\)', js_str)
            if m:
                return base64.b64decode(m.group(1)).decode('utf-8')
        except:
            pass
        try:
            m = re.search(r'unescape\s*\(\s*["\']([^"\']+)["\']\s*\)', js_str)
            if m:
                return unquote(m.group(1))
        except:
            pass
        m = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', js_str, re.I)
        if m:
            return m.group(1)
        return None

    def _sniff_xhr(self, html, page_url):
        patterns = [
            r'fetch\s*\(\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'\.open\s*\(\s*["\']GET["\']\s*,\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'\.get\s*\(\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'url\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
            r'src\s*=\s*["\']([^"\']+\.m3u8[^"\']*)["\']',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.I)
            if m:
                url = m.group(1)
                if not url.startswith('http'):
                    url = urljoin(page_url, url)
                return url
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.I | re.S)
        for sc in scripts:
            if sc.strip():
                d = self._js_decode(sc)
                if d and '.m3u8' in d:
                    return d
        return None

    def _sanitize_m3u8_url(self, url):
        if not url:
            return url
        try:
            url = unquote(url)
            url = re.sub(r'&[Cc]over=.*', '', url)
            url = re.sub(r'&[Pp]oster=.*', '', url)
            url = re.sub(r'&[Tt]humb=.*', '', url)
            url = re.sub(r'&[Pp]ic=.*', '', url)
            url = url.rstrip('&?')
        except:
            pass
        return url

    def _proxy_m3u8_url(self, url, referer=''):
        try:
            if hasattr(self, 'getProxyUrl'):
                return self.getProxyUrl() + '&type=m3u8&url=' + quote(url, safe='') + '&referer=' + quote(referer or self.host, safe='')
        except Exception as e:
            print(f"[_proxy_m3u8_url] error: {e}")
        return url

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def fetch(self, url, headers=None, timeout=8):
        try:
            if self.session:
                req_headers = self.session.headers.copy()
                if headers:
                    req_headers.update(headers)
                res = self.session.get(url, headers=req_headers, timeout=timeout, allow_redirects=True)
            else:
                import requests
                res = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
            if res and (not res.encoding or res.encoding.lower() == 'iso-8859-1'):
                res.encoding = res.apparent_encoding or 'utf-8'
            return res
        except Exception as e:
            print(f"[fetch] error: {url} -> {e}")
            return None

    def localProxy(self, params):
        try:
            # params may be dict, str, or Java Map
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except:
                    params = {}
            if not isinstance(params, dict):
                params = {}
            do = params.get('type') or params.get('action') or params.get('do')
            url = params.get('url', '')
            if do not in ['m3u8', 'py'] and not url:
                return [404, "text/plain", "not found"]
            referer = params.get('referer', '') or self.host
            if isinstance(url, list):
                url = url[0] if url else ''
            if isinstance(referer, list):
                referer = referer[0] if referer else self.host
            try:
                url = unquote(url)
                referer = unquote(referer)
            except:
                pass
            print(f"[localProxy] url={url[:80]}...")
            text = self._get_m3u8_content(url, referer)
            if not text:
                return [502, "text/plain", "m3u8 download failed"]
            cleaned = self._clean_m3u8(text, url, referer)
            return [200, "application/vnd.apple.mpegurl", cleaned]
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            print(f"[localProxy] error: {e}\n{err}")
            return [500, "text/plain", f"proxy error: {e}"]

    def _get_m3u8_content(self, url, referer):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Referer': referer,
                'Origin': self.host,
                'Connection': 'keep-alive',
            }
            print(f"[_get_m3u8_content] fetching...")
            res = self.fetch(url, headers=headers, timeout=10)
            if res and res.status_code == 200:
                print(f"[_get_m3u8_content] ok, len={len(res.text)}")
                return res.text
            print(f"[_get_m3u8_content] fail status={res.status_code if res else 'None'}")
        except Exception as e:
            print(f"[_get_m3u8_content] error: {e}")
        return None

    def _is_ad_segment(self, uri, dur=0):
        u = (uri or '').strip().lower()
        if not u:
            return False
        ad_words = [
            'ad', 'ads', 'advert', 'advertise', 'advertisement', 'sponsor',
            'pre', 'preroll', '片头', '广告', '/gg/', '_gg', 'gg_', '/adv/',
            '/ad/', '/ads/', 'banner', 'promo', 'commercial'
        ]
        if any(w in u for w in ad_words):
            return True
        try:
            if 0 < float(dur) <= 1.2:
                return True
        except:
            pass
        return False

    def _parse_m3u8_segments(self, text):
        lines = [x.strip() for x in (text or '').replace('\r', '').split('\n') if x.strip()]
        header, segments, tail = [], [], []
        pending_tags = []
        media_sequence = 0
        target_duration = 0
        started = False
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('#EXT-X-MEDIA-SEQUENCE'):
                try:
                    media_sequence = int(line.split(':', 1)[1])
                except:
                    pass
                if not started:
                    header.append(line)
                else:
                    pending_tags.append(line)
            elif line.startswith('#EXT-X-TARGETDURATION'):
                try:
                    target_duration = float(line.split(':', 1)[1])
                except:
                    pass
                if not started:
                    header.append(line)
                else:
                    pending_tags.append(line)
            elif line.startswith('#EXTINF'):
                started = True
                dur = target_duration or 3.0
                m = re.search(r'#EXTINF:\s*([\d.]+)', line)
                if m:
                    try:
                        dur = float(m.group(1))
                    except:
                        pass
                tags = pending_tags + [line]
                pending_tags = []
                uri = ''
                j = i + 1
                while j < len(lines):
                    if lines[j].startswith('#'):
                        tags.append(lines[j])
                        j += 1
                        continue
                    uri = lines[j]
                    break
                if uri:
                    segments.append({'tags': tags, 'uri': uri, 'dur': dur})
                    i = j
                else:
                    tail.extend(tags)
            elif line.startswith('#EXT-X-ENDLIST'):
                tail.append(line)
            elif line.startswith('#'):
                if started:
                    pending_tags.append(line)
                else:
                    header.append(line)
            else:
                started = True
                dur = target_duration or 3.0
                segments.append({'tags': pending_tags, 'uri': line, 'dur': dur})
                pending_tags = []
            i += 1
        return header, segments, tail, media_sequence, target_duration

    def _segment_host_key(self, uri, base_url):
        try:
            full = urljoin(base_url, uri)
            p = urlparse(full)
            path = re.sub(r'/[^/]*$', '/', p.path or '/')
            return (p.netloc.lower(), path.lower())
        except:
            return ('', '')

    def _main_path_marker(self, m3u8_url):
        try:
            p = urlparse(m3u8_url).path
            m = re.search(r'(/\d{8}/[^/]+/\d+kb/hls/)', p)
            if m:
                return m.group(1).lower()
            m = re.search(r'(/\d{8}/[^/]+/)', p)
            if m:
                return m.group(1).lower()
        except:
            pass
        return ''

    def _clean_m3u8(self, m3u8_text, m3u8_url='', referer='', skip_seconds=25):
        text = (m3u8_text or '').replace('\r', '')
        if '#EXT-X-STREAM-INF' in text:
            out = []
            last_stream = False
            for raw in text.splitlines():
                line = raw.strip()
                if not line:
                    continue
                if line.startswith('#'):
                    out.append(line)
                    last_stream = line.startswith('#EXT-X-STREAM-INF')
                else:
                    abs_url = urljoin(m3u8_url, line)
                    if last_stream or '.m3u8' in line.lower():
                        out.append(self._proxy_m3u8_url(abs_url, referer or self.host))
                    else:
                        out.append(abs_url)
                    last_stream = False
            return '\n'.join(out) + '\n'

        header, segments, tail, media_sequence, target_duration = self._parse_m3u8_segments(text)
        if not segments:
            return text

        marker = self._main_path_marker(m3u8_url)

        stat = {}
        for seg in segments:
            key = self._segment_host_key(seg['uri'], m3u8_url)
            stat[key] = stat.get(key, 0.0) + float(seg.get('dur') or 0)
        main_key = max(stat.items(), key=lambda x: x[1])[0] if stat else ('', '')
        total_dur = sum(stat.values()) or 0
        main_dur = stat.get(main_key, 0)

        cleaned = []
        removed = 0
        for idx, seg in enumerate(segments):
            key = self._segment_host_key(seg['uri'], m3u8_url)
            is_front = idx < 12
            abs_uri = urljoin(m3u8_url, seg.get('uri', ''))
            is_ad = self._is_ad_segment(seg['uri'], seg.get('dur'))
            if marker and marker not in urlparse(abs_uri).path.lower():
                is_ad = True
            tags_text = '\n'.join(seg.get('tags') or []).upper()
            if is_front and 'METHOD=NONE' in tags_text and marker and marker not in urlparse(abs_uri).path.lower():
                is_ad = True
            if (not is_ad) and is_front and total_dur > 0 and main_dur >= total_dur * 0.6:
                if key != main_key and stat.get(key, 0) <= 90:
                    is_ad = True
            if is_ad:
                removed += 1
                continue
            seg['_idx'] = idx
            cleaned.append(seg)

        if removed == 0 and len(segments) > 4:
            acc = 0.0
            cut = 0
            for idx, seg in enumerate(segments[:12]):
                key = self._segment_host_key(seg['uri'], m3u8_url)
                if key == main_key and acc >= 3:
                    break
                acc += float(seg.get('dur') or target_duration or 3)
                cut = idx + 1
                if acc >= skip_seconds:
                    break
            if cut > 0 and cut < len(segments):
                first_key = self._segment_host_key(segments[0]['uri'], m3u8_url)
                if first_key != main_key:
                    cleaned = segments[cut:]
                    removed = cut

        if not cleaned:
            cleaned = segments
            removed = 0

        new_lines = []
        has_m3u = False
        for line in header:
            if line.startswith('#EXTM3U'):
                has_m3u = True
            if line.startswith('#EXT-X-MEDIA-SEQUENCE') or line.startswith('#EXT-X-START'):
                continue
            if line.startswith('#EXT-X-KEY') and 'METHOD=NONE' in line.upper() and removed > 0:
                continue
            new_lines.append(line)
        if not has_m3u:
            new_lines.insert(0, '#EXTM3U')
        first_idx = cleaned[0].get('_idx', removed) if cleaned else removed
        new_lines.append(f'#EXT-X-MEDIA-SEQUENCE:{media_sequence + first_idx}')

        for seg in cleaned:
            for tag in seg.get('tags') or []:
                if tag.startswith('#EXT-X-KEY') or tag.startswith('#EXT-X-MAP'):
                    tag = re.sub(r'URI="([^"]+)"', lambda m: 'URI="' + urljoin(m3u8_url, m.group(1)) + '"', tag)
                new_lines.append(tag)
            new_lines.append(urljoin(m3u8_url, seg.get('uri', '')))
        if tail:
            for line in tail:
                if line.startswith('#EXT-X-ENDLIST'):
                    new_lines.append(line)
        elif '#EXT-X-ENDLIST' in text:
            new_lines.append('#EXT-X-ENDLIST')
        print(f"[m3u8清洗] 原片段:{len(segments)} 删除广告:{removed} 保留:{len(cleaned)}")
        return '\n'.join(new_lines) + '\n'
