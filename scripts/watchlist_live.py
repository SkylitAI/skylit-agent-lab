"""Plan a bounded Kit watchlist; only --live reads a local key or calls Skylit."""

import argparse
import codecs
import html
import importlib
import json
import locale
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup_watchlist import KIT_REVISION, ROOT, SetupError, checkout_revision


def load_client(path):
    root = Path(path).resolve()
    git_path = shutil.which("git")
    if not git_path:
        raise SetupError("Git is required to verify the pinned Kit checkout.")
    if checkout_revision(root, "Kit", git_path=git_path) != KIT_REVISION:
        raise SetupError(f"Kit revision must be {KIT_REVISION}.")
    sys.path.insert(0, str(root))
    client = importlib.import_module("skylit_agent_kit.watchlist")
    cli = importlib.import_module("skylit_agent_kit.watchlist_cli")
    if any(Path(module.__file__).resolve() != root / "skylit_agent_kit" / name
           for module, name in ((client, "watchlist.py"), (cli, "watchlist_cli.py"))):
        raise SetupError("Imported Kit does not match --kit; use a fresh Python process.")
    return client, cli


def output_path(value):
    root = ROOT / "reports"
    path = Path(value).absolute() if value else root / "live-watchlist.md"
    if (root.is_symlink() or path.is_symlink() or path.resolve() == root.resolve()
            or not path.resolve().is_relative_to(root.resolve())):
        raise SetupError("Choose a new --output file inside this Lab checkout's reports directory.")
    if path.exists():
        raise SetupError("Output already exists; choose a new --output filename.")
    if not path.name or not path.name.isprintable():
        raise SetupError("Choose a printable --output filename.")
    if any(parent.exists() and not parent.is_dir() for parent in path.parents):
        raise SetupError("Output parent is not a directory.")
    str(path).encode(sys.stdout.encoding or "utf-8")
    return path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    parser.add_argument("--symbols", default="SPY")
    parser.add_argument("--max-credits", type=int, default=3)
    parser.add_argument("--max-requests", type=int, default=5)
    parser.add_argument("--max-seconds", type=float, default=30)
    parser.add_argument("--output", help="New Markdown file inside Lab reports/; never overwritten")
    args = parser.parse_args(argv)
    try:
        if codecs.lookup(locale.getpreferredencoding(False)).name != "utf-8":
            raise SetupError("UTF-8 is required; rerun with python3 -X utf8 -I -B ...")
        kit, cli = load_client(args.kit)
        plan = kit.make_plan(args.symbols)
        if args.max_credits < 0 or args.max_requests < 2 or not kit.number(args.max_seconds) or not 1 <= args.max_seconds <= 3600:
            raise SetupError("Use nonnegative credits, at least 2 requests and a finite 1–3600 second cap.")
        print(f"Plan: {', '.join(plan['symbols'])}; {plan['requests']} requests; {plan['credits']} documented credits.")
        print(f"Caps: {args.max_requests} requests; {args.max_credits} credits; {args.max_seconds:g} seconds. No retries or automatic increases.")
        if plan['requests'] > args.max_requests or plan['credits'] > args.max_credits:
            raise SetupError("Estimated plan exceeds the caps; no credentials read or requests sent.")
        if not args.live:
            print("DRY RUN: no credentials read, network calls or report written. Add --live only for an authorized run.")
            return 0
        destination = output_path(args.output)
        result = kit.execute_live(cli.credential(), symbols=plan['symbols'],
                                  max_credits=args.max_credits, max_requests=args.max_requests,
                                  max_seconds=args.max_seconds, save_raw=True)
        report = kit.render_report(result)
        report += "\n\nData: [Skylit](https://www.skylit.ai/). Preserve source notices; attribution does not grant redistribution rights.\n"
        notices = [{"source": item["url"], "meta": item["response"].get("meta")}
                   for item in result["raw"] if item["response"].get("meta") is not None]
        if notices:
            report += "\n## Source metadata and notices\n\n<pre>" + html.escape(json.dumps(notices, ensure_ascii=False, indent=2)) + "</pre>\n"
        cli.save_private(destination, report)
        print(f"Saved private live-path report: {destination}")
        print("This path has mocked verification only; account billing and authenticated service behavior remain unverified.")
        return 0 if result["stop"] == "completed" else 2
    except KeyboardInterrupt:
        print("Cancelled; no retry was sent. A request already started may have an unknown outcome.", file=sys.stderr)
        return 130
    except (ValueError, OSError, ImportError) as error:
        if isinstance(error, (SetupError, ValueError)) and not isinstance(error, UnicodeError):
            print(f"error: {error}", file=sys.stderr)
        else:
            print("error: Check the pinned Kit, UTF-8 output path and directory permissions. No retry was sent.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
