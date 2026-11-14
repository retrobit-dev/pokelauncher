#!/usr/bin/env python3
"""Serves the MatePad preview, with the map editor on a side route.

    python3 tools/preview_server.py            # preview at http://localhost:8000
    python3 tools/preview_server.py --port 9000

Routes
  /                     the tablet, with mode tabs (gameplay / map editor)
  /?mode=editor         the same page, opened straight into the editor
  /device               the same render (kept for old links)
  /editor               the map editor (grid of 16x16 tiles filling the screen)
  /editor/app.js        editor logic
  /editor/app.css       editor styles
  /docs/tileset/*       the tileset atlas and its index, read by the palette
  /api/map              the current map, saved by the editor
  /api/publish          copies that map to the game's assets, so gameplay
                        mode shows what was drawn (the editor does this on save)
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
FIELD = os.path.join(DOCS, "editor", "field.png")

# The map the editor works on. Kept out of git: it is the artist's document,
# and the game will get its own export format later.

# What the game actually loads. `Mode gameplay` must show the map drawn in the
# editor, so publishing copies the document here; the two files are different
# on purpose, because one is a working document and the other ships in the APK.
GAME_MAP_PATH = os.path.join(ROOT, "app", "src", "main", "assets", "tileset", "map.json")

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
  :root {
    --pad: clamp(4px, 1.4vw, 18px);
    --ink: #2c3a40;
    --sky-deep: #9fd2e6;
    --paper: #fbf3dc;
    --btn: #f7e7bd;
    --btn-on: #2c3a40;
  }
  body {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--pad);
    padding: var(--pad);
    box-sizing: border-box;
    min-height: 100dvh;
  }

  /* The device shot keeps the space it can have, the tabs sit under it. */
  #stage {
    flex: 1 1 auto;
    min-height: 0;
    width: 100%;
    display: grid;
    place-items: center;
  }

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
    max-width: 100%;
    max-height: 100%;
    width: auto;
    height: auto;
    image-rendering: pixelated;
    image-rendering: crisp-edges; /* Firefox */
  }

  /* ---------------------------------------------------------- the tabs
     Two modes, side by side *above* the tablet, with icons only so the row
     stays one short line on a wide screen. Not a <select>: the point is to see
     both options at once. aria-pressed says which one is on, so the state is
     readable by a screen reader and not only by colour; the names live in
     aria-label and title. */
  nav {
    flex: 0 0 auto;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    justify-content: center;
  }
  nav button {
    /* One square icon button, the same flat line glyphs the editor's own tool
       bar uses: no text, no emoji, so the row never reflows and the two rows
       read as the same control surface. */
    display: grid;
    place-items: center;
    width: 40px;
    height: 40px;
    font-size: 17px;
    line-height: 1;
    color: var(--ink);
    background: var(--btn);
    border: 2px solid var(--ink);
    border-radius: 9px;
    padding: 0;
    cursor: pointer;
  }
  nav button[aria-pressed="true"] {
    background: var(--btn-on);
    color: var(--paper);
  }
  nav button:focus-visible { outline: 3px solid #1f6f8b; outline-offset: 3px; }

  /* Rendering the tablet takes ~40 s. Say so, instead of looking frozen. */
  #render-state {
    align-self: center;
    font: 500 13px/1 ui-sans-serif, system-ui, sans-serif;
    color: var(--ink);
    background: rgba(255, 255, 255, .55);
    border-radius: 999px;
    padding: 6px 12px;
    min-height: 0;
  }
  #render-state:empty { display: none; }
  #render-state[data-state="rendering"]::before { content: "⟳ Menyiapkan tampilan dari peta editor…"; }

  /* The editor replaces the tablet, maximised: it needs the room. */
  body[data-mode="editor"] #stage { place-items: stretch; }
  body[data-mode="editor"] img { display: none; }
  #editor { display: none; width: 100%; height: 100%; border: 0; background: var(--paper); }
  body[data-mode="editor"] #editor { display: block; }
</style>
</head>
<body data-mode="game">
  <!-- The mode tabs sit above the tablet: they switch what the screen shows,
       so they belong on the chrome, not inside the device. -->
  <nav aria-label="Mode tampilan">
    <!-- Icons only, and simple ones: the same glyph family as the editor's
         toolbar (a screen, a pencil) rather than colourful emoji, which render
         differently on every system and dwarf the 40px buttons. The names live
         in aria-label and title, so a screen reader still says what each does. -->
    <button id="mode-game" aria-pressed="true" aria-label="Mode gameplay" title="Mode gameplay">
      <span aria-hidden="true">▣</span>
    </button>
    <button id="mode-editor" aria-pressed="false" aria-label="Mode map editor" title="Mode map editor">
      <span aria-hidden="true">✎</span>
    </button>
    <span id="render-state" data-state="__RENDERING__" role="status"></span>
  </nav>

  <div id="stage">
    <img src="/docs/__SHOT__?v=__STAMP__" alt="PokeLauncher di MatePad Mini"
         width="2772" height="1812">
    <iframe id="editor" src="/editor" title="Editor peta" loading="lazy"></iframe>
  </div>

<script>
  (function () {
    var params = new URLSearchParams(location.search);
    var body = document.body;
    var gameBtn = document.getElementById('mode-game');
    var editorBtn = document.getElementById('mode-editor');

    function show(mode, updateUrl) {
      body.dataset.mode = mode;
      gameBtn.setAttribute('aria-pressed', String(mode === 'game'));
      editorBtn.setAttribute('aria-pressed', String(mode === 'editor'));
      if (updateUrl) {
        // replaceState, not pushState: switching modes is not navigation, and
        // the back button should leave the preview, not walk through tabs.
        var url = new URL(location.href);
        if (mode === 'editor') url.searchParams.set('mode', 'editor');
        else url.searchParams.delete('mode');
        history.replaceState(null, '', url);
      }
    }

    gameBtn.addEventListener('click', function () { show('game', true); });
    editorBtn.addEventListener('click', function () { show('editor', true); });

    // Deep link: /?mode=editor opens straight into the editor.
    if (params.get('mode') === 'editor') show('editor', false);

    // A background render was started for this load: come back once for the
    // finished shot instead of leaving a half-truth on screen. One reload, not
    // a poll loop, and never while the editor is open.
    if (document.getElementById('render-state').dataset.state === 'rendering') {
      setTimeout(function () {
        if (document.body.dataset.mode === 'game') location.reload();
      }, 42000);
    }
  })();
</script>
</body>
</html>
"""


