# Market Brief

Save a short, dated brief of Federal Reserve press releases. The default uses
the bundled fictional feed and requires no network, account, Kit or model.
This experimental package is maintained by `@prodij` and covers one source,
not a complete market view. T26 run-record sidecars and host verification remain
pending; this package writes only its Markdown brief.

Keep the package inside the full Lab checkout. From the Lab root, with Python
3.11 or later:

```sh
python3 -X utf8 -I -B experiments/market-brief/run.py
```

The default output is `experiments/market-brief/reports/brief.md`. Choose a new
output path for another run; existing files are never overwritten:

```sh
python3 -X utf8 -I -B experiments/market-brief/run.py --limit 1 --output /path/to/new-brief.md
python3 -X utf8 -I -B experiments/market-brief/run.py --input /path/to/saved-feed.xml --output /path/to/saved-input-brief.md
```

`--limit` accepts 1–20, defaults to 5, and selects the first entries in feed
order. It does not sort, summarize or infer relevance. `--input` identifies
caller-supplied saved bytes: Board-shaped links do not verify their provenance,
and their actual retrieval time remains unknown. Offline release URLs appear
as code text rather than clickable citations, including the invented URLs in
the default fixture. Publication timestamps are the adapter's exact UTC values,
separate from actual retrieval; no report clock stands in for either.

An explicit `--fetch` selects the adapter's fixed official URL and is mutually
exclusive with `--input`:

```sh
python3 -X utf8 -I -B experiments/market-brief/run.py --fetch --output /path/to/fetched-brief.md
```

This opt-in attempts at most one unauthenticated HTTPS request, with no redirects,
retries, item-page requests or model calls. It reuses the unchanged
[experimental adapter](../../scripts/fed_press_feed.py) and its 512 KiB/100-item
caps, socket timeout and elapsed checks. The 10-second budget is not a hard DNS
or process deadline. Only this path can report an observed actual retrieval time
and clickable Board release links. Package fetching is tested with mocks here;
an actual package fetch is a separate review step.

## Outcomes and files

| Exit | Meaning |
|---|---|
| 0 | Saved a valid brief, including a clearly stated zero-item feed. An empty feed does not prove there were no Board announcements. |
| 1 | Source invalid/unavailable: saved an explicit gap brief with no usable releases. Input or output failures stop the run. If stdout fails after saving, stderr identifies the saved report. |
| 2 | Invalid command arguments or an unusable output-path presentation; no output is created and no fetch starts. |

Local input must be a readable regular file of at most 512 KiB. Final input
symlinks, directories and FIFOs are rejected before a blocking read. Reports
are UTF-8, exclusively created with mode 0600 on POSIX, and never overwrite an
existing file or symlink. Output path components must not be symlinks; use a
canonical path where the OS provides directory aliases. Relative explicit paths
use the working directory; the default fixture/output use the package location.
These checks are not a filesystem sandbox against concurrent path replacement.
An output write or close failure can leave a partial report; inspect it and choose
a new path before rerunning. An unchanged bundled fixture is required for the
default fictional provenance label: its exact consumed bytes must match the
known SHA-256. Edited fixtures require explicit `--input` and use caller-supplied
provenance.

Titles are untrusted text. Punctuation is encoded as HTML character references
to prevent active Markdown links, images or formatting. Nonprintable characters,
including bidi controls, tabs and newlines, appear as visible `\uNNNN` or
`\UNNNNNNNN` code-point escapes; printable Unicode wording is preserved. This
encoding does not make semantic instructions safe for a later model consumer.
The report includes the hash of the exact accepted bytes when available, and
an explicit source status.

## Fixture and source

[`fixture.xml`](fixture.xml) is a byte-identical copy of the independently authored
[shared CC0 fixture](../../examples/fed-press-synthetic.xml). All titles, dates
and release paths are fictional; no Board release text or logo is copied.
The [source note](../../docs/sources/federal-reserve.md) documents the official
feed, Board attribution and reuse exceptions. Code is MIT licensed. Kit is
unused (`kit: null`); a maintained shared adapter requires reviewed graduation.

## Expected default brief

The following complete output is also the offline golden test. Character
references display as ordinary punctuation in rendered Markdown.

<!-- expected-start -->
```markdown
# Market Brief

Bundled fictional fixture: all release titles, dates and URLs below are invented.
Actual retrieval (UTC): unknown (offline input).

Source status: available. Showing 2 of 2 releases in feed order.
Requests attempted: 0. Model calls: 0.

### Published (UTC): 2020-01-01T12:00:00+00:00
Fictional notice&#58; paper kites &#38; sample calendars

Fictional URL (not a citation): `https://www.federalreserve.gov/newsevents/pressreleases/fictional20200101a.htm`

### Published (UTC): 2020-01-02T14:30:00+00:00
Fictional notice&#58; an imaginary meeting room

Fictional URL (not a citation): `https://www.federalreserve.gov/newsevents/pressreleases/fictional20200102a.htm`

Feed format reference: `https://www.federalreserve.gov/feeds/press_all.xml`.
Input SHA-256: `e2fc20b0b4aa3c7361250ba9f699355eddc28deb860b5a082bafc4a988bb0121`.
This covers one press-release feed; it is not a complete market view or a freshness guarantee.
```
<!-- expected-end -->

Run the package tests without network:

```sh
python3.11 -X utf8 -B -m unittest discover -s tests -p 'test_market_brief_runner.py' -v
python3.14 -X utf8 -B -m unittest discover -s tests -p 'test_market_brief_runner.py' -v
```
