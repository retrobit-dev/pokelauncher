#!/usr/bin/env python3
"""Serves the MatePad preview, with the map editor on a side route.

    python3 tools/preview_server.py            # preview at http://localhost:8000
    python3 tools/preview_server.py --port 9000

Routes
  /                     the MatePad Mini render, and nothing else
  /device               the same render (kept for old links)
  /editor               the map editor (grid of 16x16 tiles filling the screen)
  /editor/app.js        editor logic
  /editor/app.css       editor styles
  /docs/tileset/*       the tileset atlas and its index, read by the palette
  /api/map              the current map, saved by the editor
                        (GET map.json falls back to the map shipped in the APK
                        when no document has been saved yet)
  /docs/preview-tablet.png   the device render

Only these paths are reachable; nothing else in the repo is exposed.
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import posixpath
import socketserver
import sys
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
EDITOR = os.path.join(ROOT, "editor")
SHOT = "preview-tablet.png"

# The map the editor works on. Kept out of git: it is the artist's document,
# and the game will get its own export format later.
MAP_PATH = os.path.join(ROOT, "docs", "tileset", "map.json")

def _stamp() -> str:
    """The render's mtime, so a page load always asks for the current bitmap.

    `Cache-Control: no-store` covers the browser, but the preview pane can be a
    long-lived iframe: without a changing URL it keeps the bitmap it decoded
    when it mounted, and a fresh render looks like it never happened.
    """
    path = os.path.join(DOCS, SHOT)
    try:
        return str(int(os.path.getmtime(path)))
    except OSError:
        return "0"


DEVICE_PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PokeLauncher</title>
<style>
  /* The page is the bright margin around the device. The render already carries
     that same sky-blue border, so the image sits on the page with no seam. */
  html, body { margin: 0; height: 100%; background: #bfe3f2; }
  body {
    display: grid;
    place-items: center;
    padding: clamp(4px, 1.5vw, 18px);
  }
  :root { --pad: clamp(4px, 1.5vw, 18px); }

  /*
   * A 2772px render on a ~1400px pane is a 2x downscale, and a browser's
   * default smoothing turns 128px pixel-art cells into mush: the sprite reads
   * as a blurry blob. `pixelated` keeps the pixels square at any ratio.
   *
   * The box is also pinned to whole render pixels: 2772 is 4 x 693 and
   * 1812 is 4 x 453, so a width in `px` that is a multiple of 4 (or a
   * fractional 2x device pixel ratio of one) never lands a resize on a half
   * pixel. `max-width` alone would let the width float freely.
   */
  img {
    display: block;
    width: min(100%, calc((100dvh - 2 * var(--pad)) * 2772 / 1812));
    height: auto;
    image-rendering: pixelated;
    image-rendering: crisp-edges; /* Firefox */
  }
  @media (min-width: 1900px) {
    /* Plenty of room: never blow the shot up past 1:1, it only gets softer. */
    img { width: min(100%, 2772px); }
  }
</style>
</head>
<body>
<img src="/docs/__SHOT__?v=__STAMP__" alt="PokeLauncher di MatePad Mini"
     width="2772" height="1812">
</body>
</html>
"""


class PreviewHandler(http.server.BaseHTTPRequestHandler):
    """Serves the device preview, the editor, the tileset and the render."""

    # -- routing -------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        path = urllib.parse.urlsplit(self.path).path

        if path in ("/", "/index.html", "/device", "/device.html"):
            # The front page is the device, not the editor: the preview exists
            # to show what the app looks like, and the editor is a tool you go
            # looking for. /device stays as an alias so old links keep working.
            page = (DEVICE_PAGE
                    .replace("__SHOT__", SHOT)
                    .replace("__STAMP__", _stamp()))
            self.respond(page.encode("utf-8"), "text/html; charset=utf-8")
            return
        if path in ("/editor", "/editor/", "/editor/index.html"):
            self.send_file(os.path.join(EDITOR, "index.html"), "text/html; charset=utf-8")
            return
        if path.startswith("/editor/"):
            name = posixpath.basename(path)
            if name in ("app.js", "app.css"):
                kind = "text/javascript; charset=utf-8" if name.endswith(".js") \
                    else "text/css; charset=utf-8"
                self.send_file(os.path.join(EDITOR, name), kind)
                return
        if path.startswith("/docs/tileset/"):
            name = posixpath.basename(path)
            if name in ("johto-tileset.png", "tileset.json", "map.json"):
                kind = "image/png" if name.endswith(".png") else "application/json"
                target = os.path.join(DOCS, "tileset", name)
                if name == "map.json" and not os.path.exists(target):
                    # No working document yet: open the map the app ships, so the
                    # editor starts from the real village instead of a blank lawn.
                    target = os.path.join(ROOT, "app", "src", "main", "assets",
                                          "tileset", "map.json")
                self.send_file(target, kind)
                return
        if path == "/docs/" + SHOT:
            self.send_file(os.path.join(DOCS, SHOT), "image/png")
            return

        self.send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        path = urllib.parse.urlsplit(self.path).path
        if path != "/api/map":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 4 * 1024 * 1024:
            self.send_error(413, "Payload too large")
            return
        body = self.rfile.read(length)
        try:
            document = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            self.respond(json.dumps({"ok": False, "error": str(error)}).encode("utf-8"),
                         "application/json")
            return

        # Keep the last good map around: a bad save must not destroy work.
        if os.path.exists(MAP_PATH):
            try:
                os.replace(MAP_PATH, MAP_PATH + ".bak")
            except OSError:
                pass
        os.makedirs(os.path.dirname(MAP_PATH), exist_ok=True)
        with open(MAP_PATH, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
            handle.write("\n")
        self.respond(json.dumps({"ok": True, "bytes": len(body)}).encode("utf-8"),
                     "application/json")

    # -- helpers -------------------------------------------------------
    def send_file(self, path: str, content_type: str) -> None:
        if not os.path.exists(path):
            self.send_error(404, "Not found")
            return
        # Read fresh on every request: the render is regenerated by a separate
        # process while this server keeps running, and a cached read would serve
        # yesterday's screenshot from a file that is correct on disk.
        with open(path, "rb") as handle:
            body = handle.read()
        try:
            mtime = int(os.path.getmtime(path))
        except OSError:
            mtime = 0
        self.respond(body, content_type, stamp=str(mtime))

    def respond(self, body: bytes, content_type: str, stamp: str = "") -> None:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, max-age=0")
        if stamp:
            self.send_header("ETag", f'"{stamp}"')
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

    if not os.path.exists(os.path.join(DOCS, "tileset", "johto-tileset.png")):
        raise SystemExit("tileset belum ada: python3 tools/tileset/build.py")

    with Server((args.host, args.port), PreviewHandler) as httpd:
        print(f"Johto map editor: http://localhost:{args.port}/")
        print(f"  pratinjau perangkat: /device")
        print(f"  tileset: docs/tileset/  map: {os.path.relpath(MAP_PATH, ROOT)}")
        print("  Ctrl+C untuk berhenti")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nberhenti")


if __name__ == "__main__":
    main(sys.argv[1:])
