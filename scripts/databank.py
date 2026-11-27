#!/usr/bin/env python3
"""Search the Star Wars China Databank index and read its entries."""

import argparse
import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from http.client import HTTPException
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from skill_update import start_update_check, take_update_notice

SITE = "https://www.starwarsfans.cn"
INDEX_URL = f"{SITE}/portal.php?mod=list&catid=13"
SOURCE = {"name": "星球大战中文网资料库", "url": INDEX_URL}
HOSTS = {"www.starwarsfans.cn", "starwarsfans.cn"}
LINK_HOSTS = HOSTS | {"www.starwarschina.com", "starwarschina.com"}
MAX_PAGE_BYTES = 1024 * 1024
VOID_TAGS = set("area base br col embed hr img input link meta param source track wbr".split())


class DatabankError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code

    def details(self):
        return {"error_code": self.code, "message": str(self)}


class Element:
    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.children = []

    def descendants(self, tag):
        for child in self.children:
            if isinstance(child, Element):
                if child.tag == tag:
                    yield child
                yield from child.descendants(tag)

    def text(self):
        parts = []
        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag not in ("script", "style"):
                parts.append(child.text())
                if child.tag in ("br", "p", "div", "li", "tr", "blockquote", "h2", "h3"):
                    parts.append("\n")
        return "".join(parts)

    def label(self):
        return " ".join(self.text().split())


class DatabankPage(HTMLParser):
    """Keep the Discuz article, breadcrumbs, title, and post regions."""

    def __init__(self, region_ids=("article_content", "pt", "thread_subject")):
        super().__init__()
        self.region_ids = region_ids
        self.regions = {}
        self.stack = []

    def handle_starttag(self, tag, attrs):
        fields = dict(attrs)
        if not self.stack:
            key = fields.get("id") or ""
            if key not in self.region_ids and not key.startswith("postmessage_"):
                return
            element = self.regions[key] = Element(tag, fields)
        else:
            element = Element(tag, fields)
            self.stack[-1].children.append(element)
        if tag not in VOID_TAGS:
            self.stack.append(element)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if self.stack:
            self.stack[-1].children.append(data)

    def posts(self):
        return (region for key, region in self.regions.items() if key.startswith("postmessage_"))


class StarWarsRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if target.scheme not in ("http", "https") or target.netloc not in HOSTS:
            return None
        return super().redirect_request(
            req, fp, code, msg, headers, target._replace(scheme="https").geturl(),
        )


def fetch_page(url, page=None):
    try:
        opener = build_opener(StarWarsRedirects())
        request = Request(url, headers={"Accept": "text/html"})
        with opener.open(request, timeout=10) as response:
            if response.headers.get_content_type() != "text/html":
                raise DatabankError("unexpected_response", "原站返回了非 HTML 响应")
            data = response.read(MAX_PAGE_BYTES + 1)
    except (OSError, HTTPException) as error:
        raise DatabankError("source_unavailable", "无法访问星球大战中文网") from error
    if len(data) > MAX_PAGE_BYTES:
        raise DatabankError("unexpected_response", "原站响应超出单页大小限制")
    try:
        if page is None:
            page = DatabankPage()
        page.feed(data.decode("utf-8"))
        page.close()
    except ValueError as error:
        raise DatabankError("unexpected_response", "无法解析原站响应") from error
    return page


def site_link(reference, hosts=LINK_HOSTS):
    try:
        url = urlsplit(urljoin(f"{SITE}/", reference))
    except ValueError:
        return None
    if url.scheme in ("https", "http") and url.netloc in hosts:
        return url
    return None


def thread_id(reference):
    if re.fullmatch(r"[1-9][0-9]*", reference):
        return reference
    url = site_link(reference)
    if url is None:
        return None
    rewritten = re.fullmatch(r"/thread-([1-9][0-9]*)-[0-9]+-[0-9]+\.html", url.path)
    if rewritten:
        return rewritten[1]
    parameters = parse_qs(url.query)
    if url.path == "/forum.php" and parameters.get("mod") == ["viewthread"]:
        values = parameters.get("tid", [])
        if len(values) == 1 and re.fullmatch(r"[1-9][0-9]*", values[0]):
            return values[0]
    return None


def thread_url(tid):
    return f"{SITE}/forum.php?mod=viewthread&tid={tid}"


def entry_address(reference):
    tid = thread_id(reference)
    if tid is not None:
        return tid, thread_url(tid)
    official = site_link(reference, {"starwars.com", "www.starwars.com"})
    if official is not None and official.path.startswith("/databank/"):
        return None, official._replace(scheme="https").geturl()
    return None, None


def categories():
    article = fetch_page(INDEX_URL).regions.get("article_content")
    index = {}
    if article is not None:
        for anchor in article.descendants("a"):
            tid = thread_id(anchor.attrs.get("href") or "")
            label = re.fullmatch(r"(.+?)[（(]([^）)]+)[）)]", anchor.label())
            if tid and label:
                index[tid] = {"chinese": label[1], "english": label[2], "url": thread_url(tid)}
    if not index:
        raise DatabankError("unexpected_response", "无法识别原站的资料库分类索引")
    return list(index.values())


