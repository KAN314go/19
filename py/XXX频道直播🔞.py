"""
@header({
  searchable: 1,
  filterable: 1,
  quickSearch: 1,
  title: 'OXAX直播',
  lang: 'hipy'
})
"""

# coding=utf-8
import re
import sys
import urllib.parse
import json
import base64
from pyquery import PyQuery as pq
import requests
import urllib3

# 忽略不安全的 HTTPS 警告（双重保险）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.append('..')
from base.spider import Spider as BaseSpider

# 用于 Base64 补缺验证的字符集
B64_CHARS = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/')


class Spider(BaseSpider):
    def __init__(self, *args, **kwargs):
        super().__init__()
        # 1. 完美接收并保存 t4_api 参数，作为全闭环本地流媒体中转的路由端点
        self.t4_api = kwargs.get('t4_api', '')
        self.base_url = "http://oxax.tv"
        
        self.session = requests.Session()
        self.session.verify = False  # 强行无视任何 SSL 阻断
        
        # 2. 注入原装高兼容性桌面级浏览器特征指纹标头
        self.session.headers.update({
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Referer': self.base_url,
            'Origin': self.base_url,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        
        # 3. 完美回归最满意的原始纯图形台标矩阵，彻底修复ОХ-АХ HD频道失效图标
        self.all_channels = [
            {"title": "ОХ-АХ HD", "href": "/oh-ah.html", "image": "https://www.lyngsat.com/logo/tv/oo/ox-ah-tv.png"},
            {"title": "CineMan XXX HD", "href": "/sl-hot1.html", "image": "https://www.lyngsat.com/logo/tv/cc/cineman-ru.png"},
            {"title": "CineMan XXX2 HD", "href": "/sl-hot2.html", "image": "https://www.lyngsat.com/logo/tv/cc/cineman-ru.png"},
            {"title": "Brazzers TV Europe", "href": "/brazzers-tv-europe.html", "image": "https://vpnpick.com/wp-content/uploads/2019/05/Unblock-Brazzers-TV.jpg"},
            {"title": "Brazzers TV", "href": "/brazzers-tv.html", "image": "https://vpnpick.com/wp-content/uploads/2019/05/Unblock-Brazzers-TV.jpg"},
            {"title": "Red Lips", "href": "/red-lips.html", "image": "https://s.tmimgcdn.com/scr/1200x750/172200/red-lips-logo-template_172226-original.jpg"},
            {"title": "KinoXXX", "href": "/kino-xxx.html", "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRc7KHiV3wAZTd3fxOPdRhiwsaIV_Rseyhetw&usqp=CAU"},
            {"title": "XY Max HD", "href": "/xy-max-hd.html", "image": "https://tvonline.bg/wp-content/uploads/XY-Max-tv.png"},
            {"title": "XY Plus HD", "href": "/xy-plus-hd.html", "image": "https://tvonline.bg/wp-content/uploads/XY-Max-tv.png"},
            {"title": "XY Mix HD", "href": "/xy-mix-hd.html", "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSqBz7zcnA_-3Uzc5tyziaXHYHXRKQzCbiUsBVHlMoelOkDoWubhvc58JIwTwquwhhKBhw&usqp=CAU"},
            {"title": "Barely legal", "href": "/barely-legal.html", "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQQtEzEFznJo6dHBs6xljoBEYDUOFvFS29f3nthDqB0qbNVUCBMxE2CaUgdtgaBQbut7Bc&usqp=CAU"},
            {"title": "Playboy TV", "href": "/playboy-tv.html", "image": "https://seeklogo.com/images/P/playboy-tv-logo-8447C82DEB-seeklogo.com.png"},
            {"title": "Vivid Red HD", "href": "/vivid-red.html", "image": "https://www.videosatservice.eu/wp-content/uploads/2017/01/VIVID-EUROPE-TOUCH-FINAL-1.png"},
            {"title": "Exxxotica HD", "href": "/hot-pleasure.html", "image": "https://www.lyngsat.com/logo/tv/ee/exxxotica-ru.png"},
            {"title": "Babes TV", "href": "/babes-tv.html", "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRzNRbMyt8e8auGhD8bWHBrsGbQxLdaWbQe7H6cM5GNmmHtksLqxZyapdmncJt_f3moNdA&usqp=CAU"},
            {"title": "Русская ночь", "href": "/russkaya-noch.html", "image": "https://new.strah.tv/uploads/posts/2019-02/medium/1549285137_extasy_big.png"},
            {"title": "Pink O TV", "href": "/pink-o.html", "image": "https://adult-tv-channels.com/wp-content/uploads/2021/09/redlight-hd-logo.png"},
            {"title": "Erox HD", "href": "/erox-hd.html", "image": "http://okporntv.com/wp-content/uploads/e8e83fc0ec61b284c54d5ac01a282145-321x211.jpeg"},
            {"title": "Eroxxx HD", "href": "/eroxxx-hd.html", "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTVg050bKmSjWZ5SARnx7qseE2UibjbnI3QAZC0BIKAI2Oiu6BewarebQKFBRyjUIv54dvRVA&usqp=CAU"},
            {"title": "Hustler HD", "href": "/hustler-hd.html", "image": "https://upload.wikimedia.org/wikipedia/en/c/c0/HUSTLER_TV_HD.png"},
            {"title": "Private TV", "href": "/private-tv.html", "image": "https://adult-tv-channels.com/wp-content/uploads/2021/09/redlight-hd-logo.png"},
            {"title": "Redlight HD", "href": "/redlight-hd.html", "image": "https://adult-tv-channels.com/wp-content/uploads/2021/09/redlight-hd-logo.png"},
            {"title": "Penthouse Gold HD", "href": "/penthouse-gold.html", "image": "https://penthousegold.com/images/logo_phGold.png"},
            {"title": "Penthouse Quickies", "href": "/penthouse-2.html", "image": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSQdOI0kcO2OwMdiy_TaWnwO7b4VuYh7H4HNxObeZz7fQ5NOXNLfWmj6F9PpYdb5KkS8Fo&usqp=CAU"},
            {"title": "O-la-la", "href": "/o-la-la.html", "image": "https://s.tmimgcdn.com/scr/1200x750/172200/red-lips-logo-template_172226-original.jpg"},
            {"title": "Blue Hustler", "href": "/blue-hustler.html", "image": "https://static.wikia.nocookie.net/tvfanon6528/images/8/80/Blue_Hustler_%232001-.n.v.%29.png/revision/latest?cb=20180312091828"},
            {"title": "Шалун", "href": "/shalun.html", "image": "https://vpnpick.com/wp-content/uploads/2019/05/Unblock-Brazzers-TV.jpg"},
            {"title": "Dorcel TV", "href": "/dorcel-tv.html", "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/Dorcel_TV.svg/2560px-Dorcel_TV.svg.png"},
            {"title": "Extasy HD", "href": "/extasyhd.html", "image": "https://new.strah.tv/uploads/posts/2019-02/medium/1549285137_extasy_big.png"},
            {"title": "XXL", "href": "/xxl.html", "image": "https://tvonline.bg/wp-content/uploads/XY-Max-tv.png"},
            {"title": "FAP TV 2", "href": "/fap-tv-2.html", "image": "https://i.pinimg.com/474x/60/99/76/609976515a6060808317d4652ac63a3e.jpg"},
            {"title": "FAP TV 3", "href": "/fap-tv-3.html", "image": "http://okteve.com/wp-content/uploads/media/1cfd26a1b4f7dfb8023ff3d4c7f36ec5-520x293.jpeg"},
            {"title": "FAP TV 4", "href": "/fap-tv-4.html", "image": "http://okteve.com/wp-content/uploads/media/cd1153aece771a6d5c6be0dcfe188245-520x293.jpeg"},
            {"title": "FAP TV Parody", "href": "/fap-tv-parody.html", "image": "https://i.pinimg.com/236x/95/36/54/953654df639272bbce26ccaad434644a.jpg"},
            {"title": "FAP TV Compilation", "href": "/fap-tv-compilation.html", "image": "http://okteve.com/wp-content/uploads/media/59eb09001a388f2d691a9b1c83c0f088-520x293.jpeg"},
            {"title": "FAP TV Anal", "href": "/fap-tv-anal.html", "image": "http://okteve.com/wp-content/uploads/media/df180a1f2f441b6282ce427ecfc7ff3a-520x293.jpeg"},
            {"title": "FAP TV Teens", "href": "/fap-tv-teens.html", "image": "https://i.pinimg.com/236x/20/87/bb/2087bb0876b99a08fe7a122ab9c0ba6f.jpg"},
            {"title": "FAP TV Lesbian", "href": "/fap-tv-lesbian.html", "image": "http://okteve.com/wp-content/uploads/media/c449b41987c74cf9cc0dea2ab692b893-520x293.jpeg"},
            {"title": "FAP TV BBW", "href": "/fap-tv-bbw.html", "image": "https://adult-tv-channels.com/wp-content/uploads/2021/09/Fap-TV-logo.png"},
            {"title": "FAP TV Trans", "href": "/fap-tv-trans.html", "image": "https://adult-tv-channels.com/wp-content/uploads/2021/09/Fap-TV-logo.png"},
        ]

    # ---------- 大佬原装解密工具函数完全引入 ----------
    def _try_decode(self, b):
        clean = re.sub(r'[^A-Za-z0-9+/]', '', b)
        pad = (4 - len(clean) % 4) % 4
        try:
            dec_bytes = base64.b64decode(clean + '=' * pad)
            dec = dec_bytes.decode('utf-8', errors='ignore')
            if re.search(r'\{v1\}[a-f0-9]+\{[^}]+\}[a-f0-9]{10,}', dec):
                return dec
        except:
            pass
        return None

    def _get_stolen(self, junk):
        s = ""
        for c in reversed(junk):
            if c in B64_CHARS:
                s = c + s
            else:
                break
        return s

    def _decrypt_ultimate(self, raw_b64):
        res = self._try_decode(raw_b64)
        if res:
            return res
        for s1 in range(3, min(150, len(raw_b64) - 10)):
            for l1 in range(3, 60):
                if s1 + l1 > len(raw_b64):
                    break
                stolen1 = self._get_stolen(raw_b64[s1:s1 + l1])
                for sl1 in range(0, len(stolen1) + 1):
                    p1  = stolen1[len(stolen1) - sl1:] if sl1 > 0 else ""
                    mid = raw_b64[:s1] + p1 + raw_b64[s1 + l1:]
                    res = self._try_decode(mid)
                    if res:
                        return res
                    for s2 in range(s1, min(150, len(mid) - 10)):
                        for l2 in range(3, 40):
                            if s2 + l2 > len(mid):
                                break
                            stolen2 = self._get_stolen(mid[s2:s2 + l2])
                            for sl2 in range(0, len(stolen2) + 1):
                                p2   = stolen2[len(stolen2) - sl2:] if sl2 > 0 else ""
                                test = mid[:s2] + p2 + mid[s2 + l2:]
                                res  = self._try_decode(test)
                                if res:
                                    return res
        return None

    def _extract_hash(self, decoded_json, kos):
        all_matches = re.findall(r'\{[^}]+\}([a-f0-9]+)\{[^}]+\}([a-f0-9]+)', decoded_json)
        if not all_matches:
            return None
        for raw_prefix, raw_suffix in all_matches:
            exp_len = 32 - len(raw_prefix) - len(kos)
            if exp_len <= 0 or len(raw_suffix) < exp_len:
                continue
            suffix_hash = raw_suffix[:exp_len]
            final_hash  = raw_prefix + kos + suffix_hash
            if len(final_hash) == 32:
                return final_hash
        return None
    # ---------- 大佬原装解密工具函数完全引入结束 ----------

    def _abs_url(self, base, url):
        if not url:
            return ''
        if url.startswith('http'):
            return url
        if url.startswith('//'):
            return 'http:' + url
        if url.startswith('/'):
            return self.base_url + url
        return base.rsplit('/', 1)[0] + '/' + url

    def getName(self):
        return "OXAX直播"

    def init(self, extend):
        pass

    def homeContent(self, filter):
        return {
            'class': [
                {'type_name': '全部频道', 'type_id': 'all'},
                {'type_name': 'HD频道', 'type_id': 'hd'},
                {'type_name': 'FAP系列', 'type_id': 'fap'},
            ]
        }

    def homeVideoContent(self):
        videos = []
        for ch in self.all_channels:
            videos.append({
                'vod_id': ch['href'],
                'vod_name': ch['title'],
                'vod_pic': ch['image'],
                'vod_remarks': '直播',
            })
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg)
        items_per_page = 30
        if tid == 'hd':
            channels = [ch for ch in self.all_channels if 'HD' in ch['title'].upper()]
        elif tid == 'fap':
            channels = [ch for ch in self.all_channels if 'FAP' in ch['title'].upper()]
        else:
            channels = self.all_channels
        
        start = (pg - 1) * items_per_page
        end = start + items_per_page
        page_channels = channels[start:end]
        
        videos = []
        for ch in page_channels:
            videos.append({
                'vod_id': ch['href'],
                'vod_name': ch['title'],
                'vod_pic': ch['image'],
                'vod_remarks': '直播',
            })
        return {
            'list': videos,
            'page': pg,
            'pagecount': max(1, (len(channels) + items_per_page - 1) // items_per_page),
            'limit': items_per_page,
            'total': len(channels),
        }

    def detailContent(self, array):
        if not array or not array[0]:
            return {'list': []}
        
        relative_path = array[0]
        detail_url = self._abs_url(self.base_url, relative_path)
        title = relative_path.replace('.html', '').replace('/', '').replace('-', ' ').title()
        image = "https://www.lyngsat.com/logo/tv/oo/ox-ah-tv.png"
        
        for ch in self.all_channels:
            if ch['href'] == relative_path:
                title = ch['title']
                image = ch['image']
                break
        
        vod = {
            'vod_id': relative_path,
            'vod_name': title,
            'vod_pic': image,
            'vod_remarks': '直播',
            'vod_content': '成人电视直播频道',
            'vod_play_from': 'OXAX',
            'vod_play_url': f'{title}${detail_url}',
        }
        return {'list': [vod]}

    def searchContent(self, key, quick, page='1'):
        if not key:
            return {'list': []}
        key_lower = key.lower()
        results = []
        for ch in self.all_channels:
            if key_lower in ch['title'].lower():
                results.append({
                    'vod_id': ch['href'],
                    'vod_name': ch['title'],
                    'vod_pic': ch['image'],
                    'vod_remarks': '直播',
                })
        return {'list': results}

    def playerContent(self, flag, id, vipFlags):
        result = {
            "parse": 0,
            "playUrl": "",
            "url": "",
            "header": {
                "User-Agent": self.session.headers.get('User-Agent'),
                "Referer": self.base_url,
                "Origin": self.base_url
            }
        }
        
        if not id:
            return result
        
        try:
            url = id
            if '$' in url:
                url = url.split('$')[1]
                
            url = url.replace("xittv.net", "oxax.tv").replace("https:", "http:")
            
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            html = resp.text
            
            def safe_extract(pattern, text):
                m = re.search(pattern, text)
                return m.group(1) if m else None

            kodk = safe_extract(r"var\s+kodk\s*=\s*[\"']([^\"']+)[\"']", html)
            kos = safe_extract(r"var\s+kos\s*=\s*[\"']([^\"']+)[\"']", html)
            raw_b64 = safe_extract(r"new\s+Playerjs\s*\(\s*[\"']#F([^\"']+)[\"']", html)
            
            if not all([kodk, kos, raw_b64]):
                raise Exception("页面缺少核心解密参数(kodk/kos/raw_b64)")
            
            decoded_json = self._decrypt_ultimate(raw_b64)
            if not decoded_json:
                raise Exception("Base64解密失败")
                
            final_hash = self._extract_hash(decoded_json, kos)
            if not final_hash:
                raise Exception("鉴权哈希拼接失败")
            
            main_url = f"https://s.oxax.tv/{kodk}{final_hash}"
            
            # 【完美融合】：将计算出来的高级免流直链托管给全闭环本地中转代理通道，不再下发死链
            proxy_url = f"{self.t4_api}&action=proxy_m3u8&play_url={urllib.parse.quote(main_url)}&ref={urllib.parse.quote(url)}"
            result["url"] = proxy_url
            
            cookies_dict = self.session.cookies.get_dict()
            if cookies_dict:
                cookie_str = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
                result["header"]["Cookie"] = cookie_str
            
        except Exception as e:
            print(f"[ERROR] 播放器解析失败: {e}")
            if "url" in locals() and "$" not in locals().get("url", ""):
                result["url"] = f"video://{url}"
        
        return result

    def localProxy(self, param):
        action = param.get('action', '')
        
        if action == 'proxy_m3u8':
            play_url = param.get('play_url', '')
            ref = param.get('ref', '')
            
            print("\n" + "="*60)
            print(f"[V3 DEEP DEBUG] 代理中转引擎开始处理 M3U8 请求...")
            print(f"[V3 DEEP DEBUG] 传入的流地址: {play_url}")
            
            try:
                # 【独家绝招】：必须强制使用动态维护了算出来 Cookie 凭证的 self.session 发起请求！
                res = self.session.get(play_url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': ref,
                    'Origin': 'http://oxax.tv'
                }, timeout=10, allow_redirects=True)
                
                m3u8_text = res.text
                final_url = res.url
                
                print(f"[V3 DEEP DEBUG] 302 追踪完毕！状态码: {res.status_code}, 真实最终直链: {final_url}")
                print(f"[V3 DEEP DEBUG] 获取到的原始 M3U8 文本体积: {len(m3u8_text)} 字节")
                
                parsed_url = urllib.parse.urlparse(final_url)
                base_path = parsed_url.path.rsplit('/', 1)[0] + '/'
                base_dir_url = f"{parsed_url.scheme}://{parsed_url.netloc}{base_path}"
                
                new_m3u8_lines = []
                for line in m3u8_text.splitlines():
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if not line.startswith('http'):
                            line = urllib.parse.urljoin(base_dir_url, line)
                        
                        encoded_ts = urllib.parse.quote(line)
                        line = f"{self.t4_api}&action=proxy_ts&ts_url={encoded_ts}&ref={urllib.parse.quote(ref)}"
                        
                    new_m3u8_lines.append(line)
                
                fixed_m3u8 = "\n".join(new_m3u8_lines)
                print(f"[V3 DEEP DEBUG] M3U8 文本行重写补全完毕，下发给内核。")
                print("="*60 + "\n")
                return [200, "application/vnd.apple.mpegurl", fixed_m3u8]
            except Exception as e:
                print(f"[V3 DEEP DEBUG] M3U8 代理阶段遭遇异常: {e}")
                print("="*60 + "\n")
                return [500, "text/plain", f"Proxy M3U8 Error: {e}"]
                
        elif action == 'proxy_ts':
            ts_url = param.get('ts_url', '')
            ref = param.get('ref', '')
            try:
                # TS分片拉取同样继承 Session 中的全套动态算出的动态 Cookie 会话，彻底根除 404
                ts_res = self.session.get(ts_url, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': ref,
                    'Origin': 'http://oxax.tv'
                }, timeout=15, stream=True)
                return [200, "video/mp2t", ts_res.content]
            except Exception as e:
                print(f"[V3 DEEP DEBUG] TS 分片中转拉取失败: {e}")
                return [500, "text/plain", f"Proxy TS Error: {e}"]
                
        return [404, "text/plain", "Not Found"]

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        return False
