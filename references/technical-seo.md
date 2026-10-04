# Technical SEO

Inspect a representative intended public page and an intentionally excluded page
when available. Match findings to the product's expected behavior.

1. Record requested/effective URL, response time, status and response headers.
   Inspect HTML robots directives and `X-Robots-Tag` for the relevant crawler.
   Google also respects robots meta tags in the body; inspect them there too.
   Preserve intentional exclusions. A robots.txt block and a noindex instruction
   are different controls; blocked fetching can prevent discovery of a noindex.
2. Compare raw HTML with the rendered page where JavaScript matters. Inspect
   meaningful content, navigation, titles and metadata. An empty initial shell
   warrants rendering investigation; it does not prove Google cannot index it.
3. Inspect HTML and HTTP Link canonical signals, redirects, duplicate URL variants
   and the product's chosen canonical. Do not force self-canonicals on deliberate
   duplicates. Check reciprocal hreflang and actual locale URLs when applicable.
4. Review robots.txt for the intended bots and paths. Compare sitemap URLs with
   the product's intended indexable inventory; confirm reachable canonical pages
   and truthful lastmod dates. Absence of a sitemap alone is not an indexing verdict.
5. Verify meaningful HTTP responses for a known missing page and a temporary
   failure. Distinguish unavailable data from a genuinely absent resource.
6. Review readable, distinctive titles and descriptions for the audience and
   language. Record lengths as observations when useful, without universal
   character-count pass/fail thresholds.
7. Use structured data appropriate to actual visible content. The inspector checks
   JSON syntax only. Validate type-specific requirements and current feature
   eligibility separately; optional markup is not an indexing requirement.
8. Investigate measured performance, mobile usability and image accessibility
   when they affect the request. Do not prescribe preload or format changes
   without checking the assets and user flow.

The offline inspector reports its source scope explicitly. Review or unknown
results require judgment or more evidence; a report with no failed checks does
not certify a site. Capture evidence outside this public repository.

## Official sources

Verified 2026-10-04; recheck changing requirements when used:

- [Google JavaScript SEO basics](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
- [Google robots meta and X-Robots-Tag](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag)
- [Google canonical methods](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- [Google sitemap overview](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview)
- [Google localized versions](https://developers.google.com/search/docs/specialty/international/localized-versions)

Methods adapted from upstream `references/seo.md`; see [NOTICE.md](../NOTICE.md).
