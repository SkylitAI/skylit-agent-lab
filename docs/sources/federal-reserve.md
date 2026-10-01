# Experimental Federal Reserve press feed

[`scripts/fed_press_feed.py`](../../scripts/fed_press_feed.py) extracts release
titles, canonical Board links and UTC publication times for a future Market
Brief consumer. It is an experimental Lab adapter, separate from Watchlist and
its run-record schema. There is no CLI, renderer, model call or order feature.
A shared maintained adapter belongs in Kit after review and graduation; this
implementation does not change Kit or complete runner integration.

## Source and reuse

The fixed source is the Board's
[All Press Releases RSS feed](https://www.federalreserve.gov/feeds/press_all.xml),
listed in its [feed directory](https://www.federalreserve.gov/feeds/feeds.htm).
The Board's [terms](https://www.federalreserve.gov/disclaimer.htm), checked on
2026-10-01, state that website information is generally public domain unless
otherwise indicated and request attribution to the Board. Indicated restrictions
still apply; copying non-Board material may require permission from its source.
Seals and logos require separate written permission. Attribution identifies the
source and must not imply Board endorsement of this adapter or its consumers.

[`fed-press-synthetic.xml`](../../examples/fed-press-synthetic.xml) is independently
authored fictional test data dedicated under CC0-1.0. Its titles, dates and release
paths are invented; it contains no copied release text or logo. The links mimic
the source's format and are never visited by tests or the adapter.

## Parse locally

From the repository root, this command reads only the fictional fixture:

```sh
python3 - <<'PY'
import json
from pathlib import Path
from scripts.fed_press_feed import parse_feed
result = parse_feed(Path('examples/fed-press-synthetic.xml').read_bytes())
print(json.dumps(result, indent=2))
PY
```

`parse_feed(bytes)` accepts at most 512 KiB of strict UTF-8, optionally with a BOM.
The profile requires namespace-free RSS 2.0, one channel, and nonblank plain-text
channel title/link/description. At most 100 items may occur, directly under that
channel. Every item must have exactly one nonblank plain-text title, canonical
HTTPS link on `www.federalreserve.gov`, and timezone-aware RSS publication date.
Links have no credentials, port, query, fragment, encoded path or dot segments.
The accepted date profile is `Wdy, D Mon YYYY HH:MM:SS GMT` or the same form
with a signed four-digit `+/-HHMM` offset: English three-letter weekday/month,
one or two day digits, four year digits, and two digits per time/offset component.
Hours must be 00–23 and minutes/seconds 00–59; calendar dates must be valid.
Trailing text, shortened or overflowing offsets, and the unknown `-0000` zone
are rejected. Dates are converted to UTC without substituting a retrieval time.
Titles retain decoded text; nested or escaped markup is rejected. DTD/entity
declarations are forbidden; standard XML escaping such as `&amp;` remains valid.

The returned dictionary is JSON-compatible:

| Field | Meaning |
|---|---|
| `status` | `available` for valid items; `empty` for a valid zero-item channel; `invalid` for a rejected body; `unavailable` for a failed or incomplete fetch. |
| `items` | Ordered objects with only `title`, `url`, and `published_at`. Publication times are aware UTC ISO timestamps. No descriptions, categories or raw HTML are returned. |
| `source_url` | The fixed feed URL, separate from each release URL. |
| `sha256` | SHA-256 of the exact complete supplied/received bytes, including any BOM. Null when bytes exceed the cap or a fetch is incomplete. |
| `retrieved_at` | Actual UTC completion time for a fully received fetch, even if parsing fails. Null for local parsing or an incomplete fetch. |
| `requests_attempted` | Zero for parsing alone; one for an explicit fetch attempt, including a failed attempt. |
| `error` | A fixed adapter error for invalid/unavailable results; otherwise null. Source text and raw transport exceptions are excluded. |

Any invalid required item rejects the **whole feed**: status is `invalid` and
`items` is empty. There is no partial-success record or silent item dropping.
An invalid or unavailable result therefore cannot be mistaken for a valid empty
release list. Consumers must check status before using items. All titles remain
untrusted data, including text resembling instructions. A later consumer must
escape text for its rendering context; parsing grants no execution authority.

## Explicit fetching

Only calling `fetch_feed()` attempts network access. It sends one HTTPS GET to
the fixed URL with no credentials, redirects, retries, item fetches or environment
proxy configuration. It requests uncompressed bytes and requires HTTP 200 from
the exact URL. A supplied Content-Length must match the received body. It reads
at most 512 KiB plus one byte to detect overflow; incomplete or oversized responses
expose no hash or release records.

The socket timeout is 10 seconds, with elapsed-budget checks before and after
each read. This is **not a hard DNS or process deadline**: DNS resolution and a
blocking I/O operation can extend wall-clock time beyond the nominal budget.
Callers requiring hard cancellation need a separately reviewed execution boundary.
The feed is public and this adapter has no paid API or model calls; ordinary
network access is still required for fetching.

## Verification and limits

The focused synthetic suite exercises shape, required fields, dates, links,
byte/item caps, XML declarations, transport failures, redirects, elapsed checks,
request counts and exact-byte hashing on Python 3.11 and 3.14:

```sh
python3.11 -m unittest discover -s tests -p 'test_fed_press_feed.py' -v
python3.14 -m unittest discover -s tests -p 'test_fed_press_feed.py' -v
```

A separate format check parsed an existing temporary official response captured
at `2026-10-01T22:11:49.036791+00:00`: HTTP 200, 14,678 bytes, 20 items, SHA-256
`f216afb03d2abd0dffbfab6f2657229c6c6be55c52e1d1cb331c2acc6b3d077b`.
That response is not committed, and local parsing does not invent a new retrieval
time. The adapter's own transport is covered by mocks, not a new live request.
These checks do not establish ongoing availability, freshness, completeness of
all Board releases, host compatibility, or current Watchlist schema acceptance.
Market Brief integration and a reviewed record extension remain separate work.
