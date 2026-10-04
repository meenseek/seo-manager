import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_html.py"
spec = importlib.util.spec_from_file_location("audit_html", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

HTML = '''<!doctype html><html><head><title>Useful page</title>
<meta name="description" content="A useful description">
<link rel="canonical" href="https://example.com/page">
</head><body><h1>Useful page</h1><p>A real answer.</p></body></html>'''
HEADERS = "HTTP/2 200\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"


def check(report, name):
    return next(item for item in report["checks"] if item["check"] == name)


class ResponseTests(unittest.TestCase):
    def run_audit(self, html=HTML, headers=HEADERS, **kwargs):
        return audit.inspect(html, "https://example.com/page", headers, **kwargs)

    def test_intended_public_page(self):
        report = self.run_audit(expect_indexing="index", expected_canonical="https://example.com/page")
        self.assertFalse(any(c["status"] == "fail" for c in report["checks"]))
        self.assertEqual(report["observations"]["h1_count"], 1)

    def test_intentional_meta_exclusion_and_public_regression(self):
        html = HTML.replace("</head>", '<meta name="ROBOTS" content="NOINDEX, nofollow"></head>')
        self.assertEqual(check(self.run_audit(html, expect_indexing="noindex"), "noindex_matches_intent")["status"], "pass")
        self.assertEqual(check(self.run_audit(html, expect_indexing="index"), "noindex_matches_intent")["status"], "fail")

    def test_none_alias_and_restrictive_repeated_tags(self):
        html = HTML.replace("</head>", '<meta name="robots" content="index"><meta name="googlebot" content="none"></head>')
        self.assertEqual(check(self.run_audit(html, expect_indexing="index"), "noindex_matches_intent")["status"], "fail")

    def test_meta_for_another_crawler_is_not_applied(self):
        html = HTML.replace("</head>", '<meta name="bingbot" content="noindex"></head>')
        self.assertEqual(check(self.run_audit(html, expect_indexing="index"), "noindex_matches_intent")["status"], "pass")
        self.assertEqual(check(self.run_audit(html, crawler="bingbot", expect_indexing="index"), "noindex_matches_intent")["status"], "fail")

    def test_repeated_and_crawler_qualified_headers(self):
        headers = HEADERS + "X-Robots-Tag: bingbot: noindex\nX-Robots-Tag: googlebot: nofollow\n"
        self.assertEqual(check(self.run_audit(headers=headers, expect_indexing="index"), "noindex_matches_intent")["status"], "pass")
        headers += "X-Robots-Tag: googlebot: max-snippet: 20, noindex\n"
        self.assertEqual(check(self.run_audit(headers=headers, expect_indexing="index"), "noindex_matches_intent")["status"], "fail")

    def test_crawler_switch_in_a_single_header(self):
        headers = HEADERS + "X-Robots-Tag: googlebot: nofollow, bingbot: noindex\n"
        self.assertEqual(check(self.run_audit(headers=headers, expect_indexing="index"), "noindex_matches_intent")["status"], "pass")
        self.assertEqual(check(self.run_audit(headers=headers, crawler="bingbot", expect_indexing="index"), "noindex_matches_intent")["status"], "fail")

    def test_date_commas_do_not_hide_trailing_noindex(self):
        for prefix in ['', 'googlebot: ']:
            for directives in [
                'unavailable_after: Wed, 03 Dec 2025 13:00:00 GMT, noindex',
                'noindex, unavailable_after: Wed, 03 Dec 2025 13:00:00 GMT',
                'unavailable_after: Wednesday, 03-Dec-25 13:00:00 GMT, noindex',
                'unavailable_after: 2025-12-03T13:00:00Z, noindex',
            ]:
                headers = HEADERS + 'X-Robots-Tag: ' + prefix + directives + '\n'
                self.assertEqual(check(self.run_audit(headers=headers, expect_indexing='index'), 'noindex_matches_intent')['status'], 'fail')

    def test_parameter_none_is_not_standalone_none(self):
        for directives in ['max-image-preview: none', 'max-image-preview:none']:
            html = HTML.replace('</head>', '<meta name="robots" content="' + directives + '"></head>')
            headers = HEADERS + 'X-Robots-Tag: googlebot: ' + directives + '\n'
            self.assertEqual(check(self.run_audit(html=html, headers=headers, expect_indexing='index'), 'noindex_matches_intent')['status'], 'pass')
            headers += 'X-Robots-Tag: none\n'
            self.assertEqual(check(self.run_audit(html=html, headers=headers, expect_indexing='index'), 'noindex_matches_intent')['status'], 'fail')

    def test_only_final_redirect_headers_are_used(self):
        headers = "HTTP/1.1 301 Moved\nX-Robots-Tag: noindex\nLocation: /page\n\n" + HEADERS
        report = self.run_audit(headers=headers, expect_indexing="index")
        self.assertEqual(check(report, "http_status")["evidence"]["status"], 200)
        self.assertEqual(check(report, "noindex_matches_intent")["status"], "pass")

    def test_failed_response_is_not_a_pass(self):
        report = self.run_audit(headers="HTTP/2 503\nContent-Type: text/html\n", expect_indexing="index")
        self.assertEqual(check(report, "http_status")["status"], "fail")

    def test_missing_headers_and_unknown_product_intent(self):
        report = self.run_audit(headers=None, expect_indexing="index")
        self.assertEqual(check(report, "http_status")["status"], "unknown")
        self.assertEqual(check(report, "noindex_matches_intent")["status"], "unknown")
        self.assertEqual(check(self.run_audit(), "noindex_matches_intent")["status"], "review")

    def test_missing_noindex_on_excluded_page(self):
        self.assertEqual(check(self.run_audit(expect_indexing="noindex"), "noindex_matches_intent")["status"], "fail")

    def test_canonical_uses_html_base_and_rel_tokens(self):
        html = HTML.replace('<link rel="canonical" href="https://example.com/page">',
                            '<base href="https://example.com/docs/"><link rel="alternate CANONICAL" href="page">')
        result = check(self.run_audit(html, expected_canonical="https://example.com/docs/page"), "html_canonical")
        self.assertEqual(result["status"], "pass")

    def test_deliberate_other_canonical_is_supported(self):
        html = HTML.replace('href="https://example.com/page"', 'href="https://example.com/master"')
        self.assertEqual(check(self.run_audit(html, expected_canonical="https://example.com/master"), "html_canonical")["status"], "pass")

    def test_conflicting_empty_and_invalid_canonical(self):
        for extra in ['<link rel="canonical" href="/other">', '<link rel="canonical" href="">']:
            self.assertEqual(check(self.run_audit(HTML.replace("</head>", extra + "</head>")), "html_canonical")["status"], "fail")
        html = HTML.replace('href="https://example.com/page"', 'href="javascript:alert(1)"')
        self.assertEqual(check(self.run_audit(html), "html_canonical")["status"], "review")
        self.assertEqual(check(self.run_audit(html, expected_canonical="https://example.com/page"), "html_canonical")["status"], "fail")

    def test_body_metadata_is_not_treated_as_head(self):
        html = HTML.replace("</body>", '<title>Extra body title</title><link rel="canonical" href="/wrong"></body>')
        report = self.run_audit(html)
        self.assertEqual(check(report, "html_title")["evidence"], ["Useful page"])
        self.assertEqual(check(report, "html_canonical")["status"], "pass")

    def test_body_robots_is_respected(self):
        html = HTML.replace("</body>", '<meta name="robots" content="noindex"></body>')
        self.assertEqual(check(self.run_audit(html, expect_indexing="index"), "noindex_matches_intent")["status"], "fail")

    def test_inert_template_is_not_page_metadata(self):
        html = HTML.replace("</head>", '<template><meta name="robots" content="noindex"><title>Template</title><script type="application/ld+json">invalid</script></template></head>')
        report = self.run_audit(html, expect_indexing="index")
        self.assertEqual(check(report, "noindex_matches_intent")["status"], "pass")
        self.assertEqual(check(report, "html_title")["evidence"], ["Useful page"])
        self.assertEqual(check(report, "json_ld_syntax")["status"], "review")

    def test_json_ld_syntax_in_head_and_body(self):
        for data in ['{"@type":"Article"}', '{"@type":']:
            html = HTML.replace("</body>", '<script type="application/ld+json">' + data + '</script></body>')
            result = check(self.run_audit(html), "json_ld_syntax")
            self.assertEqual(result["status"], "pass" if data.endswith("}") else "fail")

    def test_unclosed_json_ld_is_reported(self):
        html = HTML + '<script type="application/ld+json">{"@type":"Article"}'
        self.assertEqual(check(self.run_audit(html), "json_ld_syntax")["status"], "fail")

    def test_non_json_numeric_literals_are_rejected(self):
        for literal in ['NaN', 'Infinity', '-Infinity']:
            html = HTML.replace("</body>", '<script type="application/ld+json">{"value":' + literal + '}</script></body>')
            self.assertEqual(check(self.run_audit(html), "json_ld_syntax")["status"], "fail")


class CLITests(unittest.TestCase):
    def run_cli(self, html=HTML.encode(), headers=HEADERS, extra=()):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            page = root / "page.html"
            page.write_bytes(html)
            response = root / "headers.txt"
            response.write_text(headers)
            before = page.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), "--url", "https://example.com/page",
                                     "--html", str(page), "--headers", str(response), *extra],
                                    capture_output=True, text=True)
            self.assertEqual(page.read_bytes(), before)
            return result

    def test_real_cli_emits_hashes_and_produces_no_mutations(self):
        result = self.run_cli(extra=["--expect-indexing", "index"])
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["source"]["html_sha256"], hashlib.sha256(HTML.encode()).hexdigest())
        self.assertIn("analyzed_at", report)

    def test_failure_exit_code(self):
        self.assertEqual(self.run_cli(extra=["--expect-indexing", "noindex"]).returncode, 1)

    def test_custom_crawler_prefix_matches_cli_token_contract(self):
        for crawler in ['360spider', '_custom', '-custom']:
            result = self.run_cli(headers=HEADERS + 'X-Robots-Tag: ' + crawler + ': noindex\n',
                                  extra=['--expect-indexing', 'index', '--crawler=' + crawler])
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertTrue(check(json.loads(result.stdout), 'noindex_matches_intent')['evidence']['observed_noindex'])

    def test_input_error_exit_code(self):
        result = self.run_cli(extra=["--expected-canonical", "file:///etc/passwd"])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")

    def test_lossy_decode_requires_review(self):
        result = self.run_cli(html=HTML.encode() + b"\xff")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)["source"]["utf8_replacement_used"])

    def test_size_bound_is_enforced(self):
        self.assertEqual(self.run_cli(html=b"x" * (audit.MAX_INPUT_BYTES + 1)).returncode, 2)


if __name__ == "__main__":
    unittest.main()
