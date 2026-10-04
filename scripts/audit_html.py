#!/usr/bin/env python3
"""Inspect saved HTML and HTTP headers without network access or file mutation."""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

MAX_INPUT_BYTES = 2 * 1024 * 1024
PARAMETER_DIRECTIVES = {
    "max-snippet", "max-image-preview", "max-video-preview", "unavailable_after"
}


def web_url(value):
    try:
        parsed = urlsplit(value)
        parsed.port
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or any(c.isspace() for c in value)):
            raise ValueError
    except ValueError:
        raise ValueError("expected an absolute HTTP(S) URL without credentials") from None
    return value


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_head = False
        self.in_title = False
        self.titles = []
        self.descriptions = []
        self.robots = []
        self.canonicals = []
        self.hreflang = []
        self.base = None
        self.h1_count = 0
        self.json_ld = []
        self.ld_parts = None
        self.template_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "template":
            self.template_depth += 1
        if self.template_depth:
            return
        attrs = {k.lower(): v or "" for k, v in attrs}
        if tag == "head":
            self.in_head = True
        if tag == "h1":
            self.h1_count += 1
        if tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self.ld_parts = []
        if tag == "meta" and attrs.get("name"):
            self.robots.append((attrs["name"].lower(), attrs.get("content", "")))
        if not self.in_head:
            return
        if tag == "title":
            self.titles.append([])
            self.in_title = True
        elif tag == "base" and self.base is None and "href" in attrs:
            self.base = attrs["href"]
        elif tag == "meta":
            name = attrs.get("name", "").lower()
            if name == "description":
                self.descriptions.append(attrs.get("content", ""))
        elif tag == "link":
            rel = attrs.get("rel", "").lower().split()
            if "canonical" in rel:
                self.canonicals.append(attrs.get("href", ""))
            if "alternate" in rel and "hreflang" in attrs:
                self.hreflang.append({"language": attrs["hreflang"], "href": attrs.get("href", "")})

    def handle_endtag(self, tag):
        if tag == "template" and self.template_depth:
            self.template_depth -= 1
            return
        if self.template_depth:
            return
        if tag == "head":
            self.in_head = False
            self.in_title = False
        elif tag == "title":
            self.in_title = False
        elif tag == "script" and self.ld_parts is not None:
            self.json_ld.append("".join(self.ld_parts))
            self.ld_parts = None

    def handle_data(self, data):
        if self.template_depth:
            return
        if self.in_title:
            self.titles[-1].append(data)
        if self.ld_parts is not None:
            self.ld_parts.append(data)


def response_headers(text):
    """Use the last response in a curl -D capture, retaining repeated headers."""
    status = None
    headers = {}
    for line in text.splitlines():
        match = re.match(r"^HTTP/\S+\s+(\d{3})(?:\s|$)", line, re.IGNORECASE)
        if match:
            status = int(match.group(1))
            headers = {}
        elif ":" in line:
            name, value = line.split(":", 1)
            headers.setdefault(name.strip().lower(), []).append(value.strip())
    return status, headers


def bare_directives(part):
    # Parameter values such as max-image-preview: none are not standalone rules.
    return re.split(r"\s+", part.strip()) if ":" not in part else []


def header_directives(values, crawler):
    directives = []
    for value in values:
        target = None
        for part in value.lower().split(","):
            part = part.strip()
            match = re.match(r"^([a-z0-9_-]+)\s*:\s*(.*)$", part)
            if match and match[1] not in PARAMETER_DIRECTIVES:
                target = match[1]
                part = match[2]
            if target is None or target == crawler:
                directives.extend(bare_directives(part))
    return directives


