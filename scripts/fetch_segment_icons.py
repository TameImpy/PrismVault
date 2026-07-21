"""Download the bundled segment-icon PNG set (PRD #96 / slice #100).

One-off helper: fetches the Noto Emoji (Apache-2.0) PNG for every icon named in
src.segment_icons.ICON_CODEPOINTS into data/segment_icons/, and writes a LICENSE
note. Run once (and again only if the icon set changes); the PNGs are committed
so the deck build never touches the network.

    python3 scripts/fetch_segment_icons.py
"""
import os
import sys
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.segment_icons import ICON_CODEPOINTS, ICON_DIR  # noqa: E402

# Noto Emoji 128px PNGs. Codepoint low-cased, no leading zeros stripped.
_URL = "https://raw.githubusercontent.com/googlefonts/noto-emoji/main/png/128/emoji_u%s.png"

_LICENSE = """Segment icons — Noto Emoji
==========================

The PNG files in this directory are from the Google Noto Emoji project and are
licensed under the Apache License, Version 2.0.

  Source:  https://github.com/googlefonts/noto-emoji
  Licence: Apache-2.0 (https://www.apache.org/licenses/LICENSE-2.0)

They are bundled here (rather than fetched at runtime) so the deck build is fully
offline and deterministic. Regenerate with: python3 scripts/fetch_segment_icons.py
"""


def main():
    os.makedirs(ICON_DIR, exist_ok=True)
    with open(os.path.join(ICON_DIR, "LICENSE"), "w") as f:
        f.write(_LICENSE)

    ok, failed = 0, []
    for name, codepoint in sorted(ICON_CODEPOINTS.items()):
        dest = os.path.join(ICON_DIR, "%s.png" % name)
        url = _URL % codepoint
        try:
            with urllib.request.urlopen(url, timeout=20) as resp:
                data = resp.read()
            with open(dest, "wb") as f:
                f.write(data)
            ok += 1
        except Exception as e:  # noqa: BLE001 - report and continue
            failed.append((name, codepoint, str(e)))

    print("Downloaded %d/%d icons to %s" % (ok, len(ICON_CODEPOINTS), ICON_DIR))
    if failed:
        print("FAILED (adjust codepoint in ICON_CODEPOINTS):")
        for name, cp, err in failed:
            print("  %s (u%s): %s" % (name, cp, err))
        sys.exit(1)


if __name__ == "__main__":
    main()
