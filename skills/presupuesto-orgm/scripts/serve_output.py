#!/usr/bin/env python3
from __future__ import annotations

import argparse
import functools
import http.server
import socketserver

from common import OUTPUT


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve presupuesto output folder")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUTPUT))
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as server:
        print(f"serving {OUTPUT} at http://127.0.0.1:{args.port}/")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
