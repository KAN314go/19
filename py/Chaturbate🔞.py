# coding: utf-8
import json
import re
from html import unescape
from urllib.parse import quote, urljoin
from base.spider import Spider


class Spider(Spider):
    host = "https://chaturbate.com"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36",
        "Referer": "https://chaturbate.com/",
    }
    categories = [
        ("女性", "female-cams"), ("男性", "male-cams"),
        ("情侣", "couple-cams"), ("变性", "trans-cams"), ("新人", "new-cams"),
        ("游戏", "gaming-cams"), ("熟女", "mature-cams"),
        ("北美", "north-american-cams"), ("南美", "south-american-cams"),
        ("亚洲", "asian-cams"), ("欧洲/俄罗斯", "euro-russian-cams"),
        ("其他地区", "other-region-cams"),
    ]
    category_params = {
        "female-cams": "&genders=f",
        "male-cams": "&genders=m",
        "couple-cams": "&genders=c",
        "trans-cams": "&genders=t",
        "new-cams": "&new_cams=true",
        "gaming-cams": "&gaming=true",
        "mature-cams": "&from_age=50&to_age=100",
        "north-american-cams": "&regions=NA",
        "south-american-cams": "&regions=SA",
        "asian-cams": "&regions=AS",
        "euro-russian-cams": "&regions=ER",
        "other-region-cams": "&regions=O",
    }

    def init(self, extend=''):
        self.host = "https://chaturbate.com"

    def _get(self, url):
        try:
            response = self.fetch(url, headers=self.headers)
            if isinstance(response, str):
                return response
            text = getattr(response, "text", None)
            if text is not None:
                return text
            content = getattr(response, "content", None)
            if isinstance(content, bytes):
                return content.decode("utf-8", "ignore")
            if content is not None:
                return str(content)
            return str(response)
        except Exception:
            return ""

    @staticmethod
    def _clean(s):
        return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()

    def _api_rooms(self, page=1, params=''):
        offset = max(0, int(page or 1) - 1) * 90
        url = self.host + "/api/ts/roomlist/room-list/?limit=90&offset=%d&require_fingerprint=false%s" % (offset, params)
        data = self._get(url)
        if isinstance(data, dict):
            return data
        try:
            return json.loads(data or "{}")
        except Exception:
            return {}

    def _api_cards(self, data):
        result = []
        for room in (data or {}).get("rooms", []):
            name = str(room.get("username") or "").strip()
            if not name:
                continue
            subject = self._clean(room.get("subject") or room.get("room_subject") or "")
            viewers = room.get("num_users")
            pic = "https://thumb.live.mmcdn.com/ri/%s.jpg" % name
            result.append({
                "vod_id": name, "vod_name": name, "vod_pic": pic,
                "vod_remarks": "%s 人" % viewers if viewers is not None else "",
                "vod_content": subject,
            })
        return result

    def _cards(self, html):
        result, seen = [], set()
        blocks = re.findall(r'<li[^>]+class="[^"]*RoomCard[^>]*>(.*?)</li>', html or '', re.S | re.I)
        for block in blocks:
            m = re.search(r'href="/([A-Za-z0-9_]+)/(?:"|\s)', block)
            if not m:
                continue
            name = m.group(1)
            if name in seen:
                continue
            seen.add(name)
            pic = ''
            pm = re.search(r'<img[^>]+(?:src|data-src)="([^"]+)"', block, re.I)
            if pm:
                pic = urljoin(self.host, pm.group(1))
            sm = re.search(r'class="[^"]*RoomCardSubject[^"]*"[^>]*>(.*?)</ul>', block, re.S | re.I)
            subject = self._clean(sm.group(1)) if sm else ''
            vm = re.search(r'class="(?:time|viewers)[^"]*"[^>]*>(.*?)</', block, re.S | re.I)
            viewers = self._clean(vm.group(1)) if vm else ''
            result.append({
                "vod_id": name, "vod_name": name, "vod_pic": pic,
                "vod_remarks": viewers, "vod_content": subject,
            })
        return result

    def homeContent(self, filter):
        return {"class": [{"type_id": x[1], "type_name": x[0]} for x in self.categories], "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg or 1)
        params = self.category_params.get(tid, '')
        data = self._api_rooms(page, params)
        items = self._api_cards(data)
        total = int(data.get("total_count") or 0)
        pagecount = max(1, (total + 89) // 90) if total else 1
        return {"list": items, "page": page, "pagecount": pagecount, "limit": len(items), "total": total}

    def searchContent(self, key, quick, pg='1'):
        page = int(pg or 1)
        url = self.host + '/api/ts/roomlist/room-list/?limit=90&offset=%d&require_fingerprint=false&q=%s' % (max(0, page - 1) * 90, quote(key, safe=''))
        data = self._get(url)
        if not isinstance(data, dict):
            try:
                data = json.loads(data or '{}')
            except Exception:
                data = {}
        items = self._api_cards(data)
        total = int(data.get("total_count") or 0)
        pagecount = max(1, (total + 89) // 90) if total else 1
        return {"list": items, "page": page, "pagecount": pagecount, "limit": len(items), "total": total}

    def detailContent(self, ids):
        room = str(ids[0] if isinstance(ids, list) else ids).strip('/')
        html = self._get(self.host + '/' + room + '/')
        title = room
        tm = re.search(r'<title[^>]*>(.*?)</title>', html or '', re.S | re.I)
        if tm:
            title = self._clean(tm.group(1)).split(' - ')[0].strip() or room
        pic = 'https://thumb.live.mmcdn.com/ri/%s.jpg' % room
        im = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', html or '', re.I)
        if im:
            pic = re.sub(r"/(?:riw|r|thumb)/", "/ri/", urljoin(self.host, im.group(1)))
        desc = ''
        dm = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]*)"', html or '', re.I)
        if dm:
            desc = unescape(dm.group(1))
        sources = self._resolution_sources(room, html)
        if sources:
            play_from = '$$$'.join(x[0] for x in sources)
            play_url = '$$$'.join(x[1] for x in sources)
        else:
            play_from, play_url = '直播间', '进入直播间$' + self.host + '/' + room + '/'
        return {"list": [{"vod_id": room, "vod_name": title, "vod_pic": pic,
            "vod_content": desc, "vod_play_from": play_from, "vod_play_url": play_url}]}

    def playerContent(self, flag, id, vipFlags):
        value = str(id or '').strip()
        if '|' in value:
            room, resolution = value.split('|', 1)
        else:
            room, resolution = value.strip('/').split('/')[-1], ''
        room = room.strip('/')
        html = self._get(self.host + '/' + room + '/')
        stream = self._hls_source(html)
        if stream and resolution:
            selected = self._select_variant(self._hls_variants(stream), resolution)
            if selected:
                stream = selected
        if stream:
            return {"parse": 0, "url": stream, "header": {
                "User-Agent": self.headers["User-Agent"], "Referer": self.host + '/' + room + '/', "Origin": self.host}}
        return {"parse": 1, "url": self.host + '/' + room + '/', "header": self.headers}

    def _hls_source(self, html):
        m = re.search(r'hls_source\\u0022:\s*\\u0022(.*?)\\u0022', html or '', re.S)
        if not m:
            return ''
        try:
            return m.group(1).encode('utf-8').decode('unicode_escape').replace('\\/', '/')
        except Exception:
            return m.group(1).replace('\\u002d', '-').replace('\\u003d', '=').replace('\\u0026', '&').replace('\\/', '/')

    def _hls_variants(self, master):
        text = self._get(master)
        if '#EXTM3U' not in text:
            return []
        result, pending = [], ''
        for line in text.replace('\r', '').split('\n'):
            line = line.strip()
            if line.startswith('#EXT-X-STREAM-INF:'):
                pending = line
            elif pending and line and not line.startswith('#'):
                match = re.search(r'RESOLUTION=\d+x(\d+)', pending, re.I)
                result.append((match.group(1) if match else '', urljoin(master, line)))
                pending = ''
        return result

    @staticmethod
    def _select_variant(variants, resolution):
        target = str(resolution or '').lower().replace('p', '').strip()
        for height, url in variants:
            if height == target:
                return url
        return ''

    def _resolution_sources(self, room, html):
        stream = self._hls_source(html)
        variants = self._hls_variants(stream) if stream else []
        variants.sort(key=lambda item: int(item[0] or 0), reverse=True)
        return [(height + 'P', '播放$' + room + '|' + height + 'p') for height, url in variants if height]

    def isVideoFormat(self, url):
        return False
