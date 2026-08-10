# -*- coding: utf-8 -*-
"""
藏姬阁
站点: https://藏姬阁.com  (真实域名跳转 https://xn--e2o-gocjgcom-nw8u993cql8elmwejgrb.cjggo.com/)
"""
import sys
import re
import json
import html as ihtml
from urllib.parse import quote, urljoin, unquote

import cloudscraper

try:
    sys.path.append('..')
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider:
        def init(self, extend="'=''"): pass
        def getName(self): return ""
        def homeContent(self, filter): return {'class': [], 'filters': {}}
        def homeVideoContent(self): return {'list': []}
        def categoryContent(self, tid, pg, filter, extend): return {'list': []}
        def detailContent(self, ids): return {'list': []}
        def searchContent(self, key, quick, pg='1'): return {'list': []}
        def playerContent(self, flag, id, vipFlags=None): return {'parse': 0, 'url': id, 'header': {}}


class Spider(BaseSpider):
    name = '藏姬阁'
    HOST = 'https://xn--e2o-gocjgcom-nw8u993cql8elmwejgrb.cjggo.com'

    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.host = self.HOST
        self.timeout = 30
        self.CATEGORIES = (
            ('国产精品', '15'), ('原创偷拍', '13'), ('中文字幕', '20'),
            ('亚洲无码', '70'), ('亚洲有码', '603'), ('欧美精选', '30'),
            ('动漫卡通', '613'),
        )
        self._scraper = None

    def _get_scraper(self):
        if self._scraper is None:
            self._scraper = cloudscraper.create_scraper(
                browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
        return self._scraper

    def getName(self):
        return self.name

    def getDependence(self):
        return ['cloudscraper']

    def homeLayout(self):
        return 0

    def destroy(self):
        try:
            if self._scraper:
                self._scraper.close()
        except Exception:
            pass

    def manualVideoCheck(self):
        return False

    def isVideoFormat(self, url):
        v = str(url or '').lower()
        return any(x in v for x in ('.m3u8', '.mp4', '.m4v', '.mpd', '.flv', '.webm', '.ts'))

    def _request(self, url, params=None, referer=None, post=False, data=None):
        a = self._get_scraper()
        headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'}
        if referer:
            headers['Referer'] = referer
        try:
            if post:
                r = a.post(url, data=data, headers=headers, params=params,
                           timeout=self.timeout, allow_redirects=True)
            else:
                r = a.get(url, headers=headers, params=params,
                          timeout=self.timeout, allow_redirects=True)
            r.encoding = r.apparent_encoding or 'utf-8'
            return r
        except Exception as e:
            self._log('request fail %s: %s' % (url, e))
            return None

    def _log(self, msg):
        try:
            self.log('[%s] %s' % (self.name, msg))
        except Exception:
            print('[%s] %s' % (self.name, msg))

    @staticmethod
    def clean(s):
        return re.sub(r'\s+', ' ', ihtml.unescape(re.sub(r'<[^>]+>', '', s or ''))).strip()

    def _cards(self, html, base_url):
        """解析 item wrap-vid 卡片列表。"""
        vods = []
        # 以 wrap-vid 开头、vid-name 结束定位单个卡片
        for m in re.finditer(
                r'<div class="item wrap-vid[^"]*">(.*?)<h3 class="vid-name">(.*?)</h3>',
                html or '', re.S):
            head, tail = m.group(1), m.group(2)
            link = re.search(r'href="([^"]*/content/(\d+)\.html)"', head + tail)
            if not link:
                continue
            href, vid = link.group(1), link.group(2)
            title_m = re.search(r'title="([^"]*)"', head + tail)
            title = title_m.group(1) if title_m else ''
            if not title:
                tm = re.search(r'<a[^>]*>([^<]+)</a>', tail)
                if tm:
                    title = tm.group(1)
            img = re.search(r"background-image:\s*url\('([^']+)'\)", head + tail) or \
                  re.search(r'data-original="([^"]*)"', head + tail)
            dur = re.search(r'<span class="vodtime">([^<]*)</span>', head + tail)
            vods.append({
                'vod_id': vid,
                'vod_name': self.clean(title),
                'vod_pic': urljoin(base_url, img.group(1)) if img else '',
                'vod_remarks': self.clean(dur.group(1)) if dur else '',
            })
        # 去重
        seen, out = set(), []
        for v in vods:
            k = v['vod_id'] + '|' + v['vod_name']
            if k in seen:
                continue
            seen.add(k)
            out.append(v)
        return out

    def homeContent(self, filter=False):
        classes = [{'type_id': str(i), 'type_name': n} for n, i in self.CATEGORIES]
        return {'class': classes, 'filters': {}}

    def homeVideoContent(self):
        r = self._request(self.host + '/')
        return {'list': self._cards(r.text, r.url if r else self.host + '/') if r else []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        try:
            page = int(pg)
        except (ValueError, TypeError):
            page = 1
        if page < 1:
            page = 1
        url = '%s/list/%s-%s.html' % (self.host, tid, page)
        r = self._request(url)
        if not r:
            return {'list': [], 'page': page, 'pagecount': 1, 'limit': 24, 'total': 0}
        vods = self._cards(r.text, r.url)
        pc = self._pagecount(r.text, tid)
        return {'list': vods, 'page': page, 'pagecount': pc, 'limit': 24, 'total': 0}

    def _pagecount(self, html, tid):
        # 尾页 /list/{tid}-{N}.html
        m = re.search(r'/list/%s-(\d+)\.html">\s*尾页' % re.escape(str(tid)), html)
        if m:
            try:
                return max(1, int(m.group(1)))
            except ValueError:
                pass
        nums = [int(x) for x in re.findall(r'/list/%s-(\d+)\.html' % re.escape(str(tid)), html)]
        return max(nums) if nums else 1

    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, (list, tuple)) and ids else ids or '').strip()
        if not vid:
            return {'list': []}
        r = self._request('%s/content/%s.html' % (self.host, vid))
        if not r:
            return {'list': []}
        return {'list': [self._detail(r.text, vid, r.url)]}

    def _detail(self, html, vid, base_url):
        title = ''
        tm = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html) or re.search(r'<title>...*?([\s\S]*?)</title>', html)
        if tm:
            title = self.clean(tm.group(1))
        if not title or title.startswith('正在播放'):
            tm2 = re.search(r'<h3 class="vid-name"[^>]*>\s*<a[^>]*title="([^"]*)"', html)
            title = self.clean(tm2.group(1)) if tm2 else title
        img = re.search(r"postimg\s*=\s*'([^']+)'", html) or \
              re.search(r"background-image:\s*url\('([^']+)'\)", html) or \
              re.search(r'<img[^>]+(?:src|data-original)="([^"]+\.(?:jpg|png|webp))"', html)
        # 播放地址 mac_url
        play_from = '在线播放'
        play_url = ''
        mu = re.search(r"var\s+mac_url\s*=\s*unescape\('([^']+)'\)", html)
        if mu:
            decoded = unquote(mu.group(1))
            # 形如: 集名$地址#集名$地址
            parts = decoded.split('#')
            pairs = []
            for p in parts:
                if '$' in p:
                    n, u = p.split('$', 1)
                    pairs.append((n.strip(), u.strip()))
            if pairs:
                play_url = '#'.join('%s$%s' % (n, u) for n, u in pairs)
        else:
            # 兜底：直接找 m3u8/mp4
            mu2 = re.search(r'(https?://[^\s\'"]+\.(?:m3u8|mp4|mpd|flv)[^\s\'"]*)', html)
            if mu2:
                play_url = '第1集$%s' % mu2.group(1)
        return {
            'vod_id': vid,
            'vod_name': title or vid,
            'vod_pic': urljoin(base_url or self.host + '/', img.group(1)) if img else '',
            'vod_content': '',
            'vod_type_name': '',
            'vod_play_from': play_from if play_url else '',
            'vod_play_url': play_url,
        }

    def searchContent(self, key, quick=False, pg='1'):
        """站点无显式搜索框；尝试常见路由，失败则从首页兜底含关键词项。"""
        keyword = str(key or '').strip()
        try:
            page = int(pg)
        except (ValueError, TypeError):
            page = 1
        if page < 1:
            page = 1
        vods = []
        found = False
        for path in ['/search.php?searchtype=5&wd=%s' % quote(keyword),
                     '/index.php/vod/search.html?wd=%s' % quote(keyword),
                     '/?wd=%s' % quote(keyword)]:
            r = self._request(self.host + path)
            if r:
                cand = self._cards(r.text, r.url)
                if cand:
                    vods = cand
                    found = True
                    break
        if not found:
            # 从首页筛选标题含关键词
            r = self._request(self.host + '/')
            if r:
                allv = self._cards(r.text, r.url)
                vods = [v for v in allv if keyword in v['vod_name']]
        return {'list': vods, 'page': page, 'pagecount': 1, 'limit': 24, 'total': 0}

    def playerContent(self, flag, id, vipFlags=None):
        url = str(id or '').strip()
        if not url:
            return {'parse': 0, 'url': '', 'header': {}}
        if self.isVideoFormat(url):
            return {'parse': 0, 'url': url,
                    'header': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                               'Referer': self.host + '/'}}
        # id 若是详情地址，回源解析 mac_url
        if re.search(r'/content/\d+\.html', url):
            vid = re.search(r'/content/(\d+)\.html', url).group(1)
            r = self._request('%s/content/%s.html' % (self.host, vid))
            if r:
                mu = re.search(r"var\s+mac_url\s*=\s*unescape\('([^']+)'\)", r.text)
                if mu:
                    decoded = unquote(mu.group(1))
                    mm = re.search(r'(https?://[^\s\'"]+\.(?:m3u8|mp4|mpd|flv)[^\s\'"]*)', decoded)
                    if mm:
                        return {'parse': 0, 'url': mm.group(1),
                                'header': {'User-Agent': 'Mozilla/5.0', 'Referer': self.host + '/'}}
        return {'parse': 1, 'url': url, 'header': {}}


if __name__ == '__main__':
    s = Spider()
    vods = s.categoryContent('15', 1, False, {})
    print('分类15 第1页:', len(vods.get('list', [])), '条 | 总页:', vods.get('pagecount'))
    if vods.get('list'):
        d = s.detailContent([vods['list'][0]['vod_id']])
        print('详情:', d['list'][0]['vod_name'], '|', d['list'][0]['vod_play_url'])
