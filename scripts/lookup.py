#!/usr/bin/env python3
"""Query Star Wars China's public glossary and return JSON."""

import argparse
import json
import ssl
import unicodedata
from html.parser import HTMLParser
from http.client import HTTPException
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from skill_update import start_update_check, take_update_notice


SOURCE_NAME = "星球大战中文网译名管理系统"
HTTP_URL = "http://starwarschina.com/glossary/"
HTTPS_URL = "https://starwarschina.com/glossary/"
CATEGORIES = (
    "作品", "人物", "生物", "事件", "地点", "组织", "种族",
    "星际飞船", "科技", "交通工具", "机器人", "头衔", "其它",
)
MAX_TERMS = 10
MAX_RESPONSE_BYTES = 256 * 1024


class GlossaryPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.last_page = None
        self.result_table = None
        self.result_table_closed = False
        self.table_depth = 0
        self.row = None
        self.cell = None
        self.form = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table_depth += 1
        elif tag == "tr" and not self.result_table_closed:
            self.row = []
            self.cell = None
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag == "form" and self.result_table_closed:
            self.form = {}
        elif tag == "input" and self.form is not None:
            fields = dict(attrs)
            if fields.get("name") in ("pgno", "tijiao"):
                self.form[fields["name"]] = fields.get("value", "")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.result_table is None and self.row[:3] == ["英文", "中文", "类别"]:
                self.result_table = self.table_depth
            elif self.result_table == self.table_depth:
                if len(self.row) != 4 or not all(self.row[:3]):
                    raise ValueError("原站译名表的行结构发生变化")
                self.rows.append(tuple(self.row[:3]))
            self.row = None
            self.cell = None
        elif tag == "table":
            if self.result_table == self.table_depth:
                self.result_table_closed = True
            self.table_depth -= 1
        elif tag == "form" and self.form is not None:
            if self.form.get("tijiao") == "末页":
                page_index = self.form.get("pgno") or ""
                if page_index.isdecimal():
                    self.last_page = int(page_index) + 1
            self.form = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GlossaryClient:
    def __init__(self):
        self.opener = build_opener(NoRedirects())
        self.url = HTTPS_URL

    def fetch(self, keyword, category, page):
        body = urlencode({
            "keyword": keyword, "category": category, "pgno": page - 1, "tijiao": "搜索",
        }).encode("ascii")
        try:
            return self._read(body)
        except URLError as error:
            # The original public URL remains available when HTTPS verification fails.
            if self.url != HTTPS_URL or not isinstance(error.reason, ssl.SSLCertVerificationError):
                raise
            self.url = HTTP_URL
            return self._read(body)

    def _read(self, body):
        request = Request(self.url, data=body, headers={"Accept": "text/html"})
        with self.opener.open(request, timeout=8) as response:
            if response.headers.get_content_type() != "text/html":
                raise ValueError("原站返回了非 HTML 响应")
            payload = response.read(MAX_RESPONSE_BYTES + 1)
        if len(payload) > MAX_RESPONSE_BYTES:
            raise ValueError("原站响应超出单页大小限制")

        page = GlossaryPage()
        page.feed(payload.decode("utf-8"))
        page.close()
        if not page.result_table_closed or page.last_page is None:
            raise ValueError("无法识别原站的译名表或分页表单")
        return page


def normalize(term):
    return " ".join(unicodedata.normalize("NFKC", term).casefold().split())


def lookup(client, keyword, category, page):
    query = {"query": keyword, "category": category or None, "page": page}
    try:
        response = client.fetch(keyword, category, page)
    except (OSError, HTTPException):
        return {
            **query, "status": "error", "error_code": "source_unavailable",
            "message": "请求星球大战中文网失败", "results": [],
        }
    except ValueError as error:
        return {
            **query, "status": "error", "error_code": "unexpected_response",
            "message": str(error), "results": [],
        }

    query["last_page"] = response.last_page
    if page > response.last_page:
        return {
            **query, "status": "error", "error_code": "page_out_of_range",
            "message": "页码超出原站的查询结果范围", "results": [],
        }

    normalized = normalize(keyword)
    results = []
    for english, chinese, entry_category in response.rows:
        exact = normalized in (normalize(english), normalize(chinese))
        results.append({
            "english": english, "chinese": chinese, "category": entry_category,
            "match": "exact" if exact else "related",
        })
    results.sort(key=lambda row: row["match"] != "exact")
    return {**query, "status": "ok" if results else "not_found", "results": results}


def main():
    parser = argparse.ArgumentParser(description="实时查阅星球大战中文网的中英译名。")
    parser.add_argument("keywords", nargs="+", metavar="词条", help="一个或多个中英文词条")
    parser.add_argument("--category", choices=CATEGORIES, default="", help="按原站类别筛选")
    parser.add_argument("--page", type=int, default=1, help="每个词条的结果页码，从 1 开始")
    args = parser.parse_args()
    keywords = list(dict.fromkeys(keyword.strip() for keyword in args.keywords))
    if not all(keywords):
        parser.error("词条不能为空")
    if len(keywords) > MAX_TERMS:
        parser.error(f"每次最多查询 {MAX_TERMS} 个不同词条")
    if args.page < 1:
        parser.error("页码必须大于等于 1")

    start_update_check()
    client = GlossaryClient()
    queries = [lookup(client, keyword, args.category, args.page) for keyword in keywords]
    print(json.dumps({
        "source": {"name": SOURCE_NAME, "url": client.url},
        "queries": queries,
        **take_update_notice(),
    }, ensure_ascii=False, indent=2))
    return int(any(query["status"] == "error" for query in queries))


if __name__ == "__main__":
    raise SystemExit(main())
