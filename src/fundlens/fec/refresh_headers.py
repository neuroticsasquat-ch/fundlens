"""Refresh the vendored FEC header files from FEC's data dictionaries (`task fec:headers`).

    python -m fundlens.fec.refresh_headers           # overwrite headers/*.csv with FEC's copies
    python -m fundlens.fec.refresh_headers --check   # exit 1 if any differs, writing nothing

The one place fundlens fetches the dictionaries; the pipeline and the tests read only the
vendored copies. After a refresh changes a file, update its columns in `files.CATALOGUE`
(`tests/unit/test_fec_files.py` fails until they agree).
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
        live = fetch(base_url, file.header_file)
        vendored = HEADERS_DIR / file.header_file
        if vendored.exists() and columns(vendored.read_bytes()) == columns(live):
            print(f"{file.header_file}: unchanged")
            continue
        stale.append(file.header_file)
        if args.check:
            print(f"{file.header_file}: differs from FEC's")
        else:
            vendored.write_bytes(live)
            print(f"{file.header_file}: updated")
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    sys.exit(main())
