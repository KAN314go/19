"""
@header({
  searchable: 1,
  filterable: 0,
  quickSearch: 1,
  title: '小涩界',
  lang: 'hipy',
})
"""

import re
import json
import html
from urllib.parse import urljoin, quote, unquote

try:
    import requests
except Exception:
    requests = None

from base.spider import Spider


class Spider(Spider):
    host = 'https://se.xiaosejie73.xyz'
    ua = 'Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36'

    def __init__(self, *args, **kwargs):
        self.t4_api = kwargs.get('t4_api', '')
        self.extend = ''
        self.s = requests.Session() if requests else None
        if self.s:
            self.s.headers.update({'User-Agent': self.ua, 'Referer': self.host + '/'})

    def init(self, extend=''):
        self.extend = extend
        return '{}'

    def getName(self):
        return '小涩界'

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False

    def destroy(self):
        if self.s:
            self.s.close()

    def _get(self, url):
        if self.s:
            r = self.s.get(url, timeout=20)
            r.encoding = r.apparent_encoding or 'utf-8'
            return r.text
        from urllib.request import Request, urlopen
        return urlopen(Request(url, headers={'User-Agent': self.ua, 'Referer': self.host + '/'}), timeout=20).read().decode('utf-8', 'ignore')

    def _clean(self, s):
        return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s or ''))).strip()

    def _href(self, h):
        return urljoin(self.host, html.unescape(h or '').replace('\\/', '/'))

    def _pic(self, block):
        m = re.search(r"(?:data-src|data-lazy-src|data-original|src)=['\"]([^'\"]+)", block, re.I)
        if m:
            return self._href(m.group(1))
        m = re.search(r"background-image\s*:\s*url\((['\"]?)([^)'\"]+)\1\)", block, re.I)
        return self._href(m.group(2)) if m else ''

    def _items(self, text):
        out, seen = [], set()
        blocks = re.findall(r'<dl[^>]+class=["\'][^"\']*vod-item[^"\']*["\'].*?</dl>', text, re.I | re.S)
        for b in blocks:
            hm = re.search(r'<a[^>]+href=["\']([^"\']*?/vodplay/[^"\']*)["\']', b, re.I)
            if not hm:
                continue
            u = self._href(hm.group(1))
            if u in seen:
                continue
            title = ''
            tm = re.search(r'<dd[^>]*>(.*?)</dd>', b, re.I | re.S)
            if tm:
                title = self._clean(tm.group(1))
            if not title:
                am = re.search(r'<img[^>]+alt=["\']([^"\']+)', b, re.I)
                title = self._clean(am.group(1)) if am else unquote(u.rstrip('/').split('/')[-1])
            pic = self._pic(b)
            rm = re.search(r'<span[^>]+class=["\'][^"\']*(?:pic-text|text-right|remarks?)[^"\']*["\']>(.*?)</span>', b, re.I | re.S)
            remark = self._clean(rm.group(1)) if rm else ''
            out.append({'vod_id': u, 'vod_name': title, 'vod_pic': pic, 'vod_remarks': remark})
            seen.add(u)
        return out

    def _cats(self):
        t = self._get(self.host + '/')
        cats, seen = [], set()
        skip = {'首页', '登录', '注册', '会员', '充值', 'APP', '下载', '搜索', '排行', '最新', '热门', '专题', '资讯', '留言', '求片'}
        for m in re.finditer(r'<a[^>]+href=["\']([^"\']*/vodtype/[^"\']*)["\'][^>]*>(.*?)</a>', t, re.I | re.S):
            u = self._href(m.group(1))
            name = self._clean(m.group(2))
            if not name or name in skip or u in seen:
                continue
            cats.append({'type_id': u, 'type_name': name})
            seen.add(u)
        return cats

    def homeContent(self, filter=None):
        return {'class': self._cats(), 'filters': {}}

    def homeVideoContent(self):
        return {'list': self._items(self._get(self.host + '/'))}

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        u = tid if str(tid).startswith('http') else self._href(str(tid))
        u = u.rstrip('/') + '/'
        if str(pg) != '1':
            if re.search(r'-\d+/$', u):
                u = re.sub(r'-\d+/$', '-' + str(pg) + '/', u)
            else:
                u = u.rstrip('/') + '-' + str(pg) + '/'
        t = self._get(u)
        items = self._items(t)
        total = 0
        m = re.search(r'class=["\'][^"\']*mac_total[^"\']*["\'][^>]*>\s*(\d+)', t)
        if not m:
            m = re.search(r'\.mac_total"\)\.text\(["\'](\d+)["\']\)', t)
        if m:
            total = int(m.group(1))
        nums = [int(x) for x in re.findall(r'/vodtype/[^/]+-(\d+)/', t)]
        pagecount = max(nums) if nums else (2 if len(items) >= 30 else 1)
        return {'page': int(pg), 'pagecount': pagecount, 'limit': len(items), 'total': total, 'list': items}

    def searchContent(self, key, quick=False, pg='1'):
        u = self.host + '/vodsearch/' + quote(str(key)) + '----------' + str(pg) + '---/'
        t = self._get(u)
        items = self._items(t)
        return {'page': int(pg), 'pagecount': 1, 'limit': len(items), 'total': len(items), 'list': items}

    def detailContent(self, ids):
        u = ids[0] if isinstance(ids, (list, tuple)) else str(ids)
        u = self._href(u)
        t = self._get(u)
        title = ''
        m = re.search(r'<title>(.*?)</title>', t, re.I | re.S)
        if m:
            title = self._clean(m.group(1)).split(' - ')[0]
        if not title:
            hm = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*</script>', t, re.I | re.S)
            if hm:
                try:
                    obj = json.loads(hm.group(1))
                    title = obj.get('vod_data', {}).get('vod_name', '')
                except Exception:
                    pass
        pic = ''
        pm = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', t, re.I)
        if pm:
            pic = self._href(pm.group(1))
        content = ''
        cm = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', t, re.I)
        if cm:
            content = self._clean(cm.group(1))
        play_url = u
        fm = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*</script>', t, re.I | re.S)
        if fm:
            try:
                obj = json.loads(fm.group(1))
                if obj.get('url'):
                    play_url = u
                    if not title:
                        title = obj.get('vod_data', {}).get('vod_name', '') or title
            except Exception:
                pass
        if not title:
            title = unquote(u.rstrip('/').split('/')[-1])
        return {'list': [{'vod_id': u, 'vod_name': title, 'vod_pic': pic, 'vod_content': content, 'vod_play_from': '小涩界', 'vod_play_url': '正片$' + play_url}]}

    def playerContent(self, flag, id, vipFlags=None):
        url = id
        page_url = ''
        if str(id).startswith('http') and ('/vodplay/' in id or not re.search(r'\.(?:mp4|m3u8|flv|m4v)(?:$|[?#])', id, re.I)):
            page_url = id
            try:
                t = self._get(id)
                m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\})\s*</script>', t, re.I | re.S)
                if m:
                    obj = json.loads(m.group(1))
                    if obj.get('url'):
                        url = self._href(obj.get('url'))
            except Exception:
                pass
        return {'parse': 0 if re.search(r'\.(?:mp4|m3u8|flv|m4v)(?:$|[?#])', str(url), re.I) else 1, 'jx': 0, 'playUrl': '', 'url': url, 'header': 'User-Agent: %s\r\nReferer: %s' % (self.ua, page_url or self.host + '/')}
