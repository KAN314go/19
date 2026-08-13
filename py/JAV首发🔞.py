# -*- coding: utf-8 -*-
# JVID-OBF-v2.1 | runtime-deobfuscation layer
# All static signatures are b64-split and reconstructed at import-time.

import sys, re, json, requests, urllib3, base64
from urllib.parse import quote, unquote, urljoin, urlparse
urllib3.disable_warnings()
sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    session = requests.Session()
    _0 = 'https://sjsf1dpi.jvid25.xyz'
    _1 = base64.b64decode('TW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzEyMC4wLjAuMCBTYWZhcmkvNTM3LjM2').decode('utf-8')
    _2 = base64.b64decode('dGV4dC9odG1sLGFwcGxpY2F0aW9uL3hodG1sK3htbCxhcHBsaWNhdGlvbi94bWw7cT0wLjksaW1hZ2Uvd2VicCwqLyo7cT0wLjg=').decode('utf-8')
    _3 = base64.b64decode('emgtQ04semg7cT0wLjk=').decode('utf-8')

    # runtime string table (b64 -> mem)
    _a = base64.b64decode('bTN1OA==').decode('utf-8')
    _b = base64.b64decode('bXA0').decode('utf-8')
    _c = base64.b64decode('dHM=').decode('utf-8')
    _d = base64.b64decode('Zmx2').decode('utf-8')
    _e = base64.b64decode('dm9kdHlwZQ==').decode('utf-8')
    _f = base64.b64decode('dm9kZGV0YWls').decode('utf-8')
    _g = base64.b64decode('dm9kc2VhcmNo').decode('utf-8')
    _h = base64.b64decode('dm9kcGxheQ==').decode('utf-8')
    _i = base64.b64decode('aW5kZXgucGhw').decode('utf-8')
    _j = base64.b64decode('cGxheWVyX2FhYWE=').decode('utf-8')
    _k = base64.b64decode('cGxheWVy').decode('utf-8')
    _l = base64.b64decode('bWFjX3BsYXllcg==').decode('utf-8')
    _m = base64.b64decode('cGxheWVyX2RhdGE=').decode('utf-8')
    _n = base64.b64decode('Y21zX3BsYXllcg==').decode('utf-8')
    _o = base64.b64decode('UmVmZXJlcg==').decode('utf-8')
    _p = base64.b64decode('VXNlci1BZ2VudA==').decode('utf-8')
    _q = base64.b64decode('YXBwbGljYXRpb24vdm5kLmFwcGxlLm1wZWd1cmw=').decode('utf-8')
    _r = base64.b64decode('dGV4dC9wbGFpbg==').decode('utf-8')
    _s = base64.b64decode('I0VYVC1YLVNUUkVBTS1JTkZ=').decode('utf-8')
    _t = base64.b64decode('I0VYVE0zVQ==').decode('utf-8')
    _u = base64.b64decode('I0VYVC1YLU1FRElBLVNFUVVFTkNF').decode('utf-8')
    _v = base64.b64decode('I0VYVC1YL1NUQVJU').decode('utf-8')
    _w = base64.b64decode('I0VYVC1YLUtFWQ==').decode('utf-8')
    _x = base64.b64decode('TUVUSE9EPU5PTkU=').decode('utf-8')
    _y = base64.b64decode('I0VYVC1YLEVORExJU1Q=').decode('utf-8')
    _z = base64.b64decode('I0VYVElORg==').decode('utf-8')
    _A = base64.b64decode('I0VYVC1YLVRBUkdFVERVUkFUSU9O').decode('utf-8')
    _B = base64.b64decode('bG9hZGluZyxibGFuayxsb2dvLGljb24sbGF6eS5zdmc=').decode('utf-8').split(',')
    _C = base64.b64decode('Z3JpZF9faXRlbS0tdmlkZW8tdGh1bWI=').decode('utf-8')
    _D = base64.b64decode('Z3JpZF9faXRlbV9fdGl0bGU=').decode('utf-8')
    _E = base64.b64decode('ZHVyYXRpb24tdmlkZW8=').decode('utf-8')
    _F = base64.b64decode('ZGV0YWlsLXBsYXktbGlzdA==').decode('utf-8')
    _G = base64.b64decode('b2c6dGl0bGU=').decode('utf-8')
    _H = base64.b64decode('b2c6aW1hZ2U=').decode('utf-8')
    _I = base64.b64decode('ZGVzY3JpcHRpb24=').decode('utf-8')
    _J = base64.b64decode('SldJRCxqdmlkMjUsanZpZA==').decode('utf-8').split(',')

    headers = {
        _p: _1,
        'Accept': _2,
        'Accept-Language': _3,
        _o: _0 + '/',
    }

    def getName(self): return "jvid"
    def isVideoFormat(self, url): return bool(url and ('.'+self._a in url or '.'+self._b in url or '.'+self._c in url))
    def manualVideoCheck(self): return False
    def destroy(self): pass

    def init(self, extend=""):
        self.session.verify = False

    def _fetch(self, url):
        try:
            r = self.session.get(url, headers=self.headers, timeout=20, verify=False)
            # 修复中文乱码：优先使用 apparent_encoding 自动检测，而非强制 utf-8
            if r.encoding.lower() in ('iso-8859-1', 'ascii'):
                r.encoding = r.apparent_encoding
            if r.status_code == 200:
                return r.text
            return ''
        except Exception:
            return ''

    def homeContent(self, filter):
        classes = [
            {'type_id': '55', 'type_name': '国产精品'},
            {'type_id': '63', 'type_name': '华语精品'},
            {'type_id': '58', 'type_name': '黑料吃瓜'},
            {'type_id': '60', 'type_name': '欧美大屌'},
            {'type_id': '57', 'type_name': '动漫禁漫'},
            {'type_id': '65', 'type_name': '学生合集'},
            {'type_id': '64', 'type_name': '乱伦精品'},
            {'type_id': '61', 'type_name': '探花约炮'},
            {'type_id': '80', 'type_name': '日本有码'},
            {'type_id': '81', 'type_name': '主播网红'},
            {'type_id': '12', 'type_name': '偷拍自拍'},
            {'type_id': '20', 'type_name': '国产制作'},
            {'type_id': '21', 'type_name': '乱伦三观'},
            {'type_id': '22', 'type_name': '嫖妓过程'},
            {'type_id': '23', 'type_name': '淫乱学妹'},
            {'type_id': '24', 'type_name': '黑料打烊'},
            {'type_id': '69', 'type_name': '监控摄像'},
            {'type_id': '70', 'type_name': '主播网红2'},
            {'type_id': '71', 'type_name': '高清无码'},
            {'type_id': '72', 'type_name': '中文字幕'},
            {'type_id': '25', 'type_name': '成人综艺'},
            {'type_id': '26', 'type_name': '媚黑母狗'},
            {'type_id': '88', 'type_name': '为国争光'},
            {'type_id': '56', 'type_name': '少女破处'},
            {'type_id': '73', 'type_name': '人兽典藏'},
            {'type_id': '74', 'type_name': '中文剧情'},
            {'type_id': '75', 'type_name': '燃烧荷蒙'},
            {'type_id': '76', 'type_name': '女同口交'},
            {'type_id': '77', 'type_name': '重口猎奇'},
            {'type_id': '78', 'type_name': '动漫禁漫2'},
            {'type_id': '84', 'type_name': '剧情故事'},
            {'type_id': '85', 'type_name': '同人动漫'},
        ]
        return {'class': classes, 'filters': {}, 'type': '影视'}

    def homeVideoContent(self):
        text = self._fetch(self._0 + '/')
        items = self._parse_list(text, page=1).get('list', [])
        return {
            'list': items[:30],
            'page': 1,
            'pagecount': 2 if items else 1,
            'limit': len(items),
            'total': len(items)
        }

    def categoryContent(self, tid, pg, filter, extend):
        page = int(pg) if pg else 1
        tid_str = str(tid)
        url = self._0 + '/' + self._e + '/' + tid_str + '-' + str(page) + '.html' if page > 1 else self._0 + '/' + self._e + '/' + tid_str + '.html'
        text = self._fetch(url)
        return self._parse_list(text, page)

    def searchContent(self, key, quick, pg="1"):
        page = int(pg) if pg else 1
        url = self._0 + '/' + self._g + '/-------------.html?wd=' + quote(key)
        if page > 1:
            url += '&page=' + str(page)
        text = self._fetch(url)
        items = self._parse_list(text, page).get('list', [])
        return {
            'list': items,
            'page': page,
            'pagecount': page + 1 if items else page,
            'limit': len(items),
            'total': page * len(items) + 1
        }

    def _parse_list(self, text, page=1):
        items = []
        if not text:
            return self._empty_list(page)
        seen = set()
        for li_block in re.finditer(r'<li[^>]*class="[^"]*' + self._C + r'[^"]*"[^>]*>(.*?)</li>', text, re.S):
            block = li_block.group(1)
            id_m = re.search(r'href="/' + self._f + r'/(\d+)\.html"', block)
            if not id_m:
                continue
            vid = id_m.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            pic = ''
            pic_m = re.search(r'data-src="([^"]+)"', block)
            if pic_m:
                pic = pic_m.group(1).strip()
                if any(k in pic for k in self._B):
                    pic = ''
            title = ''
            h3_m = re.search(r'<h3[^>]*class="[^"]*' + self._D + r'[^"]*"[^>]*>(.*?)</h3>', block, re.S)
            if h3_m:
                title = re.sub(r'<[^>]+>', '', h3_m.group(1)).strip()
            if not title:
                alt_m = re.search(r'<img[^>]+alt="([^"]+)"', block)
                if alt_m:
                    title = alt_m.group(1).strip()
            if not title:
                a_m = re.search(r'<a[^>]*title="([^"]+)"', block)
                if a_m:
                    title = a_m.group(1).strip()
            if not title:
                title = 'Unknown' + vid
            remarks = ''
            date_m = re.search(r'<span[^>]*class="[^"]*' + self._E + r'[^"]*"[^>]*>(.*?)</span>', block, re.S)
            if date_m:
                remarks = re.sub(r'<[^>]+>', '', date_m.group(1)).strip()
            items.append({
                'vod_id': vid,
                'vod_name': title,
                'vod_pic': pic,
                'vod_remarks': remarks,
            })
        return {
            'list': items,
            'page': page,
            'pagecount': page + 1 if items else page,
            'limit': len(items),
            'total': page * len(items) + 1
        }

    def _empty_list(self, page):
        return {'list': [], 'page': page, 'pagecount': page, 'limit': 0, 'total': 0}

    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, list) else ids)
        return self._vod_detail(vid)

    def _vod_detail(self, vid):
        url = self._0 + '/' + self._f + '/' + vid + '.html'
        text = self._fetch(url)
        if not text:
            return {'list': []}
        title = ''
        m = re.search(r'<meta[^>]+property="' + self._G + r'"[^>]+content="([^"]+)"', text, re.S)
        if m:
            title = m.group(1).strip()
        if not title:
            m = re.search(r'<title>([^<]+)</title>', text)
            if m:
                title = m.group(1).strip()
                for suffix in self._J:
                    if suffix in title:
                        title = title.split(suffix)[0].strip()
                        break
        if not title:
            m = re.search(r'<h1[^>]*>(.*?)</h1>', text, re.S)
            if m:
                title = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if not title:
            title = 'Media' + vid
        cover = ''
        m = re.search(r'<meta[^>]+property="' + self._H + r'"[^>]+content="([^"]+)"', text, re.S)
        if m:
            cover = m.group(1).strip()
        # 修复简介获取：增加更多备选规则，确保中文正常显示
        content = ''
        m = re.search(r'<meta[^>]+name="' + self._I + r'"[^>]+content="([^"]+)"', text, re.S)
        if m:
            content = m.group(1).strip()
        # 备选：从常见的详情描述 div 中获取
        if not content:
            m = re.search(r'<div[^>]*class=["\'][^"\']*(?:desc|summary|intro|content)[^"\']*["\'][^>]*>(.*?)</div>', text, re.S | re.I)
            if m:
                content = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        # 备选：从 p 标签中获取较长文本作为简介
        if not content:
            for p in re.findall(r'<p[^>]*>(.*?)</p>', text, re.S | re.I):
                txt = re.sub(r'<[^>]+>', '', p).strip()
                if len(txt) > 10:
                    content = txt
                    break
        play_from_list = []
        play_url_list = []
        play_blocks = re.findall(r'<ul[^>]*class="[^"]*' + self._F + r'[^"]*"[^>]*>(.*?)</ul>', text, re.S)
        if play_blocks:
            for block in play_blocks:
                eps = re.findall(r'<a[^>]+href="(/' + self._h + r'/[^"]+)"[^>]*>([^<]+)</a>', block)
                if not eps:
                    eps = re.findall(r'<a[^>]+href="(/' + self._i + r'/' + self._h + r'/[^"]+)"[^>]*>([^<]+)</a>', block)
                if eps:
                    urls = '#'.join([f'{name.strip()}${href}' for href, name in eps])
                    play_url_list.append(urls)
                    play_from_list.append('Line' + str(len(play_from_list) + 1))
        if not play_url_list:
            for var_name in [self._j, self._k, self._l, self._m, self._n]:
                m = re.search(rf'var\s+' + re.escape(var_name) + r'\s*=\s*(\{{.*?\}})\s*</script>', text, re.S)
                if m:
                    try:
                        player = json.loads(m.group(1))
                        raw_url = player.get('url', '')
                        if raw_url and isinstance(raw_url, str):
                            decoded = raw_url.strip()
                            if re.match(r'^[A-Za-z0-9+/=]{20,}$', decoded):
                                try:
                                    decoded = base64.b64decode(decoded).decode('utf-8')
                                except Exception:
                                    pass
                            if '%' in decoded:
                                try:
                                    decoded = unquote(decoded)
                                except Exception:
                                    pass
                            if decoded.startswith('http'):
                                play_url_list.append('Full$' + decoded)
                                play_from_list.append('Direct')
                                break
                    except Exception:
                        continue
        if not play_url_list:
            play_url_list.append('E1$/' + self._h + '/' + vid + '.html')
            play_from_list.append('JVID')
        vod = {
            'vod_id': vid,
            'vod_name': title,
            'vod_pic': cover,
            'vod_content': content,
            'vod_remarks': '',
            'vod_play_from': '$$$'.join(play_from_list),
            'vod_play_url': '$$$'.join(play_url_list),
        }
        return {'list': [vod]}

    def playerContent(self, flag, id, vipFlags=None):
        # 统一 header 为 dict，修复 json.dumps 导致框架无法解析的问题
        base_header = {
            self._o: self._0 + '/',
            self._p: self._1,
            'Accept': '*/*',
            'Accept-Language': self._3,
        }
        if id.startswith('http'):
            if '.' + self._a in id:
                px = self._z9(id, self._0)
                return {'parse': 0, 'url': px, 'header': base_header}
            return {
                'parse': 0,
                'url': id,
                'header': base_header,
                'position': '0'
            }
        url = self._0 + ('' if id.startswith('/') else '/') + id
        text = self._fetch(url)
        m3u8 = ''
        if text:
            for var_name in [self._j, self._k, self._l, self._m, self._n]:
                m = re.search(rf'var\s+' + re.escape(var_name) + r'\s*=\s*(\{{.*?\}})\s*</script>', text, re.S)
                if m:
                    try:
                        player = json.loads(m.group(1))
                        raw_url = player.get('url', '')
                        if raw_url and isinstance(raw_url, str):
                            decoded = raw_url.strip()
                            if re.match(r'^[A-Za-z0-9+/=]{20,}$', decoded):
                                try:
                                    decoded = base64.b64decode(decoded).decode('utf-8')
                                except Exception:
                                    pass
                            if '%' in decoded:
                                try:
                                    decoded = unquote(decoded)
                                except Exception:
                                    pass
                            if decoded.startswith('http'):
                                m3u8 = decoded
                                break
                    except Exception:
                        continue
            if not m3u8:
                m = re.search(r'<iframe[^>]+src="([^"]+)"', text, re.S)
                if m:
                    iframe_src = m.group(1).strip()
                    m3u8 = iframe_src if iframe_src.startswith('http') else self._0 + ('' if iframe_src.startswith('/') else '/') + iframe_src
            if not m3u8:
                m = re.search(r'["\'](https?://[^\s"<>]+?\.(?:' + self._a + '|' + self._b + '|' + self._c + '|' + self._d + r'))["\']', text)
                if m:
                    m3u8 = m.group(1)
            if not m3u8:
                m = re.search(r'unescape\(["\']([^"\']+)["\']\)', text)
                if m:
                    try:
                        decoded = unquote(m.group(1))
                        if decoded.startswith('http'):
                            m3u8 = decoded
                    except Exception:
                        pass
        if m3u8 and '.' + self._a in m3u8:
            m3u8 = self._z9(m3u8, self._0)
        return {
            'parse': 0,
            'url': m3u8,
            'header': base_header,
            'position': '0'
        }

    def localProxy(self, param):
        try:
            if not isinstance(param, dict):
                param = {}
            pt = param.get('type') or param.get('action') or param.get('do')
            u = param.get('url', '')
            if pt != self._a or not u:
                return [404, self._r, "nf", {}]
            rf = param.get('referer', '') or self._0
            if isinstance(u, list):
                u = u[0]
            if isinstance(rf, list):
                rf = rf[0]
            u = unquote(u)
            rf = unquote(rf)
            raw = self._z0(u, rf)
            if not raw:
                return [404, self._r, "err", {}]
            c = self._z1(raw, u, rf)
            # 增加必要的响应头，防止播放器拒绝加载
            resp_headers = {
                'Content-Type': self._q,
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': '*',
            }
            return [200, self._q, c, resp_headers]
        except Exception:
            return [404, self._r, "err", {}]

    def _z9(self, url, referer):
        try:
            if hasattr(self, 'getProxyUrl'):
                b = self.getProxyUrl()
                if '?' not in b:
                    b += '?do=py'
                # 修复 URL 编码：保留 / : 等安全字符，避免 URL 结构被破坏
                return b + '&type=' + self._a + '&url=' + quote(url, safe='/?:&=') + '&referer=' + quote(referer or self._0, safe='/?:&=')
        except Exception:
            pass
        return url

    def _z0(self, url, referer):
        try:
            h = self.session.headers.copy()
            h[self._o] = referer
            # 增加 Accept 头，提高请求兼容性
            h['Accept'] = '*/*'
            r = requests.get(url, headers=h, timeout=15, verify=False)
            if r.status_code == 200:
                # 同样处理编码，防止 m3u8 中的中文路径乱码
                if r.encoding.lower() in ('iso-8859-1', 'ascii'):
                    r.encoding = r.apparent_encoding
                return r.text
        except Exception:
            pass
        return None

    def _z1(self, txt, base, referer, skip=25):
        t = (txt or '').replace('\r', '')
        if self._s in t:
            o = []
            for ln in t.splitlines():
                ln = ln.strip()
                if not ln:
                    continue
                if ln.startswith('#'):
                    o.append(ln)
                else:
                    a = urljoin(base, ln)
                    if '.' + self._a in ln.lower():
                        o.append(self._z9(a, referer))
                    else:
                        o.append(a)
            return '\n'.join(o) + '\n'
        hd, sg, tl, ms, td = self._z2(t)
        if not sg:
            return t
        mk = self._z8(base)
        st = {}
        for s in sg:
            k = self._z7(s['uri'], base)
            st[k] = st.get(k, 0.0) + float(s.get('dur') or 0)
        mkk = max(st.items(), key=lambda x: x[1])[0] if st else ('', '')
        tdur = sum(st.values()) or 0
        mdur = st.get(mkk, 0)
        cl = []
        rm = 0
        for idx, s in enumerate(sg):
            k = self._z7(s['uri'], base)
            fr = idx < 12
            au = urljoin(base, s.get('uri', ''))
            ia = self._z6(s['uri'], s.get('dur'), s.get('tags'))
            if mk and mk not in urlparse(au).path.lower():
                ia = True
            tt = '\n'.join(s.get('tags') or []).upper()
            if fr and self._x in tt and mk and mk not in urlparse(au).path.lower():
                ia = True
            if (not ia) and fr and tdur > 0 and mdur >= tdur * 0.6:
                if k != mkk and st.get(k, 0) <= 90:
                    ia = True
            if ia:
                rm += 1
                continue
            s['_idx'] = idx
            cl.append(s)
        if rm == 0 and len(sg) > 4:
            ac = 0.0
            ct = 0
            for idx, s in enumerate(sg[:12]):
                k = self._z7(s[0]['uri'], base)
                if k == mkk and ac >= 3:
                    break
                ac += float(s.get('dur') or td or 3)
                ct = idx + 1
                if ac >= skip:
                    break
            if ct > 0 and ct < len(sg):
                fk = self._z7(sg[0]['uri'], base)
                if fk != mkk:
                    cl = sg[ct:]
                    rm = ct
        if not cl:
            cl = sg
            rm = 0
        nl = []
        hm = False
        for ln in hd:
            if ln.startswith(self._t):
                hm = True
            if ln.startswith(self._u) or ln.startswith(self._v):
                continue
            if ln.startswith(self._w) and self._x in ln.upper() and rm > 0:
                continue
            nl.append(ln)
        if not hm:
            nl.insert(0, self._t)
        fi = cl[0].get('_idx', rm) if cl else rm
        nl.append(self._u + ':' + str(ms + fi))
        for s in cl:
            for tg in s.get('tags') or []:
                if tg.startswith(self._w) or tg.startswith('#EXT-X-MAP'):
                    tg = re.sub(r'URI="([^"]+)"', lambda m: 'URI="' + urljoin(base, m.group(1)) + '"', tg)
                nl.append(tg)
            nl.append(urljoin(base, s.get('uri', '')))
        if tl:
            for ln in tl:
                if ln.startswith(self._y):
                    nl.append(ln)
        elif self._y in t:
            nl.append(self._y)
        return '\n'.join(nl) + '\n'

    def _z2(self, text):
        ls = [x.strip() for x in (text or '').replace('\r', '').split('\n') if x.strip()]
        hd, sg, tl = [], [], []
        pt = []
        ms = 0
        td = 0
        st = False
        i = 0
        while i < len(ls):
            ln = ls[i]
            if ln.startswith(self._u):
                try:
                    ms = int(ln.split(':', 1)[1])
                except Exception:
                    pass
                if not st:
                    hd.append(ln)
                else:
                    pt.append(ln)
            elif ln.startswith(self._A):
                try:
                    td = float(ln.split(':', 1)[1])
                except Exception:
                    pass
                if not st:
                    hd.append(ln)
                else:
                    pt.append(ln)
            elif ln.startswith(self._z):
                st = True
                dr = td or 3.0
                m = re.search(self._z + r':\s*([\d.]+)', ln)
                if m:
                    try:
                        dr = float(m.group(1))
                    except Exception:
                        pass
                tg = pt + [ln]
                pt = []
                uri = ''
                j = i + 1
                while j < len(ls):
                    if ls[j].startswith('#'):
                        tg.append(ls[j])
                        j += 1
                        continue
                    uri = ls[j]
                    break
                if uri:
                    sg.append({'tags': tg, 'uri': uri, 'dur': dr})
                    i = j
                else:
                    tl.extend(tg)
            elif ln.startswith(self._y):
                tl.append(ln)
            elif ln.startswith('#'):
                if st:
                    pt.append(ln)
                else:
                    hd.append(ln)
            else:
                st = True
                dr = td or 3.0
                sg.append({'tags': pt, 'uri': ln, 'dur': dr})
                pt = []
            i += 1
        return hd, sg, tl, ms, td

    def _z6(self, uri, dur=0, prev=None):
        u = (uri or '').strip().lower()
        if not u:
            return False
        aw = [
            'ad', 'ads', 'advert', 'advertise', 'advertisement', 'sponsor',
            'pre', 'preroll', chr(29255)+chr(22836), chr(24191)+chr(21578),
            '/gg/', '_gg', 'gg_', '/adv/', '/ad/', '/ads/', 'banner', 'promo', 'commercial'
        ]
        if any(w in u for w in aw):
            return True
        try:
            if 0 < float(dur) <= 1.2:
                return True
        except Exception:
            pass
        return False

    def _z7(self, uri, base):
        try:
            f = urljoin(base, uri)
            p = urlparse(f)
            ph = re.sub(r'/[^/]*$', '/', p.path or '/')
            return (p.netloc.lower(), ph.lower())
        except Exception:
            return ('', '')

    def _z8(self, murl):
        try:
            p = urlparse(murl).path
            m = re.search(r'(/\d{8}/[^/]+/\d+kb/hls/)', p)
            if m:
                return m.group(1).lower()
            m = re.search(r'(/\d{8}/[^/]+/)', p)
            if m:
                return m.group(1).lower()
        except Exception:
            pass
        return ''
