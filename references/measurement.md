# Measurement

Record the baseline before a planned change when outcome comparison matters.
Use the product's existing measurement owner. Keep page/query data, exports and
audit history outside this public tool repository.

Define the relevant metric, unit, subject, dimensions, source, observation period
and retrieval time. Search impressions, clicks, CTR and average position describe
different things from product activation or revenue. Compare compatible report
types and dimensions; note missing access, incomplete periods and data lag.

Choose a follow-up window from indexing latency, traffic volume and the hypothesis.
A 14-day comparison may be useful for some sites, but is not a universal deadline.
Do not claim a follow-up is scheduled unless it actually is. Recurring monitoring
requires the user's request and the owning environment's scheduling mechanism.

Separate implementation validation from indexing, visibility and conversion
outcomes. Compare like periods and cohorts; record seasonality, query mix and
concurrent changes. Describe an uncontrolled before/after difference as an
association. Do not promise indexing, ranking or AI citations.

For AI answer samples, retain the question, platform/mode, observed time and cited
URLs. A `site:` result count or crawler visit count is not a reliable census of
indexed pages or proof of citation improvement. Evaluate data freshness alongside
the value; missing or failed retrieval is not a measured zero.

## Verify analytics collection

For analytics setup or repair, distinguish saved configuration, a tag present on
the deployed page, an event sent, and that event received by the intended reporting
destination. A successful save or tag-quality badge does not establish collection.
Confirm the intended account, property/stream and site, then use a real page visit
and the provider's supported diagnostics to trace an expected event such as
`page_view` through sending and receipt. Keep the URL, observation time, destination
and result in the product's existing record. Do not manufacture collection requests
or count unrelated/pre-existing events as proof of the test visit.

If no event is sent, inspect deployed configuration, duplicate initialization,
console/diagnostic errors, consent state and browser or network restrictions before
attributing the result to reporting delay. Check conflicting cookie flags and
domain/expiry settings against current official documentation. An error observed
in one browser is evidence about that test environment; verify a suspected cause
after repair instead of generalizing it to every visitor.

Prefer the product's supported platform integration. If a confirmed integration
defect requires replacing it, make the change in the product owner, preserve the
authorized measurement/privacy scope, and remove the old path to avoid duplicate
events. Keep synthetic/local previews from sending production analytics. Inspect
the deployed page and repeat the real-visit test after the change.

When destination access or receipt cannot be verified, report exactly which stage
passed and leave collection unverified. Record the blocker and next verification
condition; a processing-delay estimate is not evidence of eventual receipt.

## Official sources

Verified 2026-10-04; recheck when used:

- [Search Console performance report](https://support.google.com/webmasters/answer/7576553)
- [Google AI search guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)

Analytics sources verified 2026-10-05; recheck when used:

- [GA4 Realtime report](https://support.google.com/analytics/answer/9271392)
- [GA4 DebugView](https://support.google.com/analytics/answer/7201382)
- [Tag Assistant](https://support.google.com/tagmanager/answer/10039345)
- [Google tag cookie customization](https://developers.google.com/tag-platform/security/guides/customize-cookies)

Adapted from upstream `references/measure.md`; see [NOTICE.md](../NOTICE.md).
