"""Refresh the vendored FEC header files from FEC's data dictionaries (`task fec:headers`).

    python -m fundlens.fec.refresh_headers           # overwrite headers/*.csv with FEC's copies
    python -m fundlens.fec.refresh_headers --check   # exit 1 if any differs, writing nothing

The one place fundlens fetches the dictionaries; the pipeline and the tests read only the
vendored copies. After a refresh changes a file, update its columns in `files.CATALOGUE`
(`tests/unit/test_fec_files.py` fails until they agree). A header FEC publishes no file for
(`weball`, `webk`: `header_from_fec` false) was written from FEC's file description and is
skipped: a change there is made by hand.
"""

import argparse
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from fundlens.fec.files import CATALOGUE
from fundlens.settings import get_settings

HEADERS_DIR = Path(__file__).parent / "headers"
TIMEOUT_SECONDS = 30


def fetch(base_url: str, header_file: str) -> bytes:
    url = f"{base_url.rstrip('/')}/data_dictionaries/{header_file}"
    with urlopen(Request(url, headers={"User-Agent": "fundlens"}), timeout=TIMEOUT_SECONDS) as r:
        return r.read()


def columns(header: bytes) -> list[str]:
    # By column, not byte: FEC ends the line with CRLF, which a checkout may not preserve.
    return header.decode().strip().split(",")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh the vendored FEC header files.")
    parser.add_argument("--check", action="store_true", help="Compare only; write nothing.")
    args = parser.parse_args(argv)
    base_url = get_settings().fec_bulk_url
    stale: list[str] = []
    for file in CATALOGUE.values():
        header_file = file.header_file
        # A CSV's header row is in the file itself: there is nothing vendored to refresh.
        if header_file is None:
            continue
        if not file.header_from_fec:
            print(f"{header_file}: from FEC's file description, not refreshed")
            continue
        live = fetch(base_url, header_file)
        vendored = HEADERS_DIR / header_file
        if vendored.exists() and columns(vendored.read_bytes()) == columns(live):
            print(f"{header_file}: unchanged")
            continue
        stale.append(header_file)
        if args.check:
            print(f"{header_file}: differs from FEC's")
        else:
            vendored.write_bytes(live)
            print(f"{header_file}: updated")
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    sys.exit(main())
