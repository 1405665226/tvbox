
# coding: utf-8
# FongMi / TVBox Python Spider
# jable.py

import re
import html as html_parser
from urllib.parse import quote, urljoin
from base.spider import Spider as BaseSpider


class Spider(BaseSpider):

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
        self.debug_message = ""

    def getName(self):
        return "Jable诊断版"

    def _request(self, url):
        response = self.fetch(url, headers=self.headers)
        return response.text

    def _clean(self, value):
        value = html_parser.unescape(value or "")
        return re.sub(r"\s+", " ", value).strip()

    def _meta(self, page, name):
        for tag in re.findall(r"<meta\b[^>]*>", page, re.I):
            prop = re.search(
                r"""(?:property|name)\s*=\s*["']([^"']+)["']""",
                tag, re.I
            )
            content = re.search(
                r"""content\s*=\s*["']([^"']*)["']""",
                tag, re.I
            )
            if prop and content and prop.group(1).lower() == name.lower():
                return self._clean(content.group(1))
        return ""

    def _url(self, value):
        value = str(value or "").strip()
        if value.startswith(("http://", "https://")):
            return value
        return urljoin(self.host + "/", value)

    # 首页分类
    def homeContent(self, filter):
        return {
            "class": [
                {"type_id": "latest", "type_name": "最新"},
                {"type_id": "diagnostic", "type_name": "接口测试"}
            ]
        }

    # 首页推荐视频
    def homeVideoContent(self):
        try:
            page = self._request(self.host + "/")
            return {"list": self.parse_vod_list(page)}
        except Exception as e:
            self.debug_message = "首页请求失败: " + str(e)
            return {"list": []}

    # 视频列表解析
    def parse_vod_list(self, page):
        result = []
        seen = set()

        # 解析指向 /videos/xxx/ 的链接
        pattern = re.compile(
            r"""<a\b([^>]*?)href\s*=\s*["']([^"']*/videos/[^"']+)["']([^>]*)>(.*?)</a>""",
            re.I | re.S
        )

        for m in pattern.finditer(page):
            attrs = m.group(1) + " " + m.group(3)
            href = html_parser.unescape(m.group(2))
            inner = m.group(4)
            video_url = self._url(href)

            if video_url in seen:
                continue

            # 标题优先读取 title 属性
            title_match = re.search(
                r"""title\s*=\s*["']([^"']+)["']""",
                attrs, re.I
            )
            title = self._clean(title_match.group(1)) if title_match else ""

            if not title:
                title = self._clean(
                    re.sub(r"<[^>]+>", " ", inner)
                )

            # 封面
            pic_match = re.search(
                r"""<(?:img|source)\b[^>]*?\b(?:data-src|data-original|src)\s*=\s*["']([^"']+)["']""",
                inner, re.I | re.S
            )
            pic = self._url(pic_match.group(1)) if pic_match else ""

            # 时长
            duration_match = re.search(
                r"""class\s*=\s*["'][^"']*duration[^"']*["'][^>]*>(.*?)</""",
                inner, re.I | re.S
            )
            remarks = (
                self._clean(re.sub(r"<[^>]+>", " ", duration_match.group(1)))
                if duration_match else ""
            )

            if not title:
                title = video_url.rstrip("/").split("/")[-1]

            seen.add(video_url)
            result.append({
                "vod_id": video_url,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": remarks
            })

        return result

    # 分类与分页
    def categoryContent(self, tid, pg, filter, extend):
        page_num = max(1, int(pg or 1))

        # 内置诊断分类，不访问网站
        if tid == "diagnostic":
            return {
                "list": [{
                    "vod_id": self.host + "/videos/ebwh-360/",
                    "vod_name": "Spider接口测试",
                    "vod_pic": "",
                    "vod_remarks": "接口正常"
                }],
                "page": 1,
                "pagecount": 1,
                "limit": 1,
                "total": 1
            }

        url = self.host + "/"
        if page_num > 1:
            url += "?page=" + str(page_num)

        try:
            page = self._request(url)
            vods = self.parse_vod_list(page)

            self.debug_message = (
                "列表请求成功；HTML长度=%d；视频数=%d"
                % (len(page), len(vods))
            )

            return {
                "list": vods,
                "page": page_num,
                "pagecount": page_num + 1 if vods else page_num,
                "limit": 20,
                "total": 0
            }
        except Exception as e:
            self.debug_message = "分类请求失败: " + str(e)
            return {
                "list": [],
                "page": page_num,
                "pagecount": 0,
                "limit": 20,
                "total": 0
            }

    # 搜索
    def searchContent(self, key, quick, pg="1"):
        page_num = max(1, int(pg or 1))
        url = (
            self.host + "/search/"
            + quote(key, safe="")
            + "/?page=" + str(page_num)
        )

        try:
            page = self._request(url)
            vods = self.parse_vod_list(page)
            return {
                "list": vods,
                "page": page_num,
                "pagecount": page_num + 1 if vods else page_num,
                "limit": 20,
                "total": 0
            }
        except Exception as e:
            self.debug_message = "搜索请求失败: " + str(e)
            return {
                "list": [],
                "page": page_num,
                "pagecount": 0,
                "limit": 20,
                "total": 0
            }

    # 详情
    def detailContent(self, ids):
        url = self._url(ids[0])
        page = self._request(url)

        title = self._meta(page, "og:title")
        pic = self._meta(page, "og:image")

        if not title:
            title = url.rstrip("/").split("/")[-1]

        # canonical
        canonical = re.search(
            r"""<link\b[^>]*\brel=["']canonical["'][^>]*\bhref=["']([^"']+)""",
            page, re.I
        )
        if canonical:
            url = self._url(canonical.group(1))

        # 详情页封面备用
        if not pic:
            poster = re.search(
                r"""<video\b[^>]*\bposter=["']([^"']+)""",
                page, re.I
            )
            if poster:
                pic = self._url(poster.group(1))

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

    # 播放入口
    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 1,
            "jx": 0,
            "url": self._url(id),
            "header": self.headers
        }

    def destroy(self):
        pass