class PreviewHandler(http.server.BaseHTTPRequestHandler):
    """Serves the device preview, the editor, the tileset and the render."""

    # A re-render takes tens of seconds, so it is shared state: two page loads
    # must not start two renders, and the tabs show whether one is running.
    _render_lock = __import__("threading").Lock()
    _rendering = False

    # -- routing -------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        path = urllib.parse.urlsplit(self.path).path

        if path in ("/", "/index.html", "/device", "/device.html"):
            # The front page is the device, not the editor: the preview exists
            # to show what the app looks like, and the editor is a tool you go
            # looking for. /device stays as an alias so old links keep working.
            self.refresh_shot()
            page = (DEVICE_PAGE
                    .replace("__SHOT__", SHOT)
                    .replace("__STAMP__", _stamp())
                    .replace("__RENDERING__", self.render_state()))
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
                if name == "map.json":
                    # Serve exactly the map the game loads, not a separate
                    # working copy. The editor used to read docs/tileset/map.json
                    # while the game read the APK asset, so the two could show
                    # different maps until someone pressed Simpan: the editor
                    # was honest about one file and gameplay about another.
                    # /api/map still writes the working document (it is the
                    # editor's draft), but every read - editor included - comes
                    # from the file the app actually loads.
                    target = GAME_MAP_PATH
                self.send_file(target, kind)
                return
        if path == "/docs/tileset/player.png":
            # The spawn marker in the editor is the app's own walk sheet, so the
            # editor shows the character the game shows. Allowed by name, not by
            # prefix: this server exposes a short list of files, never a folder.
            self.send_file(
                os.path.join(ROOT, "app", "src", "main", "assets", "sprites", "player.png"),
                "image/png",
            )
            return
        if path == "/docs/" + SHOT:
            self.send_file(os.path.join(DOCS, SHOT), "image/png")
            return

        self.send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        path = urllib.parse.urlsplit(self.path).path
        if path == "/api/publish":
            self.publish_map()
            return
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

        # Write the file the game loads, not a separate draft.
        #
        # There used to be two: the editor saved docs/tileset/map.json and
        # /api/publish copied it into the APK. Between the two, the editor showed
        # one map and gameplay showed another - a map could look finished in the
        # editor and still be empty in the game, or worse, the game could keep
        # showing an older map than the one on screen. One file, written once,
        # removes the whole class of bug.
        if os.path.exists(GAME_MAP_PATH):
            try:
                os.replace(GAME_MAP_PATH, GAME_MAP_PATH + ".bak")
            except OSError:
                pass
        os.makedirs(os.path.dirname(GAME_MAP_PATH), exist_ok=True)
        with open(GAME_MAP_PATH, "w", encoding="utf-8") as handle:
            json.dump(document, handle)
            handle.write("\n")
        self.respond(json.dumps({"ok": True, "bytes": len(body)}).encode("utf-8"),
                     "application/json")

    def publish_map(self) -> None:
        """Confirm the saved map is one the game can read.

        Saving already writes the file the app loads, so there is nothing left
        to copy: this checks the document round-trips through the same rules the
        game uses, and reports a bad map here instead of as a blank screen later.
        """
        if not os.path.exists(GAME_MAP_PATH):
            self.respond(json.dumps({"ok": False, "error": "belum ada peta tersimpan"}).encode("utf-8"),
                         "application/json")
            return
        try:
            with open(GAME_MAP_PATH, encoding="utf-8") as handle:
                document = json.load(handle)
            if not isinstance(document.get("cells"), dict):
                raise ValueError("peta tidak punya objek 'cells'")
            if not isinstance(document.get("cols"), int) or not isinstance(document.get("rows"), int):
                raise ValueError("peta tidak punya cols/rows")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            self.respond(json.dumps({"ok": False, "error": str(error)}).encode("utf-8"),
                         "application/json")
            return
        self.respond(json.dumps({"ok": True}).encode("utf-8"), "application/json")

    def refresh_shot(self) -> None:
        """Re-renders the tablet shot when the map it was drawn from changed.

        `Mode gameplay` has to show the map from the editor. The render is a
        Python script, so there are two honest options: ask the user to run it,
        or run it here. Running it here is what makes the promise true without a
        second terminal.

        It runs *in the background*, behind a class-wide lock: a full render is
        ~40 s on this panel, and blocking the page request for that long looks
        exactly like a broken preview. The page serves the current shot now and
        the next load serves the new one; the tabs carry the re-render state so
        the wait is visible instead of mysterious.
        """
        source = GAME_MAP_PATH
        try:
            newest = max(os.path.getmtime(source), os.path.getmtime(FIELD))
            shot = os.path.join(DOCS, SHOT)
            if os.path.exists(shot) and os.path.getmtime(shot) >= newest:
                with PreviewHandler._render_lock:
                    PreviewHandler._rendering = False
                return
        except OSError:
            return

        with PreviewHandler._render_lock:
            if PreviewHandler._rendering:
                return
            PreviewHandler._rendering = True

        import subprocess
        import threading

        tools = os.path.join(ROOT, "tools")

        def work() -> None:
            try:
                for command in (
                    [sys.executable, os.path.join(tools, "mock_ingame.py"), "--field"],
                    [sys.executable, os.path.join(tools, "render_tablet.py")],
                ):
                    subprocess.run(command, cwd=ROOT, check=True,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                   timeout=300)
            except (subprocess.SubprocessError, OSError):
                # A failed re-render must not take the preview down: the old
                # shot is still a better answer than an error page.
                pass
            finally:
                with PreviewHandler._render_lock:
                    PreviewHandler._rendering = False

        threading.Thread(target=work, daemon=True).start()

    @classmethod
    def render_state(cls) -> str:
        with cls._render_lock:
            return "rendering" if cls._rendering else "ready"

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
        print(f"  tileset: docs/tileset/  map: {os.path.relpath(GAME_MAP_PATH, ROOT)}")
        print("  Ctrl+C untuk berhenti")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nberhenti")


if __name__ == "__main__":
    main(sys.argv[1:])
