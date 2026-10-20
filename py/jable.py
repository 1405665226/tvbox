
# jable.py
# FongMi/TV Python Spider
# api: "./jable.py"

import re
import html
from urllib.parse import urljoin, quote
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):

    host = "https://jable.tv"

    def init(self, extend=""):
        self.extend = extend
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
            "Referer": self.host + "/",
        }

    # -------------------------
    # 网络请求
    # -------------------------

    def _get(self, url):
        # 使用 FongMi Spider 基类提供的 fetch 接口
        result = self.fetch(url, headers=self.headers)

        if isinstance(result, bytes):
            return result.decode("utf-8", errors="replace")

        return str(result)

    # -------------------------
    # HTML 工具
    # -------------------------

    def _meta(self, page, prop):
        tags = re.findall(
            r"<meta\b[^>]*>",
            page,
            re.I | re.S
        )

        for tag in tags:
            p = re.search(
                r"""\bproperty\s*=\s*["']([^"']+)["']""",
                tag,
                re.I
            )
            c = re.search(
                r"""\bcontent\s*=\s*["']([^"']*)["']""",
                tag,
                re.I
            )

            if p and c and p.group(1).lower() == prop.lower():
                return html.unescape(c.group(1).strip())

        return ""

    def _video_url(self, value):
        value = str(value).strip()

        if value.startswith(("http://", "https://")):
            return value

        if value.startswith("/"):
            return urljoin(self.host, value)

        value = value.removeprefix("videos/").strip("/")
        return urljoin(self.host, "/videos/" + value + "/")

    def _cards(self, page):
        """从列表页提取视频卡片。"""
        page = html.unescape(page)
        result = []
        seen = set()

        # 优先在含视频链接的 HTML 标签中提取封面和标题
        pattern = re.compile(
            r'<a\b([^>]*\bhref=["\']([^"\']*/videos/[^"\']+)["\'][^>]*)>'
            r'(.*?)</a>',
            re.I | re.S
        )

        for match in pattern.finditer(page):
            attrs = match.group(1)
            href = match.group(2)
            inner = match.group(3)

            url = self._video_url(href)

            if url in seen:
                continue
            seen.add(url)

            title_match = re.search(
                r"""\btitle=["']([^"']+)["']""",
                attrs,
                re.I
            )

            image_match = re.search(
                r"""<(?:img|source)\b[^>]*?\b(?:data-src|data-original|src)=["']([^"']+)["']""",
                inner,
                re.I | re.S
            )

            title = (
                html.unescape(title_match.group(1)).strip()
                if title_match else ""
            )

            if not title:
                title_match = re.search(
                    r"<(?:h[1-6]|span)[^>]*>(.*?)</(?:h[1-6]|span)>",
                    inner,
                    re.I | re.S
                )
                if title_match:
                    title = re.sub(
                        r"<[^>]+>", "", title_match.group(1)
                    ).strip()

            pic = (
                urljoin(self.host, image_match.group(1))
                if image_match else ""
            )

            if not title:
                title = url.rstrip("/").split("/")[-1]

            result.append({
                "vod_id": url,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": "",
            })

        return result

    def page(self, items, pg, pagecount=9999):
        return {
            "list": items,
            "page": int(pg),
            "pagecount": pagecount,
            "limit": 20,
            "total": len(items),
        }

    # -------------------------
    # 首页
    # -------------------------

    def homeContent(self, filter):
        return {
            "class": [
                {"type_id": "latest", "type_name": "最新"},
            ]
        }

    # -------------------------
    # 分类 / 分页
    # -------------------------

    def categoryContent(self, tid, pg, filter, extend):
        page_num = max(1, int(pg or 1))

        if tid == "latest":
            url = self.host + "/"
        else:
            url = self._video_url(tid)

        if page_num > 1:
            separator = "&" if "?" in url else "?"
            url += separator + "page=" + str(page_num)

        try:
            page = self._get(url)
            items = self._cards(page)

            return {
                "list": items,
                "page": page_num,
                "pagecount": page_num + 1 if items else page_num,
                "limit": 20,
                "total": 0,
            }
        except Exception:
            return self.page([], page_num, 1)

    # -------------------------
    # 搜索
    # -------------------------

    def searchContent(self, key, quick, pg="1"):
        page_num = max(1, int(pg or 1))

        url = (
            self.host
            + "/search/"
            + quote(key, safe="")
            + "/?page="
            + str(page_num)
        )

        try:
            page = self._get(url)
            items = self._cards(page)

            return {
                "list": items,
                "page": page_num,
                "pagecount": page_num + 1 if items else page_num,
                "limit": 20,
                "total": 0,
            }
        except Exception:
            return self.page([], page_num, 1)

    # -------------------------
    # 视频详情
    # -------------------------

    def detailContent(self, ids):
        url = self._video_url(ids[0])
        page = html.unescape(self._get(url))

        title = self._meta(page, "og:title")
        pic = self._meta(page, "og:image")

        if not pic:
            m = re.search(
                r"""<video\b[^>]*\bposter=["']([^"']+)""",
                page,
                re.I
            )
            if m:
                pic = html.unescape(m.group(1))

        canonical = re.search(
            r"""<link\b[^>]*\brel=["']canonical["'][^>]*\bhref=["']([^"']+)""",
            page,
            re.I
        )

        if canonical:
            url = urljoin(self.host, canonical.group(1))

        if not title:
            title = url.rstrip("/").split("/")[-1]

        # 提取页面声明的 HLS URL
        match = re.search(
            r"""\bhlsUrl\s*=\s*(['"])(.*?)\1""",
            page,
            re.I | re.S
        )

        play_url = match.group(2).strip() if match else ""

        if play_url.startswith("//"):
            play_url = "https:" + play_url
        elif play_url.startswith("/"):
            play_url = urljoin(self.host, play_url)

        return {
            "list": [{
                "vod_id": url,
                "vod_name": title,
                "vod_pic": pic,
                "vod_content": "",
                "vod_play_from": "Jable",
                "vod_play_url": (
                    "正片$" + play_url
                    if play_url
                    else "详情页$" + url
                ),
            }]
        }

    # -------------------------
    # 播放
    # -------------------------

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "jx": 0,
            "url": id,
            "header": self.headers,
        }

    def destroy(self):
        pass
