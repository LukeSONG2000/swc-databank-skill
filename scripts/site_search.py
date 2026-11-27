#!/usr/bin/env python3
"""Search public forum threads through Star Wars China's own search form."""

import argparse
import json
import re
from urllib.parse import parse_qs, parse_qsl, urlencode

from databank import DatabankError, DatabankPage, SITE, fetch_page, site_link, thread_id, thread_url
from skill_update import start_update_check, take_update_notice


SEARCH_URL = f"{SITE}/search.php?mod=forum"
SOURCE = {"name": "星球大战中文网论坛搜索", "url": SEARCH_URL}


def forum_page(url):
    page = fetch_page(url, DatabankPage(("ct",)))
    content = page.regions.get("ct")
    if content is not None:
        nodes = list(content.descendants("div"))
        message = next((node for node in nodes if node.attrs.get("id") == "messagetext"), None)
        if message is not None:
            text = message.label().split("如果您的浏览器", 1)[0].strip()
            code = "rate_limited" if re.search(r"只能进行一次搜索|搜索过于频繁", text) else "search_unavailable"
            raise DatabankError(code, text or "论坛暂时无法处理搜索请求")
        for heading in content.descendants("h2"):
            count = re.search(r"相关内容\s*([0-9]+)\s*个", heading.label())
            if count is not None:
                return content, int(count[1])
    raise DatabankError("unexpected_response", "无法识别论坛搜索结果")


def pagination(content):
    controls = next((
        node for node in content.descendants("div")
        if "pg" in (node.attrs.get("class") or "").split()
    ), None)
    if controls is None:
        return None, 1
    links = []
    for anchor in controls.descendants("a"):
        url = site_link(anchor.attrs.get("href") or "")
        if url is None or url.path != "/search.php":
            continue
        params = parse_qs(url.query)
        page = params.get("page", [""])[0]
        if params.get("mod") == ["forum"] and params.get("searchid", [""])[0].isdigit() and page.isdigit():
            links.append((int(page), url))
    if not links:
        raise DatabankError("unexpected_response", "无法识别论坛搜索分页")
    last_page, template = max(links, key=lambda link: link[0])
    current = next(controls.descendants("strong"), None)
    if current is not None and current.label().isdigit():
        last_page = max(last_page, int(current.label()))
    return template, last_page


def threads(content):
    listing = next((
        node for node in content.descendants("div") if node.attrs.get("id") == "threadlist"
    ), None)
    results = []
    if listing is None:
        return results
    for item in listing.descendants("li"):
        heading = next(item.descendants("h3"), None)
        link = next(heading.descendants("a"), None) if heading is not None else None
        tid = thread_id(link.attrs.get("href") or "") if link is not None else None
        if tid is None or not link.label():
            continue

        entry = {
            "id": tid,
            "title": link.label(),
            "url": thread_url(tid),
        }
        paragraphs = list(item.descendants("p"))
        if len(paragraphs) >= 3:
            entry["snippet"] = paragraphs[1].label()
            footer = paragraphs[-1]
            posted_at = next(footer.descendants("span"), None)
            if posted_at is not None:
                entry["posted_at"] = posted_at.label()
            for anchor in footer.descendants("a"):
                if (anchor.attrs.get("href") or "").startswith(("forum-", "forum.php")):
                    entry["forum"] = anchor.label()
                    break
        results.append(entry)
    return results


def search(keyword, page, limit):
    query = urlencode({"srchtxt": keyword, "searchsubmit": "yes"})
    content, total = forum_page(f"{SEARCH_URL}&{query}")
    template, last_page = pagination(content)
    if page > last_page:
        raise DatabankError("page_out_of_range", f"页码超出搜索结果范围，最后一页为 {last_page}")
    if page > 1:
        params = dict(parse_qsl(template.query))
        params["page"] = page
        url = template._replace(scheme="https", query=urlencode(params), fragment="")
        content, total = forum_page(url.geturl())

    results = threads(content)
    if total and not results:
        raise DatabankError("unexpected_response", "论坛报告有搜索结果，但未能读取帖子")
    return {
        "status": "ok" if results else "not_found",
        "page": page, "last_page": last_page, "total": total, "results": results[:limit],
    }


def main():
    parser = argparse.ArgumentParser(description="在星球大战中文网论坛搜索帖子。")
    parser.add_argument("keyword", help="中文或英文关键词")
    parser.add_argument("--page", type=int, default=1, help="结果页码，从 1 开始")
    parser.add_argument("--limit", type=int, default=10, help="单页最多返回多少条帖子")
    args = parser.parse_args()
    keyword = args.keyword.strip()
    if not keyword:
        parser.error("关键词不能为空")
    if args.page < 1 or not 1 <= args.limit <= 30:
        parser.error("--page 必须大于等于 1，--limit 必须在 1 到 30 之间")

    start_update_check()
    try:
        result = search(keyword, args.page, args.limit)
    except DatabankError as error:
        result = {"status": "error", **error.details(), "results": []}
    print(json.dumps({
        "source": SOURCE, "query": keyword, **result, **take_update_notice(),
    }, ensure_ascii=False, indent=2))
    return int(result["status"] == "error")


if __name__ == "__main__":
    raise SystemExit(main())