def inspect(html, url, headers=None, crawler="googlebot", expect_indexing=None,
            expected_canonical=None):
    web_url(url)
    if expected_canonical:
        web_url(expected_canonical)
    crawler = crawler.lower()
    page = Page()
    page.feed(html)
    page.close()
    checks = []

    def add(name, status, evidence):
        checks.append({"check": name, "status": status, "evidence": evidence})

    status, fields = response_headers(headers) if headers is not None else (None, {})
    add("http_status", "unknown" if status is None else "pass" if status == 200 else "fail",
        {"status": status, "scope": "final saved response"})
    titles = [" ".join("".join(t).split()) for t in page.titles]
    add("html_title", "pass" if len(titles) == 1 and titles[0] else "review", titles)
    add("html_description", "pass" if len(page.descriptions) == 1 and page.descriptions[0].strip()
        else "review", page.descriptions)

    meta = [content for name, content in page.robots if name in {"robots", crawler}]
    directives = [d for content in meta for part in content.lower().split(",")
                  for d in bare_directives(part)]
    xrobots = fields.get("x-robots-tag", [])
    directives += header_directives(xrobots, crawler)
    excluded = any(d in {"noindex", "none"} for d in directives)
    if expect_indexing is None:
        indexing = "review"
    elif excluded:
        indexing = "pass" if expect_indexing == "noindex" else "fail"
    elif status is None:
        indexing = "unknown"
    else:
        indexing = "pass" if expect_indexing == "index" else "fail"
    add("noindex_matches_intent", indexing, {
        "expected": expect_indexing, "crawler": crawler, "observed_noindex": excluded,
        "meta": meta, "x_robots_tag": xrobots, "headers_available": status is not None,
        "scope": "saved HTML and supplied headers; not proof of indexing"
    })

    base = urljoin(url, page.base) if page.base is not None else url
    canonicals = [urljoin(base, href.strip()) if href.strip() else "" for href in page.canonicals]
    try:
        valid_canonical = len(canonicals) == 1 and bool(web_url(canonicals[0]))
    except ValueError:
        valid_canonical = False
    canonical_status = "pass" if valid_canonical else "review"
    if len(set(canonicals)) > 1:
        canonical_status = "fail"
    if expected_canonical is not None:
        canonical_status = "pass" if valid_canonical and canonicals[0] == expected_canonical else "fail"
    add("html_canonical", canonical_status, {
        "observed": canonicals, "expected": expected_canonical, "scope": "HTML head only"
    })

    errors = []
    def reject_constant(value):
        raise ValueError("non-JSON numeric literal: " + value)

    for number, raw in enumerate(page.json_ld, 1):
        try:
            json.loads(raw, parse_constant=reject_constant)
        except (ValueError, RecursionError) as exc:
            errors.append({"block": number, "error": str(exc)})
    if page.ld_parts is not None:
        errors.append({"block": len(page.json_ld) + 1, "error": "unclosed JSON-LD script"})
    add("json_ld_syntax", "fail" if errors else "pass" if page.json_ld else "review", {
        "blocks": len(page.json_ld), "errors": errors, "scope": "JSON syntax; no schema validation"
    })
    return {
        "url": url, "crawler": crawler, "checks": checks,
        "observations": {"h1_count": page.h1_count, "hreflang": page.hreflang},
        "limitations": ["No network or JavaScript rendering", "No robots.txt or sitemap inspection",
                        "No HTTP Link canonical or hreflang reciprocity validation",
                        "No schema eligibility or indexing/ranking/citation verdict",
                        "Capture time and provenance not verified"]
    }


def read_input(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        raise ValueError("each input must be at most 2 MiB")
    try:
        return raw.decode("utf-8-sig"), hashlib.sha256(raw).hexdigest(), False
    except UnicodeDecodeError:
        return raw.decode("utf-8-sig", errors="replace"), hashlib.sha256(raw).hexdigest(), True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="effective response URL, absolute HTTP(S)")
    parser.add_argument("--html", required=True, help="saved UTF-8 HTML file")
    parser.add_argument("--headers", help="saved curl -D headers, including HTTP status lines")
    parser.add_argument("--crawler", default="googlebot", help="crawler token for robots directives")
    parser.add_argument("--expect-indexing", choices=["index", "noindex"])
    parser.add_argument("--expected-canonical", help="explicit expected absolute canonical URL")
    args = parser.parse_args(argv)
    try:
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", args.crawler):
            raise ValueError("crawler must be a single bot token")
        html, html_hash, html_lossy = read_input(args.html)
        headers, headers_hash, headers_lossy = read_input(args.headers) if args.headers else (None, None, False)
        report = inspect(html, args.url, headers, args.crawler, args.expect_indexing, args.expected_canonical)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    report["analyzed_at"] = datetime.now(timezone.utc).isoformat()
    report["source"] = {"html_sha256": html_hash, "headers_sha256": headers_hash,
                        "utf8_replacement_used": html_lossy or headers_lossy}
    if html_lossy or headers_lossy:
        report["checks"].append({"check": "input_encoding", "status": "review",
                                 "evidence": "invalid UTF-8 decoded with replacement characters"})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if any(c["status"] == "fail" for c in report["checks"]) else 0


if __name__ == "__main__":
    sys.exit(main())
