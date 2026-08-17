# -*- coding: utf-8 -*-
import sys
import re
import json
import time
import base64
import hashlib
import datetime
import requests
from urllib.parse import quote

sys.path.append('..')
try:
    from base.spider import Spider
except ImportError:
    class Spider:
        def fetch(self, url, headers=None, **kw):
            import requests as rq
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r

HOST = "https://apiw2.lhlamp.com/v3/"
HOSTS = ['https://apiw2.lhlamp.com/v3/', 'https://apiw.ygdj8.com/v3/', 'https://apit2.lhlamp.com/v3/', 'https://api.atzxyff.com/v3/']
UA = "okhttp/4.9.2"
SALT = "a@v*9$QAQ"
VIP_TOKEN = ""

CATEGORIES = {
    "hot": "🔥热门", "new": "🆕最新", "rank": "🏆排行榜", "japan": "🇯🇵日本AV",
    "japan_av": "🇯🇵日本AV筛选", "eu_us_studio": "🌍歐美筛选", "ngs_genre": "🇨🇳國產筛选",
    "short_genre": "📱短劇筛选", "bc": "💰乳腺幣", "bonus": "🎁乳腺幣獎勵",
    "btc1": "🤰孕婦專題", "btc2": "📹酒店監控", "btc3": "🍉吃瓜專題", "btc4": "💸裸貸專題",
    "topic": "📌VIP專題", "wumi": "🔞無碼", "wumi_comic": "📚無碼漫畫", "comic_cat": "🗂️漫畫分類",
    "df": "🤖AI換臉", "xc": "🇨🇳XCHINA", "anime": "📺動畫", "comic": "📚漫畫熱門",
    "comic_all": "📚漫畫全部", "actors": "👩演員", "yt": "▶️YouTube", "of": "🔞OnlyFans",
    "ngs": "🎥NGS", "live": "🔴直播",
}

FILTER_TABS = {'japan_av': 'main_screen/popular_classic/japanav', 'ngs_genre': 'main_screen/popular_classic/ngs', 'eu_us_studio': 'yt/hot/videos', 'short_genre': 'yt/hot/videos'}


