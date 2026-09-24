# Changelog

This file is kept in English only. Release notes on the
[Releases page](https://github.com/MrMarkinBoladao/xml-sitemap-analyzer/releases)
are bilingual (English and Portuguese).

Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed
- `__version__` is now `1.0.0`, matching the `v1.0.0` tag. This also changes the
  default User-Agent to `sitemap-analyzer/1.0.0`.

### Added
- This changelog.
- MIT license. Until now the repository was public with no license, which by
  default means all rights reserved — nobody could legally reuse the code even
  though it was readable. A `LICENSE` file, an `SPDX-License-Identifier` header
  in `sitemap_analyzer.py` (so the license travels with the file when it is
  copied on its own) and a License section in both README languages.

## [1.0.0] - 2026-09-24

First release.

### Added
- Sitemap discovery from the `Sitemap:` line in `robots.txt`, falling back to
  10 well-known paths when none is declared.
- Recursive walking of nested `<sitemapindex>` documents, gzipped `.xml.gz`
  sitemaps, plain-text sitemaps and RSS/Atom feeds.
- Link-crawl fallback for sites with no sitemap, or whose declared sitemap
  cannot be read.
- Platform fingerprinting for roughly 25 stacks (WordPress, Shopify, Next.js,
  Drupal, Magento, Plone, Hugo and others) using HTML, HTTP headers,
  `robots.txt` and sitemap naming.
- Parallel page inspection extracting title, meta description, `h1`,
  `canonical`, language, HTTP status and size.
- Feed and JSON API probing.
- Grouped list output with a summary, a broken-page list and a warnings block.
- JSON and CSV export, with English field names.
- English output by default and `--lang pt` for Portuguese, covering the
  `--help` text as well as the report.
- `robots.txt` Disallow rules respected by default; blocked URLs are reported
  as skipped rather than fetched. `--ignore-robots` opts out.
- `analyze.bat` and `analisar.bat` double-click shortcuts for Windows.

### Notes on behavior
- Host redirects are followed before sitemap discovery, so `example.com`
  redirecting to `www.example.com` does not cause 404s on `robots.txt`.
- When a declared sitemap returns 403/404, the report states that it fell back
  to crawling instead of claiming the sitemap was used.
- Responses are capped at 600 KB, enough for metadata without downloading
  large binaries.
- On Windows, stdout is reconfigured to UTF-8 so redirecting output to a file
  does not corrupt non-ASCII characters, and ANSI colors are enabled on the
  console.

[Unreleased]: https://github.com/MrMarkinBoladao/xml-sitemap-analyzer/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/MrMarkinBoladao/xml-sitemap-analyzer/releases/tag/v1.0.0
