# -*- coding: utf-8 -*-
# TVBox爬虫 - KanAV (https://kanav.ad)
# MacCMS v10 架构，支持中文字幕/日韩有码/无码/国产AV/流出自拍/动漫番剧

import sys
import re
import json
import requests
from urllib.parse import urljoin, quote

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "KanAV"

    def init(self, extend=""):
        self.host = "https://kanav.ad"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.host + "/",
        })
        # 分类映射（从首页导航提取）
        self.classes = [
            {"type_id": "1", "type_name": "中文字幕"},
            {"type_id": "2", "type_name": "日韩有码"},
            {"type_id": "3", "type_name": "日韩无码"},
            {"type_id": "4", "type_name": "国产AV"},
            {"type_id": "22", "type_name": "流出自拍"},
            {"type_id": "20", "type_name": "动漫番剧"},
        ]
        # 子分类（流出自拍和动漫番剧的二级分类，用于展示，但列表页直接使用父分类即可）
        # 实际上 /vod/type/id/22.html 会包含所有子分类，所以无需额外处理

    def isVideoFormat(self, url):
        return url and (".m3u8" in url or ".mp4" in url or ".mpd" in url)

    def manualVideoCheck(self):
        return False

    def _fetch(self, url, timeout=15):
        try:
            r = self.session.get(url, timeout=timeout)
            r.encoding = "utf-8"
            return r.text
        except Exception as e:
            print(f"[KanAV] 请求失败: {url} -> {e}")
            return ""

    def _fix_url(self, url):
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return self.host + url
        if url.startswith("http"):
            return url
        return self.host + "/" + url

    def _clean(self, text):
        if not text:
            return ""
        return re.sub(r"\s+", " ", text.strip())

    # ---------- 首页分类 ----------
    def homeContent(self, filter=False):
        classes = [{"type_id": c["type_id"], "type_name": c["type_name"]} for c in self.classes]
        # 添加筛选（按时间排序）
        filters = {}
        for c in self.classes:
            filters[c["type_id"]] = [
                {"key": "by", "name": "排序", "value": [
                    {"n": "时间", "v": "time_add"},
                    {"n": "人气", "v": "hits"},
                ]}
            ]
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        """首页推荐：直接取精选视频（首页的精选视频区）"""
        html = self._fetch(self.host)
        if not html:
            return {"list": []}
        videos = self._parse_home_videos(html)
        return {"list": videos[:20]}

    def _parse_home_videos(self, html):
        """解析首页精选视频区（.post-list 内的视频卡片）"""
        videos = []
        # 匹配精选视频区域（class="post-list"）
        pattern = r'<div class="post-list">(.*?)</div>\s*<div class="clearfix"></div>'
        post_list_match = re.search(pattern, html, re.S)
        if not post_list_match:
            return videos
        post_html = post_list_match.group(1)

        # 匹配每个视频卡片
        card_pattern = r'<div class="col-md-3 col-sm-6 col-xs-6">.*?<div class="video-item">.*?<a href="([^"]+)".*?<img[^>]+data-original="([^"]+)"[^>]*alt="([^"]*)"[^>]*>.*?<span class="model-view-left">([^<]*)</span>.*?<span class="model-view">([^<]*)</span>.*?</div>.*?<div class="entry-title">.*?<a[^>]*>([^<]*)</a>.*?(\d{4}\s*/\s*\d{2}\s*/\s*\d{2})'
        for m in re.finditer(card_pattern, post_html, re.S):
            href = self._fix_url(m.group(1))
            pic = self._fix_url(m.group(2))
            alt = self._clean(m.group(3))
            category = self._clean(m.group(4))
            duration = self._clean(m.group(5))
            title = self._clean(m.group(6))
            date = self._clean(m.group(7))

            # 提取视频ID（从播放链接中）
            vid_match = re.search(r'/id/(\d+)/', href)
            vod_id = vid_match.group(1) if vid_match else href

            # 组合备注
            remark = f"{category} | {duration}" if category else duration
            videos.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return videos

    # ---------- 分类列表 ----------
    def categoryContent(self, tid, pg, filter=False, extend=None):
        pg = int(pg) if pg else 1
        # 构建分类URL：/index.php/vod/type/id/{tid}.html 或 /index.php/vod/type/id/{tid}/page/{pg}.html
        if pg == 1:
            url = f"{self.host}/index.php/vod/type/id/{tid}.html"
        else:
            url = f"{self.host}/index.php/vod/type/id/{tid}/page/{pg}.html"

        # 如果有筛选参数
        if extend and isinstance(extend, dict):
            by = extend.get("by", "")
            if by:
                url += f"?by={by}"

        html = self._fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 0, "total": 0}

        videos = self._parse_category_videos(html)
        # 提取总页数
        pagecount = self._extract_page_count(html) or pg

        return {
            "list": videos,
            "page": pg,
            "pagecount": max(pagecount, pg),
            "limit": len(videos),
            "total": max(pagecount, pg) * (len(videos) or 20),
        }

    def _parse_category_videos(self, html):
        """解析分类页的视频列表（结构同首页精选）"""
        videos = []
        pattern = r'<div class="col-md-3 col-sm-6 col-xs-6">.*?<div class="video-item">.*?<a href="([^"]+)".*?<img[^>]+data-original="([^"]+)"[^>]*alt="([^"]*)"[^>]*>.*?<span class="model-view-left">([^<]*)</span>.*?<span class="model-view">([^<]*)</span>.*?</div>.*?<div class="entry-title">.*?<a[^>]*>([^<]*)</a>.*?(\d{4}\s*/\s*\d{2}\s*/\s*\d{2})'
        for m in re.finditer(pattern, html, re.S):
            href = self._fix_url(m.group(1))
            pic = self._fix_url(m.group(2))
            alt = self._clean(m.group(3))
            category = self._clean(m.group(4))
            duration = self._clean(m.group(5))
            title = self._clean(m.group(6))
            date = self._clean(m.group(7))

            vid_match = re.search(r'/id/(\d+)/', href)
            vod_id = vid_match.group(1) if vid_match else href

            remark = f"{category} | {duration}" if category else duration
            videos.append({
                "vod_id": vod_id,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remark,
            })
        return videos

    def _extract_page_count(self, html):
        """从分页链接提取总页数"""
        # 查找尾页链接
        last = re.search(r'<a[^>]*href="[^"]*?/page/(\d+)\.html"[^>]*>尾页</a>', html)
        if last:
            return int(last.group(1))
        # 查找所有页码数字
        nums = re.findall(r'/page/(\d+)\.html', html)
        if nums:
            return max(int(n) for n in nums)
        # 查找“共X页”文本
        total = re.search(r'共\s*(\d+)\s*页', html)
        if total:
            return int(total.group(1))
        return None

    # ---------- 详情 ----------
    def detailContent(self, ids):
        vod_id = ids[0] if isinstance(ids, list) else ids
        # 播放页URL：/index.php/vod/play/id/{vod_id}/sid/1/nid/1.html
        url = f"{self.host}/index.php/vod/play/id/{vod_id}/sid/1/nid/1.html"
        html = self._fetch(url)
        if not html:
            return {"list": []}

        # 提取标题
        title = ""
        title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html)
        if title_match:
            title = self._clean(title_match.group(1))
        if not title:
            og_title = re.search(r'<meta property="og:title" content="([^"]+)"', html)
            if og_title:
                title = self._clean(og_title.group(1))
        if not title:
            title = f"视频{vod_id}"

        # 提取封面（通常视频封面在播放页的 video 标签 poster 或 meta og:image）
        pic = ""
        og_img = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if og_img:
            pic = self._fix_url(og_img.group(1))
        if not pic:
            video_poster = re.search(r'<video[^>]+poster="([^"]+)"', html)
            if video_poster:
                pic = self._fix_url(video_poster.group(1))
        if not pic:
            img = re.search(r'<img[^>]+src="([^"]+)"[^>]*class="[^"]*thumb[^"]*"', html)
            if img:
                pic = self._fix_url(img.group(1))

        # 提取简介（meta description）
        desc = ""
        meta_desc = re.search(r'<meta name="description" content="([^"]+)"', html)
        if meta_desc:
            desc = self._clean(meta_desc.group(1))

        # ---------- 提取播放地址 ----------
        play_url = self._extract_play_url(html)

        if play_url:
            play_from = "KanAV"
            play_urls = f"正片${play_url}"
        else:
            # 如果找不到，将详情页URL作为播放地址（WebView模式）
            play_from = "详情页"
            play_urls = f"正片${url}"

        vod = {
            "vod_id": vod_id,
            "vod_name": title,
            "vod_pic": pic,
            "vod_content": desc,
            "vod_play_from": play_from,
            "vod_play_url": play_urls,
        }
        return {"list": [vod]}

    def _extract_play_url(self, html):
        """从播放页HTML中提取真实的视频地址（m3u8/mp4）"""
        # 1. 尝试提取 player_aaaa 变量（MacCMS常用）
        player_aaaa = re.search(r'var\s+player_aaaa\s*=\s*({.*?})\s*;', html, re.S)
        if player_aaaa:
            try:
                data = json.loads(player_aaaa.group(1))
                url = data.get("url", "")
                encrypt = data.get("encrypt", 0)
                if url:
                    if encrypt == 1:
                        # URL编码的
                        import urllib.parse
                        url = urllib.parse.unquote(url)
                    elif encrypt == 2:
                        # Base64编码的
                        import base64
                        try:
                            url = base64.b64decode(url).decode('utf-8')
                        except:
                            pass
                    return self._fix_url(url)
            except:
                pass

        # 2. 尝试提取 player_data 变量
        player_data = re.search(r'player_data\s*=\s*({.*?})\s*;', html, re.S)
        if player_data:
            try:
                data = json.loads(player_data.group(1))
                url = data.get("url", "")
                if url:
                    return self._fix_url(url)
            except:
                pass

        # 3. 尝试提取 var now 变量（某些模板使用）
        now = re.search(r'var\s+now\s*=\s*["\']([^"\']+)["\']', html)
        if now:
            return self._fix_url(now.group(1))

        # 4. 直接查找 <video> 标签的 src
        video_src = re.search(r'<video[^>]+src="([^"]+)"', html)
        if video_src:
            return self._fix_url(video_src.group(1))

        # 5. 查找 <source> 标签
        source = re.search(r'<source[^>]+src="([^"]+)"', html)
        if source:
            return self._fix_url(source.group(1))

        # 6. 查找 iframe（可能有嵌套播放器）
        iframe = re.search(r'<iframe[^>]+src="([^"]+)"', html)
        if iframe:
            iframe_url = self._fix_url(iframe.group(1))
            # 递归解析iframe内容（但会请求额外页面，此处简化，直接返回iframe地址，让TVBox WebView处理）
            # 或者可以选择再次提取
            return iframe_url

        # 7. 直接匹配 m3u8/mp4 直链
        direct = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4|mpd)[^\s"\'<>]*)', html)
        if direct:
            return self._fix_url(direct.group(1))

        return None

    # ---------- 播放 ----------
    def playerContent(self, flag, id, vipFlags=None):
        if not id:
            return {"parse": 1, "url": "", "header": {}}

        # 如果 id 是直链视频格式，直接返回
        if self.isVideoFormat(id):
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": self.host + "/",
            }
            return {"parse": 0, "url": id, "header": json.dumps(headers)}

        # 如果 id 是播放页URL，尝试再次提取
        if "/vod/play/" in id or "id=" in id:
            html = self._fetch(id)
            if html:
                play_url = self._extract_play_url(html)
                if play_url and self.isVideoFormat(play_url):
                    headers = {
                        "User-Agent": "Mozilla/5.0",
                        "Referer": self.host + "/",
                    }
                    return {"parse": 0, "url": play_url, "header": json.dumps(headers)}
                else:
                    # 如果提取失败，返回WebView模式
                    return {"parse": 1, "url": id, "header": json.dumps({"Referer": self.host + "/"})}
            else:
                return {"parse": 1, "url": id, "header": json.dumps({"Referer": self.host + "/"})}

        # 其他情况，尝试WebView
        if not id.startswith("http"):
            id = self._fix_url(id)
        return {"parse": 1, "url": id, "header": json.dumps({"Referer": self.host + "/"})}

    # ---------- 搜索 ----------
    def searchContent(self, key, quick=False, pg="1"):
        pg = int(pg) if pg else 1
        enc_key = quote(key)
        # 搜索URL：/index.php/vod/search.html?wd=关键词&by=time_add
        url = f"{self.host}/index.php/vod/search.html?wd={enc_key}"
        if pg > 1:
            url += f"&page={pg}"

        html = self._fetch(url)
        if not html:
            return {"list": [], "page": pg, "pagecount": 1, "limit": 0, "total": 0}

        # 搜索结果页面结构与分类页相同
        videos = self._parse_category_videos(html)
        pagecount = self._extract_page_count(html) or pg

        return {
            "list": videos,
            "page": pg,
            "pagecount": max(pagecount, pg),
            "limit": len(videos),
            "total": max(pagecount, pg) * (len(videos) or 20),
        }

    def localProxy(self, param):
        """本地代理（图片防盗链）"""
        try:
            if not isinstance(param, dict):
                return None
            url = param.get("url") or param.get("pic") or ""
            if not url:
                return [404, "text/plain", b""]
            # 补全协议
            if url.startswith("//"):
                url = "https:" + url
            elif not url.startswith("http"):
                url = self._fix_url(url)
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": self.host + "/",
            }
            r = self.session.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return [r.status_code, "text/plain", b""]
            content_type = r.headers.get("Content-Type", "image/jpeg")
            return [200, content_type, r.content]
        except Exception as e:
            return [500, "text/plain", str(e).encode()]

    def destroy(self):
        if self.session:
            self.session.close()