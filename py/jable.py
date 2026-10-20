# -*- coding: utf-8 -*-
import re
import sys
import json
import time
from urllib.parse import quote, unquote

try:
    import requests
except Exception:
    requests = None
import urllib.request

try:
    import urllib3
    urllib3.disable_warnings()
except Exception:
    pass
try:
    from lxml import etree
except Exception:
    etree = None


class Spider:
    """Jable.tv 独立 Python Spider (优化版)"""

    def __init__(self):
        self.host = "https://jable.tv"
        self.ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/122.0.0.0 Safari/537.36")
        self._session = None
        self.categories = [
            {"type_id": "latest-updates", "type_name": "最新发布"},
            {"type_id": "most-viewed", "type_name": "最多观看"},
            {"type_id": "release", "type_name": "近期上映"},
            {"type_id": "categories", "type_name": "视频分类"}
        ]
        self.filters = {
            "latest-updates": [
                {"key": "sort", "name": "排序", "value": [
                    {"n": "最新发布", "v": "post_date"},
                    {"n": "最多观看", "v": "viewed"},
                    {"n": "最高评分", "v": "rate"}
                ]}
            ]
        }

    def getName(self):
        return "Jable"

    def getDependence(self):
        return []

    def init(self, extend=""):
        if isinstance(extend, str) and extend.strip()[:1] == "{":
            try:
                extend = json.loads(extend)
            except Exception:
                extend = dict()
        if not isinstance(extend, dict):
            extend = dict()
        if extend.get("host"):
            self.host = str(extend["host"]).rstrip("/")

    def _headers(self, referer=None):
        return {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": (referer or self.host) + "/",
            "Cache-Control": "no-cache",
        }

    def _session_obj(self):
        if self._session is not None:
            return self._session
        if requests is None:
            return None
        try:
            s = requests.Session()
            s.verify = False
            s.headers.update(self._headers())
            self._session = s
            return s
        except Exception:
            return None

    def _ensure_str(self, data):
        if isinstance(data, str):
            return data
        if data is None:
            return ""
        if isinstance(data, bytes):
            try:
                return data.decode("utf-8")
            except UnicodeDecodeError:
                return data.decode("gbk", errors="ignore")
        return str(data)

    def _get(self, url, referer=None):
        if not url:
            return ""
        headers = self._headers(referer)
        sess = self._session_obj()
        if sess is not None:
            for _ in range(3):
                try:
                    r = sess.get(url, headers=headers, timeout=15)
                    if r.status_code == 200:
                        return self._ensure_str(r.content)
                except Exception:
                    time.sleep(1)
            return ""
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=15)
            return self._ensure_str(resp.read())
        except Exception:
            pass
        return ""

    def _fix(self, u):
        if not u:
            return ""
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            return self.host + u
        return u

    def _cards(self, html):
        if not html or etree is None:
            return []
        try:
            tree = etree.HTML(html)
        except Exception:
            return []
        
        out, seen = [], set()
        # 直接通过包含 /videos/ 的链接进行鲁棒性提取，避免网页布局变动导致失效
        for a in tree.xpath('//a[contains(@href, "/videos/")]'):
            try:
                href = a.get("href", "")
                m = re.search(r'/videos/([^/]+)/', href)
                if not m:
                    continue
                vid = m.group(1)
                if vid in seen or len(vid) < 3:
                    continue
                seen.add(vid)
                
                title = a.get("title", "").strip()
                if not title:
                    t_nodes = a.xpath('.//h6[@class="title"]//text() | .//img/@alt | .//text()')
                    title = "".join([t.strip() for t in t_nodes if t.strip()]).strip()
                if not title:
                    title = vid
                
                img_nodes = a.xpath('.//img/@data-src | .//img/@src')
                img = img_nodes[0] if img_nodes else ""
                
                out.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": self._fix(img),
                    "vod_remarks": ""
                })
            except Exception:
                continue
        return out

    def homeContent(self, filter=None):
        return {"class": self.categories, "filters": self.filters}

    def homeVideoContent(self):
        html = self._get(self.host)
        return {"list": self._cards(html)}

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        pg = max(int(pg or 1), 1)
        result = {"list": [], "page": pg, "pagecount": 9999, "limit": 24, "total": 99999}
        
        if tid == "categories":
            html = self._get(self.host + "/categories/")
            if not html or etree is None:
                return result
            tree = etree.HTML(html)
            cats = tree.xpath('//a[contains(@href, "/categories/")]')
            out, seen = [], set()
            for c in cats:
                href = c.get("href", "")
                name = "".join(c.xpath('.//text()')).strip()
                m = re.search(r'/categories/([^/]+)/', href)
                if m and name and m.group(1) not in seen:
                    seen.add(m.group(1))
                    out.append({"vod_id": "cat_" + m.group(1), "vod_name": name, "vod_pic": "", "vod_remarks": "分类"})
            result["list"] = out
            return result
        
        if tid.startswith("cat_"):
            c_name = tid.replace("cat_", "")
            url = "%s/categories/%s/%s" % (self.host, c_name, ("" if pg == 1 else "%d/" % pg))
        else:
            sort_by = (extend or {}).get("sort", "post_date")
            if pg == 1:
                url = "%s/%s/" % (self.host, tid)
            else:
                url = "%s/%s/?from=%s&page=%d" % (self.host, tid, sort_by, pg)

        html = self._get(url)
        result["list"] = self._cards(html)
        return result

    def detailContent(self, ids):
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0]) if ids else ""
        else:
            vid = str(ids or "")
        vid = vid.strip()
        if not vid:
            return {"list": []}

        url = "%s/videos/%s/" % (self.host, vid)
        html = self._get(url)
        if not html:
            return {"list": []}

        title, cover, desc, actors = "", "", "", []
        try:
            tree = etree.HTML(html)
            title = "".join(tree.xpath('//h1[@class="header-title"]//text()')).strip()
            img_l = tree.xpath('//meta[@property="og:image"]/@content')
            cover = img_l[0] if img_l else ""
            desc = "".join(tree.xpath('//div[@class="description"]//text()')).strip()
            actors = [a.strip() for a in tree.xpath('//span[@class="actor-name"]//text()') if a.strip()]
        except Exception:
            pass

        if not title:
            title = vid

        vod = {
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": cover,
            "vod_content": desc,
            "vod_actor": " / ".join(actors),
            "vod_play_from": "Jable",
            "vod_play_url": "正片$" + vid
        }
        return {"list": [vod]}

    def searchContent(self, key, quick=False, pg="1"):
        pg = max(int(pg or 1), 1)
        url = "%s/search/%s/?page=%d" % (self.host, quote(key), pg)
        html = self._get(url)
        cards = self._cards(html)
        return {"list": cards, "page": pg, "pagecount": pg + 1 if cards else pg, "limit": 20, "total": len(cards)}

    def playerContent(self, flag, id, vipFlags=None):
        url = "%s/videos/%s/" % (self.host, id)
        html = self._get(url)
        play_url = ""
        if html:
            m = re.search(r'https?://[^\s"\'<>]+\bmaster\.m3u8\b[^\s"\'<>]*', html)
            if not m:
                m = re.search(r'hlsUrl\s*=\s*[\'"]([^\'"]+\.m3u8[^\'"]*)[\'"]', html)
            if m:
                play_url = m.group(0) if "http" in m.group(0) else m.group(1)

        header = {"User-Agent": self.ua, "Referer": self.host + "/"}
        return {
            "parse": 0,
            "jx": 0,
            "playUrl": "",
            "url": play_url,
            "header": header,
            "format": "application/x-mpegURL"
        }

    def isVideoFormat(self, url):
        return ".m3u8" in (url or "").lower()

    def manualVideoCheck(self):
        return False

    def action(self, action):
        return dict()

    def destroy(self):
        return None