def _aes_cbc(key, iv, data):
    try:
        from Crypto.Cipher import AES
        c = AES.new(key, AES.MODE_CBC, iv)
        pt = c.decrypt(data)
        p = pt[-1]
        return pt[:-p] if 1 <= p <= 16 and pt[-p:] == bytes([p]) * p else pt
    except Exception:
        pass
    SBOX = bytes.fromhex('637c777bf26b6fc53001672bfed7ab76ca82c97dfa5947f0add4a2af9ca472c0b7fd9326363ff7cc34a5e5f171d8311504c723c31896059a071280e2eb27b27509832c1a1b6e5aa0523bd6b329e32f8453d100ed20fcb15b6acbbe394a4c58cfd0efaafb434d338545f9027f503c9fa851a3408f929d38f5bcb6da2110fff3d2cd0c13ec5f974417c4a77e3d645d197360814fdc222a908846eeb814de5e0bdbe0323a0a4906245cc2d3ac629195e479e7c8376d8dd54ea96c56f4ea657aae08ba78252e1ca6b4c6e8dd741f4bbd8b8a703eb5664803f60e613557b986c11d9ee1f8981169d98e949b1e87e9ce5528df8ca1890dbfe6426841992d0fb054bb16')
    Si = [0] * 256
    for i, b in enumerate(SBOX):
        Si[b] = i
    def gmul(a, b):
        r = 0
        while b:
            if b & 1:
                r ^= a
            a = a << 1 ^ (0x11B if a & 0x80 else 0)
            a &= 255
            b >>= 1
        return r
    M9 = [gmul(i, 9) for i in range(256)]
    M11 = [gmul(i, 11) for i in range(256)]
    M13 = [gmul(i, 13) for i in range(256)]
    M14 = [gmul(i, 14) for i in range(256)]
    Rcon = [1, 2, 4, 8, 16, 32, 64, 128, 27, 54, 108, 216, 171, 77]
    Nk = len(key) // 4
    Nr = Nk + 6
    w = [0] * 4 * (Nr + 1)
    for i in range(Nk):
        w[i] = int.from_bytes(key[i * 4:i * 4 + 4], 'big')
    i = Nk
    while i < 4 * (Nr + 1):
        tmp = w[i - 1]
        if i % Nk == 0:
            tmp = ((tmp << 8) | (tmp >> 24)) & 0xffffffff
            tmp = (SBOX[tmp >> 24] << 24) | (SBOX[(tmp >> 16) & 255] << 16) | (SBOX[(tmp >> 8) & 255] << 8) | SBOX[tmp & 255]
            tmp ^= Rcon[i // Nk - 1] << 24
        elif Nk > 6 and i % Nk == 4:
            tmp = (SBOX[tmp >> 24] << 24) | (SBOX[(tmp >> 16) & 255] << 16) | (SBOX[(tmp >> 8) & 255] << 8) | SBOX[tmp & 255]
        w[i] = w[i - Nk] ^ tmp
        i += 1
    def ar(s, rn):
        for i in range(16):
            s[i] ^= w[rn * 4 + i // 4] >> (24 - i % 4 * 8) & 255
    def ishift(s):
        t = s[:]
        s[0] = t[0]; s[4] = t[4]; s[8] = t[8]; s[12] = t[12]
        s[1] = t[13]; s[5] = t[1]; s[9] = t[5]; s[13] = t[9]
        s[2] = t[10]; s[6] = t[14]; s[10] = t[2]; s[14] = t[6]
        s[3] = t[7]; s[7] = t[11]; s[11] = t[15]; s[15] = t[3]
    def imix(s):
        for c in range(4):
            a0, a1, a2, a3 = s[c * 4], s[c * 4 + 1], s[c * 4 + 2], s[c * 4 + 3]
            s[c * 4] = M14[a0] ^ M11[a1] ^ M13[a2] ^ M9[a3]
            s[c * 4 + 1] = M9[a0] ^ M14[a1] ^ M11[a2] ^ M13[a3]
            s[c * 4 + 2] = M13[a0] ^ M9[a1] ^ M14[a2] ^ M11[a3]
            s[c * 4 + 3] = M11[a0] ^ M13[a1] ^ M9[a2] ^ M14[a3]
    pt = bytearray(data)
    prev = bytearray(iv)
    for blk in range(0, len(pt), 16):
        s = list(pt[blk:blk + 16])
        ar(s, Nr)
        for rnd in range(Nr - 1, 0, -1):
            s = [Si[b] for b in s]
            ishift(s)
            ar(s, rnd)
            imix(s)
        s = [Si[b] for b in s]
        ishift(s)
        ar(s, 0)
        for i in range(16):
            pt[blk + i] = s[i] ^ prev[i]
        prev = bytearray(data[blk:blk + 16])
    p = pt[-1]
    return bytes(pt[:-p]) if 1 <= p <= 16 and pt[-p:] == bytes([p]) * p else bytes(pt)


class Spider(Spider):
    def __init__(self):
        self.host = HOST
        self.token = ''
        self.did = ''
        self._ft = 0
        self._fd = {}
        self._cf = []
        self._cft = 0
        self._seen = set()
        for h in HOSTS:
            try:
                requests.get(h + 'speed_test', timeout=3)
                self.host = h
                break
            except Exception:
                continue
        if not self.did:
            self.did = 'avnight_tvbox'

    def init(self, extend=""):
        return {}

    def _token(self):
        if self.token:
            return self.token
        if VIP_TOKEN:
            self.token = VIP_TOKEN
            return self.token
        def flow(did):
            try:
                h = {'User-Agent': UA, 'Accept': 'application/json'}
                r = requests.get(self.host + '202306/visitor', params={'device_id': did, 'platform': 'android', 'channel_code': 'night'}, headers=h, timeout=8)
                t = r.json().get('token', '')
                if not t:
                    return None, 0
                h['Authorization'] = 'Bearer ' + t
                for path, payload in [('mission/check_in', None), ('draw/start', {'draw_count': 1})]:
                    try:
                        rr = requests.post(self.host + path, json=payload, headers=h, timeout=8)
                        nt = rr.json().get('token', '')
                        if nt:
                            t = nt
                            h['Authorization'] = 'Bearer ' + nt
                    except Exception:
                        pass
                pad = t.split('.')[1] + '=' * (-len(t.split('.')[1]) % 4)
                return t, json.loads(base64.b64decode(pad)).get('vip_till', 0)
            except Exception:
                return None, 0
        t, vt = flow('avnight_tvbox')
        if vt < time.time() + 172800:
            for did in ['avnight_tvbox2', 'avnight_tvbox3']:
                t2, v2 = flow(did)
                if t2 and v2 > vt:
                    t, vt = t2, v2
        if t:
            self.token = t
        return self.token

    def _get(self, path, params=None):
        h = {'User-Agent': UA, 'Accept': 'application/json'}
        t = self._token()
        if t:
            h['Authorization'] = 'Bearer ' + t
        r = requests.get(self.host + path, params=params, headers=h, timeout=15)
        if r.status_code == 401:
            self.token = ''
            h['Authorization'] = 'Bearer ' + self._token()
            r = requests.get(self.host + path, params=params, headers=h, timeout=15)
        return r

    def _post(self, path, body=None, params=None):
        h = {'User-Agent': UA, 'Accept': 'application/json'}
        t = self._token()
        if t:
            h['Authorization'] = 'Bearer ' + t
        r = requests.post(self.host + path, json=body or {}, params=params, headers=h, timeout=15)
        if r.status_code == 401:
            self.token = ''
            h['Authorization'] = 'Bearer ' + self._token()
            r = requests.post(self.host + path, json=body or {}, params=params, headers=h, timeout=15)
        return r

    def _dec(self, text, ts):
        dt = datetime.datetime.utcfromtimestamp(ts + 28800).strftime('%Y%m%d-%H%M%S')
        key = hashlib.md5((SALT + dt).encode()).hexdigest().encode()
        iv = (dt + '#').encode()
        pt = _aes_cbc(key, iv, base64.b64decode(text))
        return json.loads(pt.decode('utf-8', 'replace'))

    def _q(self, k):
        return (0 if str(k).isdigit() else 1, -(int(k) if str(k).isdigit() else 0), str(k))

    def _pic(self, url):
        return 'http://127.0.0.1:9978/proxy?url=' + quote(url) if url else ''

    def _item(self, v):
        act = ','.join([a.get('name', '') for a in v.get('actors', [])])
        tags = ','.join(v.get('tags', [])) if isinstance(v.get('tags'), list) else ''
        return {'vod_id': v.get('code', ''), 'vod_name': v.get('title', ''), 'vod_pic': self._pic(v.get('cover64', '') or v.get('thumb64', '') or v.get('cover', '') or v.get('img64', '')), 'vod_remarks': (tags or v.get('video_type', ''))[:20], 'vod_actor': act[:50]}

    def _batch(self, codes):
        if not codes:
            return []
        try:
            h = {'User-Agent': UA, 'Accept': 'application/json'}
            t = self._token()
            if t:
                h['Authorization'] = 'Bearer ' + t
            r = requests.post(self.host + 'videos/page', json={'codes': codes}, headers=h, timeout=15)
            j = self._dec(r.text.strip(), int(r.headers.get('X-AVNIGHT-TIME', 0)))
            return [d.get('video', d) for d in j.get('data', [])]
        except Exception:
            return []

    def _items(self, vs):
        out = []
        for v in vs:
            if v.get('code'):
                out.append(self._item(v))
        return out

    def _pagecount(self, count, limit=20):
        try:
            return max(1, (int(count) + limit - 1) // limit)
        except Exception:
            return 1

    def _filters(self):
        if time.time() - self._ft < 600:
            return self._fd
        try:
            j = self._get('filter/category').json()
            self._fd = {k: [(g['name'], str(g['sid'])) for g in v] for k, v in j.items()}
            self._ft = time.time()
        except Exception:
            pass
        return self._fd

    def homeContent(self, filter=False):
        classes = [{'type_id': k, 'type_name': v} for k, v in CATEGORIES.items()]
        fs = self._filters()
        for c in classes:
            if c['type_id'] in fs and fs[c['type_id']]:
                c['filters'] = [{'key': 'flt', 'name': '標籤', 'value': [{'n': '全部', 'v': ''}] + [{'n': n, 'v': s} for n, s in fs[c['type_id']]]}, {'key': 'sort', 'name': '排序', 'value': [{'n': '上架時間', 'v': 'onshelf_tm'}, {'n': '人氣', 'v': 'collect_count'}, {'n': '熱度', 'v': 'watch_count'}]}]
        try:
            if time.time() - self._cft > 600:
                j = self._get('comic/category').json()
                self._cf = [(g.get('name', ''), str(g.get('sid', ''))) for g in j.get('comic_genres', [])]
                self._cft = time.time()
            for c in classes:
                if c['type_id'] == 'comic_cat':
                    c['filters'] = [{'key': 'flt', 'name': '題材', 'value': [{'n': '全部', 'v': ''}] + [{'n': n, 'v': s} for n, s in self._cf]}]
        except Exception:
            pass
        return {'class': classes, 'list': [], 'filter': True}

    def homeVideoContent(self):
        return self.categoryContent('new', 1, '', '')

    def categoryContent(self, tid, pg=1, filter=False, extend=""):
        if isinstance(extend, dict):
            extend = '&'.join('%s=%s' % (k, v) for k, v in extend.items())
        extend = str(extend or '')
        pn = 1
        try:
            pn = max(int(str(pg)), 1)
        except Exception:
            pass
        vs = []
        nextc = 1
        tid = str(tid)
        try:
            if tid in ('japan_av', 'eu_us_studio', 'ngs_genre', 'short_genre'):
                sid = ''
                sort = 'onshelf_tm'
                for kv in extend.split('&'):
                    if '=' in kv:
                        k, v = kv.split('=', 1)
                        if k == 'flt':
                            sid = v
                        elif k == 'sort':
                            sort = v
                if sid:
                    j = self._get('filter/category/%s/%s/videos' % (tid, sid), {'page': pn, 'order_by': sort}).json()
                    vs = j.get('videos', [])
                    nextc = j.get('total_pages', 1) or 1
                else:
                    j = self._get(FILTER_TABS[tid]).json()
                    vs = j.get('videos', []) or j.get('data', [])
                    nextc = 1
            elif tid == 'bonus':
                j = self._get('breast_coin_video/bonus').json()
                vs = j.get('breast_coin_video_single', [])
                for c in j.get('breast_coin_video_collection', []):
                    vd = c.get('video_data', [])
                    if isinstance(vd, list):
                        vs += vd
                nextc = 1
            elif tid.startswith('btc'):
                j = self._get('breast_coin_video/' + tid[3:], {'next': '' if str(pn) == '1' else str((int(pn) - 1) * 20)}).json()
                vs = []
                for c in j.get('collections', []):
                    vd = c.get('video_data', [])
                    if isinstance(vd, list):
                        vs += vd
                nextc = pn + 1 if j.get('next') else 1
            elif tid == 'topic':
                j = self._get('vip/topic').json()
                vs = []
                for t in j.get('data', []):
                    tv = t.get('videos', [])
                    if isinstance(tv, list):
                        vs += tv
                nextc = 1
            elif tid == 'bc':
                j = self._get('main_screen/breast_coin_video').json()
                codes = [d.get('code') for d in j.get('data', []) if d.get('code')]
                vs = self._batch(codes[:20])
                nextc = 1
            elif tid == 'wumi':
                j = self._get('vip/wumi/videos').json()
                vs = j.get('videos', [])
                nextc = 1
            elif tid == 'wumi_comic':
                j = self._get('vip/wumi/comics').json()
                vs = j.get('comics', [])
                nextc = 1
            elif tid == 'comic_cat':
                sid = ''
                for kv in (extend or '').split('&'):
                    if kv.startswith('flt='):
                        sid = kv[4:]
                if sid:
                    j = self._get('comic/category/' + sid + '/comics', {'page': pn}).json()
                    vs = j.get('comics', [])
                    nextc = j.get('total_pages', 1) or 1
                else:
                    j = self._get('comic/all').json()
                    vs = j.get('comics', [])
                    nextc = 1
            elif tid == 'actors':
                j = self._post('category/actors', {} if str(pn) == '1' else {'next': str((int(pn) - 1) * 100)}).json()
                lst = []
                for a in j.get('actors', []):
                    if a.get('sid') and a['sid'] not in self._seen:
                        self._seen.add(a['sid'])
                        lst.append({'vod_id': 'ACTOR-' + str(a['sid']), 'vod_name': a.get('name', ''), 'vod_pic': self._pic(a.get('cover64', '')), 'vod_remarks': a.get('actor_type_text', '') or ('%d部' % a.get('video_count', 0)), 'vod_actor': a.get('country', '')})
                return {'list': lst, 'page': pn, 'pagecount': pn + 1 if j.get('next') else 1, 'limit': len(lst), 'total': len(lst)}
            elif tid == 'df':
                j = self._get('main_screen/popular_classic/deepfake_collection').json()
                vs = j.get('data', [])
                nextc = 1
            elif tid == 'xc':
                j = self._get('main_screen/popular_classic/xchina_collection').json()
                vs = j.get('data', [])
                nextc = 1
            elif tid == 'hot':
                j = self._get('yt/hot/videos').json()
                vs = j.get('videos', [])
                nextc = 1
            elif tid == 'new':
                j = self._get('yt/new/videos', {'next': '' if str(pn) == '1' else str((int(pn) - 1) * 20)}).json()
                vs = j.get('videos', [])
                nextc = pn + 1 if j.get('next') else pn
            elif tid == 'rank':
                j = self._get('vip/ranking/videos').json()
                for k in ['niche', 'popularity', 'quality']:
                    vs += j.get(k, [])
                nextc = 1
            elif tid == 'japan':
                j = self._get('main_screen/popular_classic/japanav').json()
                vs = j.get('data', [])
                nextc = 1
            elif tid == 'yt':
                j = self._get('yt/new/videos').json()
                vs = j.get('videos', [])
                nextc = 1
            elif tid == 'of':
                j = self._get('onlyfans/fever/videos').json()
                vs = j.get('videos', [])
                nextc = 1
            elif tid == 'ngs':
                j = self._get('main_screen/popular_classic/ngs').json()
                vs = j.get('data', [])
                nextc = 1
            elif tid == 'anime':
                j = self._get('anime/hot', {'next': '' if str(pn) == '1' else str((int(pn) - 1) * 24)}).json()
                vs = j.get('videos', [])
                nextc = pn + 1 if j.get('next') else 1
            elif tid == 'comic':
                j = self._get('comic/hot').json()
                vs = j.get('comics', [])
                nextc = 1
            elif tid == 'comic_all':
                j = self._get('comic/all').json()
                vs = j.get('comics', [])
                nextc = 1
            elif tid == 'live':
                j = self._get('livebroadcast/videos').json()
                vs = j.get('videos', []) or j.get('data', [])
                lst = []
                for v in vs:
                    if v.get('code'):
                        it = self._item(v)
                        if v.get('source'):
                            it['vod_id'] += '|' + v['source']
                        lst.append(it)
                return {'list': lst, 'page': pn, 'pagecount': 1, 'limit': len(lst), 'total': len(lst)}
        except Exception:
            vs = []
        lst = self._items(vs)
        return {'list': lst, 'page': pn, 'pagecount': nextc, 'limit': len(lst), 'total': len(lst)}

    def detailContent(self, ids):
        if isinstance(ids, list):
            vid = ids[0] if ids else ''
        else:
            vid = str(ids) if ids else ''
        if not vid:
            return {'list': []}
        if '|' in vid:
            c, src = vid.split('|', 1)
            return {'list': [{'vod_id': c, 'vod_name': c, 'vod_pic': '', 'type_name': '直播', 'vod_actor': '', 'vod_director': '', 'vod_year': '', 'vod_area': '', 'vod_remarks': '直播', 'vod_content': '', 'vod_play_from': 'live', 'vod_play_url': '正片$' + src}]}
        code = vid.split('/')[-1]
        if not code:
            return {'list': []}
        if code.startswith('COMIC-') or code.startswith('COMICB-'):
            try:
                c = self._get('comic/content/' + code).json().get('comic', {})
                imgs = [i.get('image') for i in c.get('imgs64', []) if i.get('image')]
                if imgs:
                    au = ','.join([a.get('name', '') for a in c.get('authors', [])])
                    pp = [self._pic(i) for i in imgs]
                    return {'list': [{'vod_id': code, 'vod_name': c.get('title', ''), 'vod_pic': pp[0], 'type_name': '', 'vod_actor': au, 'vod_director': '', 'vod_year': '', 'vod_area': '', 'vod_remarks': '共%dP' % len(imgs), 'vod_content': c.get('title', ''), 'vod_play_from': 'pics', 'vod_play_url': '正片$pics://' + '&&'.join(pp)}]}
            except Exception:
                pass
        if code.startswith('DEEPFAKE-') or code.startswith('XCHINA-'):
            sid = code.split('-')[-1]
            p = 'deepfake/collection/' + sid if code.startswith('DEEPFAKE-') else 'xchina/collection/' + sid
            try:
                c = self._get(p).json().get('collection', {})
                imgs = c.get('imgs64', [])
                if imgs:
                    act = ','.join([a.get('name', '') for a in c.get('actors', [])])
                    pp = [self._pic(i) for i in imgs]
                    return {'list': [{'vod_id': code, 'vod_name': c.get('title', ''), 'vod_pic': pp[0], 'type_name': '', 'vod_actor': act, 'vod_director': '', 'vod_year': '', 'vod_area': '', 'vod_remarks': '', 'vod_content': c.get('title', ''), 'vod_play_from': 'pics', 'vod_play_url': '正片$pics://' + '&&'.join(pp)}]}
            except Exception:
                pass
        if code.startswith('ACTOR-'):
            sid = code.split('-')[-1]
            try:
                j = self._get('actor/' + sid + '/videos').json()
                vs = j.get('videos', [])[:20]
                codes = [v.get('code') for v in vs if v.get('code')]
                play = []
                for d in self._batch(codes):
                    src = d.get('sources', {})
                    u = next((src[k] for k in sorted(src, key=lambda x: (len(x), x)) if isinstance(src[k], str) and '.m3u8' in src[k]), '')
                    if u:
                        play.append((d.get('title', '') or d.get('code', ''), u))
                if play:
                    a = j.get('actor', {})
                    urls = '$$$'.join(['%s$%s' % (t[:20], u) for t, u in play])
                    return {'list': [{'vod_id': code, 'vod_name': (a.get('name', '') or '演員') + '作品合集', 'vod_pic': self._pic(a.get('cover64', '')), 'type_name': '', 'vod_actor': '', 'vod_director': '', 'vod_year': '', 'vod_area': '', 'vod_remarks': '%d部' % len(play), 'vod_content': '', 'vod_play_from': '作品', 'vod_play_url': urls}]}
            except Exception:
                pass
        try:
            r = self._get('video/' + code + '/info')
            ts = int(r.headers.get('X-AVNIGHT-TIME', 0))
            j = self._dec(r.text.strip(), ts)
        except Exception:
            return {'list': []}
        v = j.get('video', {})
        src = j.get('sources', {}) or v.get('sources', {})
        play = []
        for k in sorted(src.keys(), key=lambda x: (len(x), x)):
            u = src[k]
            if isinstance(u, str) and u.startswith('http') and ('.m3u8' in u or '.mp4' in u):
                play.append((k, u))
        froms = '$$$'.join([p[0] for p in play]) or 'line'
        urls = '$$$'.join(['正片$' + p[1] for p in play]) or ('正片$' + '')
        act = ','.join([a.get('name', '') for a in v.get('actors', [])])
        gen = ','.join([g.get('name', '') for g in v.get('genres', [])])
        return {'list': [{'vod_id': code, 'vod_name': v.get('title', ''), 'vod_pic': self._pic(v.get('cover64', '')), 'type_name': gen, 'vod_actor': act, 'vod_director': '', 'vod_year': str(datetime.datetime.utcfromtimestamp(v.get('onshelf_tm', 0) + 28800).year) if v.get('onshelf_tm') else '', 'vod_area': '', 'vod_remarks': ','.join(v.get('tags', [])) if isinstance(v.get('tags'), list) else '', 'vod_content': v.get('content', '') or v.get('title', ''), 'vod_play_from': froms, 'vod_play_url': urls}]}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            pn = max(int(str(pg)), 1)
            params = {'q': key}
            if pn > 1:
                params['next'] = str((pn - 1) * 20)
            j = self._get('search/video', params).json()
            vs = j.get('videos', []) or j.get('data', [])
            total = j.get('total', 0) or 0
            pc = max(1, (total + 19) // 20) if total else pn
            return {'list': self._items(vs), 'page': pn, 'pagecount': pc, 'limit': len(vs), 'total': total}
        except Exception:
            return {'list': []}

    def playerContent(self, flag, id, vipFlags=None):
        url = str(id) if id else str(flag)
        return {'parse': 0, 'url': url}

    def localProxy(self, param):
        try:
            u = param.split('url=', 1)[-1] if 'url=' in param else param
            u = requests.utils.unquote(u)
            r = requests.get(u, headers={'User-Agent': UA}, timeout=10)
            t = r.content.decode('utf-8', 'replace').strip()
            b = None
            for drop in (1, 0):
                try:
                    cand = base64.b64decode(t[drop:])
                    if cand[:4] == b'RIFF' or cand[:2] == b'\xff\xd8' or cand[:8] == b'\x89PNG\r\n\x1a\n' or cand[:3] == b'GIF':
                        b = cand
                        break
                except Exception:
                    continue
            if b is None:
                b = r.content
            if b[:4] == b'RIFF' and b[8:12] == b'WEBP':
                ct = 'image/webp'
            elif b[:2] == b'\xff\xd8':
                ct = 'image/jpeg'
            elif b[:8] == b'\x89PNG\r\n\x1a\n':
                ct = 'image/png'
            elif b[:3] == b'GIF':
                ct = 'image/gif'
            else:
                ct = 'application/octet-stream'
            return {'code': 200, 'header': {'Content-Type': ct, 'Cache-Control': 'max-age=86400'}, 'body': b}
        except Exception:
            return {'code': 404}