#!/usr/bin/env python3
"""Serves the MatePad Mini landscape preview at http://localhost:8000.

The page is only the image: the launcher screen inside the tablet bezel, with
no captions, header or footer.

    python3 tools/preview_server.py
    python3 tools/preview_server.py --port 9000
"""
from __future__ import annotations

import argparse
import http.server
import os
import posixpath
import socketserver
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
SHOT = "preview-tablet.png"

PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PokeLauncher</title>
<style>
  html, body { margin: 0; min-height: 100%; }
  body {
    min-height: 100vh;
    display: grid; place-items: center;
    padding: clamp(8px, 2.5vw, 28px);
    background: #ffffff;
  }
  img {
    display: block;
    max-width: 100%;
    max-height: calc(100vh - 2 * clamp(8px, 2.5vw, 28px));
    width: auto; height: auto;
  }
</style>
</head>
<body>
<img src="/docs/__SHOT__" alt="PokeLauncher di MatePad Mini">
</body>
</html>
"""


class PreviewHandler(http.server.BaseHTTPRequestHandler):
    """Serves the page and the one render, nothing else."""

    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        path = urllib.parse.urlsplit(self.path).path

        if path in ("/", "/index.html"):
            self.respond(PAGE.replace("__SHOT__", SHOT).encode("utf-8"), "text/html; charset=utf-8")
            return

        if path.startswith("/docs/") and posixpath.basename(path) == SHOT:
            file_path = os.path.join(DOCS, SHOT)
            if os.path.exists(file_path):
                self.respond(open(file_path, "rb").read(), "image/png")
                return

        self.send_error(404, "Not found")

    def respond(self, body: bytes, content_type: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        # the Arena preview embeds this page in an iframe from another origin
        self.send_header("Content-Security-Policy", "frame-ancestors *")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:  # quieter output
        sys.stderr.write(f"  {self.address_string()} {fmt % args}\n")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args(argv)

    if not os.path.exists(os.path.join(DOCS, SHOT)):
        raise SystemExit("render dulu: python3 tools/render_tablet.py")

    with Server((args.host, args.port), PreviewHandler) as httpd:
        print(f"MatePad Mini preview: http://localhost:{args.port}/")
        print(f"  menyajikan: docs/{SHOT}")
        print("  Ctrl+C untuk berhenti")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nberhenti")


if __name__ == "__main__":
    main(sys.argv[1:])