def category_entries(category):
    entries = {}
    for post in fetch_page(category["url"]).posts():
        for row in post.descendants("tr"):
            cells = [c for c in row.children if isinstance(c, Element) and c.tag == "td"]
            if len(cells) != 2:
                continue
            english, chinese = (cell.label() for cell in cells)
            for anchor in cells[1].descendants("a"):
                tid, url = entry_address(anchor.attrs.get("href") or "")
                if url and english and chinese:
                    entries[url, english, chinese] = {
                        "id": tid, "english": english, "chinese": chinese,
                        "category": category["chinese"], "url": url,
                    }
    if not entries:
        raise DatabankError("unexpected_response", "无法识别该分类的条目索引")
    return list(entries.values())


def search_key(label):
    normalized = unicodedata.normalize("NFKC", label).casefold()
    return "".join(char for char in normalized if char.isalnum())


def match_strength(word, entry):
    english = entry["english"]
    names = [english, entry["chinese"]]
    if "," in english:
        surname, rest = english.split(",", 1)
        names.append(f"{rest} {surname}")
    keys = [search_key(name) for name in names]
    if word in keys:
        return "exact"
    return "related" if any(word in key for key in keys) else None


def search(keyword, category_name, limit):
    word = search_key(keyword)
    wanted = search_key(category_name) if category_name else None
    sections = categories()
    if wanted:
        sections = [
            item for item in sections
            if wanted in (search_key(item["chinese"]), search_key(item["english"]))
        ]
    if not sections:
        raise DatabankError("unknown_category", "找不到该分类，可用 categories 查看分类")

    results = []
    errors = []
    with ThreadPoolExecutor(max_workers=min(len(sections), 3)) as workers:
        jobs = [workers.submit(category_entries, item) for item in sections]
        for category, job in zip(sections, jobs):
            try:
                for entry in job.result():
                    match = match_strength(word, entry)
                    if match:
                        results.append({**entry, "match": match})
            except DatabankError as error:
                errors.append({"category": category["chinese"], **error.details()})
    results.sort(key=lambda entry: entry["match"] != "exact")
    status = "ok" if results else "not_found"
    if errors:
        status = "error" if len(errors) == len(sections) else "partial"
    return {
        "query": keyword, "category": category_name, "status": status,
        "total": len(results), "results": results[:limit], "errors": errors,
    }


def in_databank(breadcrumb):
    if breadcrumb is None:
        return False
    for anchor in breadcrumb.descendants("a"):
        url = site_link(anchor.attrs.get("href") or "")
        if url is None:
            continue
        if re.fullmatch(r"/forum-19-[0-9]+\.html", url.path):
            return True
        if url.path == "/forum.php" and parse_qs(url.query).get("fid") == ["19"]:
            return True
    return False


def read(tid, offset, max_chars):
    url = thread_url(tid)
    page = fetch_page(url)
    title = page.regions.get("thread_subject")
    post = next(page.posts(), None)
    if title is None or post is None:
        raise DatabankError("unexpected_response", "无法识别该条目的标题或正文")
    if not in_databank(page.regions.get("pt")):
        raise DatabankError("not_databank_entry", "该主题不在资料库版块")

    lines = [line.strip() for line in post.text().splitlines()]
    content = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    if not content:
        raise DatabankError("unexpected_response", "原帖未返回可读取的正文文字")
    if offset > len(content):
        raise DatabankError("offset_out_of_range", "起始位置超出正文长度")
    end = offset + max_chars
    return {
        "status": "ok", "entry": {"id": tid, "title": title.label(), "url": url},
        "offset": offset, "next_offset": end if end < len(content) else None,
        "content_length": len(content), "content": content[offset:end],
    }


def main():
    parser = argparse.ArgumentParser(description="查询星球大战中文网资料库。")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("categories", help="列出原站的资料库分类")
    search_args = commands.add_parser("search", help="检索索引中的中英文条目")
    search_args.add_argument("keyword", help="中文或英文词条")
    search_args.add_argument("--category", help="原站分类的中文或英文名称")
    search_args.add_argument("--limit", type=int, default=10, help="最多返回多少条结果")
    read_args = commands.add_parser("read", help="读取条目主帖的文字正文")
    read_args.add_argument("entry", help="条目 ID 或星球大战中文网的论坛链接")
    read_args.add_argument("--offset", type=int, default=0, help="从正文的哪个字符开始")
    read_args.add_argument("--max-chars", type=int, default=8000, help="最多返回多少字符")
    args = parser.parse_args()

    start_update_check()
    try:
        if args.command == "categories":
            result = {"status": "ok", "categories": categories()}
        elif args.command == "search":
            if not search_key(args.keyword) or (args.category is not None and not search_key(args.category)):
                parser.error("词条和类别须包含文字或数字")
            if not 1 <= args.limit <= 100:
                parser.error("--limit 必须在 1 到 100 之间")
            result = search(args.keyword, args.category, args.limit)
        else:
            tid = thread_id(args.entry.strip())
            if not tid:
                parser.error("请提供条目 ID 或星球大战中文网的论坛链接")
            if args.offset < 0 or not 1 <= args.max_chars <= 20000:
                parser.error("--offset 必须为非负数，--max-chars 必须在 1 到 20000 之间")
            result = read(tid, args.offset, args.max_chars)
    except DatabankError as error:
        result = {"status": "error", **error.details()}

    print(json.dumps({"source": SOURCE, **result, **take_update_notice()}, ensure_ascii=False, indent=2))
    return int(result["status"] in ("partial", "error"))


if __name__ == "__main__":
    raise SystemExit(main())
