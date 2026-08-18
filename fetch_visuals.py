#!/usr/bin/env python3
"""
Download a picture for every word in the phonics cycle.

Two sources, tried in order:

  1. Noto Animated Emoji (CC BY 4.0) -- a 512px animated GIF. Frames are
     unpacked into a horizontal sprite sheet so pygame can play them; pygame
     cannot decode animated GIFs on its own.
  2. Noto Color Emoji (Apache 2.0) -- a static 512px PNG, for the ~half of
     the list with no animated version.

Output:
  assets/images/<word>.png          sprite sheet (animated) or single frame
  assets/images/manifest.json       frame geometry + timing per word
  assets/credits.json               attribution, merged with the audio credits

Usage:
    python fetch_visuals.py              # fetch what is missing
    python fetch_visuals.py --force      # re-fetch everything
    python fetch_visuals.py --size 192   # frame size in pixels
"""

import argparse
import io
import json
import os
import urllib.request

from PIL import Image

from visual_data import NO_GOOD_EMOJI, all_visual_targets

ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(ROOT, "assets", "images")
MANIFEST = os.path.join(IMAGE_DIR, "manifest.json")
CREDITS = os.path.join(ROOT, "assets", "credits.json")

ANIMATED_URL = "https://fonts.gstatic.com/s/e/notoemoji/latest/{cp}/512.gif"
STATIC_URL = ("https://raw.githubusercontent.com/googlefonts/noto-emoji/"
              "main/png/512/emoji_u{cp}.png")

UA = "toddler-mode/0.1 (https://github.com/jaded0/toddler_mode)"

ANIMATED_CREDIT = {
    "source": "Noto Animated Emoji",
    "author": "Google Fonts",
    "license": "CC BY 4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "url": "https://googlefonts.github.io/noto-emoji-animation/",
}
STATIC_CREDIT = {
    "source": "Noto Color Emoji",
    "author": "Google Fonts",
    "license": "Apache-2.0",
    "license_url": "https://www.apache.org/licenses/LICENSE-2.0",
    "url": "https://github.com/googlefonts/noto-emoji",
}

MAX_FRAMES = 30  # keeps sprite sheets to a sane width


def _save_png(image, path):
    """Write a palette-quantised PNG.

    Emoji use few distinct colours, so a 255-colour palette is visually
    indistinguishable from RGBA (mean error ~0.5/255) at about a sixth of the
    size -- worth it for assets that get committed to the repo.
    """
    quantised = image.quantize(colors=255, method=Image.FASTOCTREE)
    quantised.save(path, optimize=True)


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        if resp.status != 200:
            raise OSError(f"HTTP {resp.status}")
        return resp.read()


def _static_codepoint(cp):
    """Noto's static PNGs drop the FE0F variation selector that GIFs keep."""
    parts = [p for p in cp.split("-") if p != "fe0f"]
    return "_".join(parts)


def fetch_animated(cp, size):
    """Return (sprite_sheet_image, frame_count, mean_frame_ms) or None."""
    try:
        raw = _get(ANIMATED_URL.format(cp=cp))
    except Exception:
        return None
    try:
        gif = Image.open(io.BytesIO(raw))
    except Exception:
        return None

    frames, durations = [], []
    try:
        while True:
            frames.append(gif.convert("RGBA").resize((size, size), Image.LANCZOS))
            durations.append(gif.info.get("duration", 40))
            if len(frames) >= MAX_FRAMES:
                break
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass

    if len(frames) < 2:
        return None

    sheet = Image.new("RGBA", (size * len(frames), size), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        sheet.paste(frame, (i * size, 0))
    mean_ms = max(20, int(sum(durations) / len(durations)))
    return sheet, len(frames), mean_ms


def fetch_static(cp, size):
    """Return a single-frame RGBA image, or None."""
    try:
        raw = _get(STATIC_URL.format(cp=_static_codepoint(cp)))
    except Exception:
        return None
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception:
        return None
    return img.resize((size, size), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=192, help="frame size in pixels")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    os.makedirs(IMAGE_DIR, exist_ok=True)
    targets = all_visual_targets()

    credits = {}
    if os.path.exists(CREDITS):
        try:
            with open(CREDITS) as fh:
                credits = json.load(fh)
        except Exception:
            credits = {}
    credits.setdefault("audio", {})
    credits.setdefault("images", {})

    manifest = {"frame_size": args.size, "words": {}}
    if os.path.exists(MANIFEST) and not args.force:
        try:
            with open(MANIFEST) as fh:
                old = json.load(fh)
            if old.get("frame_size") == args.size:
                manifest["words"] = old.get("words", {})
        except Exception:
            pass

    stats = {"animated": 0, "static": 0, "missing": 0, "cached": 0}

    for word, cp in sorted(targets.items()):
        rel = f"{word}.png"
        path = os.path.join(IMAGE_DIR, rel)
        if not args.force and word in manifest["words"] and os.path.exists(path):
            stats["cached"] += 1
            continue

        result = fetch_animated(cp, args.size)
        if result is not None:
            sheet, count, ms = result
            _save_png(sheet, path)
            manifest["words"][word] = {
                "file": rel, "frames": count, "frame_ms": ms,
                "size": args.size, "animated": True,
                "approximate": word in NO_GOOD_EMOJI,
            }
            credits["images"][rel] = dict(ANIMATED_CREDIT, codepoint=cp)
            stats["animated"] += 1
            print(f"  {word:12} animated  {count:2} frames @ {ms}ms")
            continue

        img = fetch_static(cp, args.size)
        if img is not None:
            _save_png(img, path)
            manifest["words"][word] = {
                "file": rel, "frames": 1, "frame_ms": 0,
                "size": args.size, "animated": False,
                "approximate": word in NO_GOOD_EMOJI,
            }
            credits["images"][rel] = dict(STATIC_CREDIT, codepoint=cp)
            stats["static"] += 1
            print(f"  {word:12} static")
            continue

        stats["missing"] += 1
        print(f"  {word:12} NO IMAGE (codepoint {cp})")

    with open(MANIFEST, "w") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False, sort_keys=True)
    with open(CREDITS, "w") as fh:
        json.dump(credits, fh, indent=2, ensure_ascii=False, sort_keys=True)

    print(f"\n{stats['animated']} animated, {stats['static']} static, "
          f"{stats['cached']} cached, {stats['missing']} missing")
    approx = sorted(w for w, m in manifest["words"].items() if m.get("approximate"))
    if approx:
        print(f"approximate matches (emoji is a stretch): {', '.join(approx)}")
    print(f"manifest -> {MANIFEST}")


if __name__ == "__main__":
    main()
