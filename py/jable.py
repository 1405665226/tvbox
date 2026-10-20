
# coding: utf-8
# FongMi / TVBox Python Spider
# Jable

import re
import html as html_parser
from urllib.parse import quote, urljoin
from base.spider import Spider


class Spider(Spider):

    def init(self, extend=""):
        self.host = "https://jable.tv"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/130.0.0.0 Safari/537.36"
            ),
            "Referer": self.host + "/",
        }

    def getName(self):
        return "Jable"

    # -------------------------
    # 网络请求
    # -------------------------

    def get_html(self, url):
        response = self.fetch(url, headers=self.headers)
        return response.text

    # -------------------------
    # URL 规范化
    # -------------------------

    def video_url(self, value):
        value = str(value).strip()

        if value.startswith(("http://", "https://")):
            return value

        return urljoin(self.host + "/", value)

    # -------------------------
    # HTML 元数据
    # -------------------------

    def get_meta(self, page, prop):
        for tag in re.findall(
            r"<meta\b[^>]*>",
            page,
            re.I | re.S
        ):
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
                return html_parser.unescape(c.group(1)).strip()

        return ""

    # -------------------------
    # 首页分类
    # -------------------------

    def homeContent(self, filter):
        return {
            "class": [
                {
                    "type_id": "latest",
                    "type_name": "最新"
                }
            ],
            "filters": {}
        }

    def homeVideoContent(self):
        try:
            page = self.get_html(self.host + "/")
            return {
                "list": self.parse_vod_list(page)
            }
        except Exception:
            return {"list": []}

    # -------------------------
    # 视频列表解析
    # -------------------------

    def parse_vod_list(self, page):
        vods = []
        seen = set()

        # 匹配指向 /videos/xxx/ 的链接
        pattern = re.compile(
            r"""<a\b([^>]*?)href\s*=\s*["']([^"']*/videos/[^"']+)["']([^>]*)>(.*?)</a>""",
            re.I | re.S
        )

        for match in pattern.finditer(page):
            attrs = match.group(1) + " " + match.group(3)
            href = html_parser.unescape(match.group(2))
            inner = match.group(4)

            url = self.video_url(href)

            if url in seen:
                continue

            # 提取标题
            title_match = re.search(
                r"""\btitle\s*=\s*["']([^"']+)["']""",
                attrs,
                re.I
            )

            title = (
                html_parser.unescape(title_match.group(1)).strip()
                if title_match else ""
            )

            if not title:
                title_match = re.search(
                    r"""class=["'][^"']*(?:title|video-title)[^"']*["'][^>]*>(.*?)</""",
                    inner,
                    re.I | re.S
                )

                if title_match:
                    title = re.sub(
                        r"<[^>]+>", "", title_match.group(1)
                    )
                    title = html_parser.unescape(title).strip()

            # 提取缩略图
            pic_match = re.search(
                r"""<(?:img|source)\b[^>]*?\b(?:data-src|data-original|src)\s*=\s*["']([^"']+)["']""",
                inner,
                re.I | re.S
            )

            pic = ""
            if pic_match:
                pic = urljoin(
                    self.host,
                    html_parser.unescape(pic_match.group(1))
                )

            # 提取时长
            duration_match = re.search(
                r"""class=["'][^"']*duration[^"']*["'][^>]*>(.*?)</""",
                inner,
                re.I | re.S
            )

            remarks = ""
            if duration_match:
                remarks = re.sub(
                    r"<[^>]+>", "", duration_match.group(1)
                ).strip()

            if not title:
                title = url.rstrip("/").split("/")[-1]

            seen.add(url)

            vods.append({
                "vod_id": url,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remarks
            })

        return vods

    # -------------------------
    # 分类与分页
    # -------------------------

    def categoryContent(self, tid, pg, filter, extend):
        page_num = max(1, int(pg or 1))

        if tid == "latest":
            url = self.host + "/"
        elif str(tid).startswith(("http://", "https://", "/")):
            url = self.video_url(tid)
        else:
            url = self.host + "/"

        if page_num > 1:
            sep = "&" if "?" in url else "?"
            url += sep + "page=" + str(page_num)

        try:
            page = self.get_html(url)
            vods = self.parse_vod_list(page)

            return {
                "list": vods,
                "page": page_num,
                "pagecount": page_num + 1 if vods else page_num,
                "limit": 20,
                "total": 0
            }
        except Exception:
            return {
                "list": [],
                "page": page_num,
                "pagecount": 0,
                "limit": 20,
                "total": 0
            }

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
            page = self.get_html(url)
            vods = self.parse_vod_list(page)

            return {
                "list": vods,
                "page": page_num,
                "pagecount": page_num + 1 if vods else page_num,
                "limit": 20,
                "total": 0
            }
        except Exception:
            return {
                "list": [],
                "page": page_num,
                "pagecount": 0,
                "limit": 20,
                "total": 0
            }

    # -------------------------
    # 视频详情
    # -------------------------

    def detailContent(self, ids):
        url = self.video_url(ids[0])
        page = self.get_html(url)

        title = self.get_meta(page, "og:title")
        pic = self.get_meta(page, "og:image")

        # canonical 地址
        canonical = re.search(
            r"""<link\b[^>]*\brel=["']canonical["'][^>]*\bhref=["']([^"']+)""",
            page,
            re.I
        )

        if canonical:
            url = urljoin(
                self.host,
                html_parser.unescape(canonical.group(1))
            )

        # 封面备用
        if not pic:
            poster = re.search(
                r"""<video\b[^>]*\bposter=["']([^"']+)""",
                page,
                re.I
            )
            if poster:
                pic = urljoin(
                    self.host,
                    html_parser.unescape(poster.group(1))
                )

        if not title:
            title = url.rstrip("/").split("/")[-1]

        # 返回详情页供播放器使用。
        # 不在这里把临时媒体地址当作永久地址保存。
        return {
            "list": [{
                "vod_id": url,
                "vod_name": title,
                "vod_pic": pic,
                "vod_content": "",
                "vod_play_from": "Jable",
                "vod_play_url": "正片$" + url
            }]
        }

    # -------------------------
    # 播放
    # -------------------------

    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 1,
            "jx": 0,
            "url": self.video_url(id),
            "header": self.headers
        }

    def destroy(self):
        pass
