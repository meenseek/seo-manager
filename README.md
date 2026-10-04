# SEO Manager

A reusable SEO agent skill with an offline HTML inspector. One shared method can
support several products while each product keeps its content, configuration,
priorities and results.

The skill covers technical inspection, search intent and content maintenance,
AI-search evidence, Naver and measurement. The Python tool checks saved HTML and
response headers; it does not crawl sites, render JavaScript, access accounts,
publish content or schedule work.

## Use the skill

Clone this repository and load [SKILL.md](SKILL.md) in your agent. It requires no
model API or subscription. For Codex, install the repository as a skill folder:

```sh
git clone https://github.com/meenseek/seo-manager.git
mkdir -p ~/.codex/skills
ln -s "$(pwd)/seo-manager" ~/.codex/skills/seo-manager
```

Check for an existing file or link before installation; reuse the same target or
choose another installation location rather than replacing it. New Codex chats
can discover the skill after installation. Invoke `$seo-manager`, or ask for an
SEO audit and specify the product and allowed work. Update the source checkout
with `git pull --ff-only` when it has no local changes; the link needs no reinstall.
Remove only the skill link to uninstall; the checkout remains intact. Other agents
can read the same skill and references directly.

## Apply to a product

Use the same installed skill from the product's workspace; do not copy it into
each product. Give the agent the target repository or site and the allowed work:

- `$seo-manager Audit this site's public pages. Report confirmed issues before making changes.`
- `$seo-manager Fix the confirmed canonical issue in this product and run its required checks.`
- `$seo-manager Compare SEO issues across these named products and keep each result with its owner.`

Read the selected product's local rules before choosing pages or changing files.
Authenticated pages, private user data and deliberately excluded pages retain
their product-owned boundaries. A product can span multiple repositories; keep
each change with the repository that owns the affected behavior.

An existing work coordinator can read this repository's `SKILL.md` and use the
same inspector while retaining the selected product and authorization. Register
connections in that coordinator; this public repository keeps no product list,
campaign inventory or credentials. For direct use, no coordinator is required.

## Inspect a saved response

Requires Python 3.11+ and no third-party packages. Capture a public page that is
within your permitted scope, retaining its final response headers and effective
URL. For example, from the repository root:

```sh
capture_dir="$(mktemp -d)"
curl --location --max-redirs 5 --max-time 20 --max-filesize 2097152 \
  --proto '=https' --proto-redir '=https' \
  --dump-header "$capture_dir/headers.txt" --output "$capture_dir/page.html" \
  --write-out '%{url_effective}\n' https://example.com/ > "$capture_dir/url.txt"
python3 scripts/audit_html.py \
  --url "$(cat "$capture_dir/url.txt")" \
  --html "$capture_dir/page.html" --headers "$capture_dir/headers.txt" \
  --expect-indexing index
rm -r "$capture_dir"
```

Run the inspector only if the capture succeeded. Save captures and results in the
product's approved evidence location if they are needed after the audit. The
tool writes JSON to stdout and never edits the input files.

Use `--expect-indexing noindex` for intentionally excluded pages, or omit the
option when intent is unknown. `--crawler` selects `googlebot` (default), `bingbot`
or another bot's robots directives. `--expected-canonical` compares the HTML
canonical with an explicitly chosen absolute URL.

Checks distinguish `pass`, `fail`, `review` and `unknown`. Exit code **1** means a
check failed; **2** means invalid input; **0** means no failed checks, including
reports that still require review or contain unknowns. It is never a site-wide
SEO grade. HTTP status, title, description, robots directives, HTML canonical and
JSON-LD syntax are checked. H1 count and hreflang links are observations.

Inputs are decoded as UTF-8 (replacement characters are reported). The tool does
not verify capture provenance, robots.txt, sitemap coverage, HTTP Link canonicals,
rendered DOM, hreflang reciprocity, schema eligibility or actual indexing. Follow
the skill's references for those checks.

## Validate changes

From a fresh clone, using only Python:

```sh
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/audit_html.py
python3 scripts/audit_html.py --help
```

CI runs these checks on Python 3.11 and 3.14. Tests cover intentional exclusions,
crawler-specific directives, redirects, canonical resolution, malformed data,
missing evidence and the real CLI. They verify inspector behavior, not search
performance. Review new skill behavior with a representative product request
before publishing substantial workflow changes.

## Ownership and provenance

This is a shared work tool, with no product runtime dependency or central campaign
database. Product adapters and credentials remain outside this public repository.
The first implementation needs neither a web service nor an account integration.

Selected methods are adapted from
[Fire Your SEO Agency](https://github.com/leopard627/fire-your-seo-agency), with
dated corrections and MIT attribution in [NOTICE.md](NOTICE.md). See
[LICENSE](LICENSE) for the license. Claims about search platforms must be checked
again when they affect a recommendation; the verification date is not a promise
of continued validity.
