"""Experimental fixed-source RSS adapter; importing and parsing never fetch data."""

from datetime import datetime, timedelta, timezone
import hashlib
from http.client import HTTPException
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from xml.etree import ElementTree


SOURCE_URL = "https://www.federalreserve.gov/feeds/press_all.xml"
MAX_BYTES = 512 * 1024
MAX_ITEMS = 100
SECONDS = 10
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
PUBLICATION_DATE = re.compile(
    rf"({'|'.join(WEEKDAYS)}), ([0-9]{{1,2}}) "
    rf"({'|'.join(MONTHS)}) ([0-9]{{4}}) "
    r"([01][0-9]|2[0-3]):([0-5][0-9]):([0-5][0-9]) "
    r"(GMT|[+-](?:[01][0-9]|2[0-3])[0-5][0-9])"
)


class _FeedError(ValueError):
    """Only fixed adapter messages, never source content or transport exceptions."""


def _record(status, error=None, digest=None, items=None):
    return {"source_url": SOURCE_URL, "status": status, "error": error,
            "sha256": digest, "retrieved_at": None, "requests_attempted": 0,
            "items": items if items is not None else []}


def _text(parent, name):
    fields = parent.findall(name)
    if len(fields) != 1 or len(fields[0]) or not (fields[0].text or "").strip():
        raise _FeedError("Required RSS field is missing, duplicated or not plain text.")
    value = fields[0].text.strip()
    if "<" in value or ">" in value:
        raise _FeedError("Required RSS field contains markup.")
    return value


def _item(element):
    title, link, date = (_text(element, field) for field in ("title", "link", "pubDate"))
    if (not re.fullmatch(r"https://www\.federalreserve\.gov/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+", link)
            or any(part in {".", ".."} for part in link.split("/")[3:])):
        raise _FeedError("Item link is not a canonical Board HTTPS URL.")
    try:
        match = PUBLICATION_DATE.fullmatch(date)
        if not match:
            raise ValueError
        weekday, day, month, year, hour, minute, second, zone = match.groups()
        zone_info = timezone.utc
        if zone != "GMT":
            if zone == "-0000":
                raise ValueError
            offset = timedelta(hours=int(zone[1:3]), minutes=int(zone[3:5]))
            zone_info = timezone(-offset if zone[0] == "-" else offset)
        published = datetime(int(year), MONTHS.index(month) + 1, int(day),
                             int(hour), int(minute), int(second), tzinfo=zone_info)
        if WEEKDAYS[published.weekday()] != weekday:
            raise ValueError
        published = published.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        raise _FeedError("Item publication date is invalid or lacks a timezone.") from None
    return {"title": title, "url": link, "published_at": published.isoformat()}


def parse_feed(raw):
    """Parse bounded UTF-8 bytes into a JSON-compatible record; no partial items."""
    if not isinstance(raw, bytes):
        return _record("invalid", "Feed input must be bytes.")
    if len(raw) > MAX_BYTES:
        return _record("invalid", "Feed exceeds 512 KiB.")
    digest = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8-sig")
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.IGNORECASE):
            raise _FeedError("DTD and entity declarations are forbidden.")
        declaration = re.search(r"<\?xml\b[^?]*\bencoding\s*=\s*(['\"])(.*?)\1", text)
        if declaration and declaration[2].lower() not in {"utf-8", "utf8"}:
            raise _FeedError("Feed must declare UTF-8 encoding.")
        root = ElementTree.fromstring(text)
        if root.tag != "rss" or root.attrib != {"version": "2.0"} or len(root) != 1 or root[0].tag != "channel":
            raise _FeedError("Expected RSS 2.0 with exactly one channel.")
        if any("}" in element.tag for element in root.iter()):
            raise _FeedError("Namespaced elements are outside this RSS profile.")
        channel = root[0]
        for field in ("title", "link", "description"):
            _text(channel, field)
        entries = channel.findall("item")
        if len(entries) != sum(1 for _ in root.iter("item")):
            raise _FeedError("RSS items must be direct children of the channel.")
        if len(entries) > MAX_ITEMS:
            raise _FeedError("Feed exceeds 100 items.")
        items = [_item(entry) for entry in entries]
    except _FeedError as error:
        return _record("invalid", str(error), digest)
    except (UnicodeError, ElementTree.ParseError, ValueError, RecursionError):
        return _record("invalid", "Invalid UTF-8 RSS document.", digest)
    return _record("available" if items else "empty", digest=digest, items=items)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_feed():
    """Attempt one fixed HTTPS request; socket timeout and checks around reads.

    This is not a hard DNS/process deadline. No redirects, retries, credentials,
    environment proxy configuration, or item-URL requests are used.
    """
    deadline = time.monotonic() + SECONDS
    request = Request(SOURCE_URL, headers={"Accept": "application/rss+xml, application/xml, text/xml",
                      "Accept-Encoding": "identity", "User-Agent": "skylit-agent-lab/experimental-fed-feed"})
    try:
        with build_opener(ProxyHandler({}), _NoRedirect()).open(request, timeout=SECONDS) as response:
            if response.status != 200 or response.geturl() != SOURCE_URL:
                raise _FeedError("Unexpected HTTP response; redirects are forbidden.")
            length = getattr(response, "headers", {}).get("Content-Length")
            if length is not None and (not re.fullmatch(r"[0-9]{1,10}", length) or int(length) > MAX_BYTES):
                raise _FeedError("Invalid or oversized HTTP response length.")
            chunks, size = [], 0
            while True:
                if time.monotonic() >= deadline:
                    raise _FeedError("Feed elapsed-time budget exceeded.")
                chunk = response.read1(min(65536, MAX_BYTES + 1 - size))
                if time.monotonic() >= deadline:
                    raise _FeedError("Feed elapsed-time budget exceeded.")
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_BYTES:
                    raise _FeedError("Feed exceeds 512 KiB.")
                chunks.append(chunk)
            if length is not None and size != int(length):
                raise _FeedError("Incomplete or mismatched HTTP response length.")
            retrieved = datetime.now(timezone.utc).isoformat()
        result = parse_feed(b"".join(chunks))
        result["retrieved_at"] = retrieved
    except _FeedError as error:
        result = _record("unavailable", str(error))
    except HTTPError as error:
        error.close()
        result = _record("unavailable", "HTTP request failed; no retry sent.")
    except TimeoutError:
        result = _record("unavailable", "Feed request timed out; no retry sent.")
    except (URLError, OSError, HTTPException):
        result = _record("unavailable", "Feed connection failed; no retry sent.")
    result["requests_attempted"] = 1
    return result
