#!/usr/bin/env python3
"""Renders the launcher inside EMUI 13 / HarmonyOS 4 system chrome.

The MatePad Mini runs HarmonyOS 4.3 (AOSP based, API 31). That UI reserves a
status bar at the top and a gesture navigation bar at the bottom, and the
launcher is drawn edge to edge behind both: `safeDrawingPadding()` in
LauncherScreen.kt keeps the content inside the safe area.

Insets used here are the HarmonyOS defaults converted at 3 px per dp:

    status bar        27 dp  ->  81 px
    gesture bar       16 dp  ->  48 px

Output: docs/preview-harmonyos.png (landscape) and
        docs/preview-harmonyos-portrait.png
"""
from __future__ import annotations

import os
import sys

import render_tablet as base

STATUS_BAR_DP = 27
GESTURE_BAR_DP = 16


def build(width: int, height: int) -> base.Canvas:
    device = base.Device(
        width,
        height,
        inset_top=base.dp(STATUS_BAR_DP),
        inset_bottom=base.dp(GESTURE_BAR_DP),
    )
    screen = device.draw_screen(system_bars=True)
    device.draw_body()
    for yy in range(device.h):
        src = yy * device.w * 3
        dst = ((yy + device.BEZEL) * device.outer_w + device.BEZEL) * 3
        device.cv.buf[dst:dst + device.w * 3] = screen.buf[src:src + device.w * 3]
    device.draw_hardware()
    return device.cv


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orientation", choices=("landscape", "portrait", "both"), default="both")
    args = parser.parse_args(argv)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if args.orientation in ("landscape", "both"):
        png = build(2560, 1600).to_png(os.path.join(root, "docs", "preview-harmonyos.png"))
        print(f"docs/preview-harmonyos.png ({png // 1024} KB)")
    if args.orientation in ("portrait", "both"):
        png = build(1600, 2560).to_png(
            os.path.join(root, "docs", "preview-harmonyos-portrait.png"))
        print(f"docs/preview-harmonyos-portrait.png ({png // 1024} KB)")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main(sys.argv[1:])
