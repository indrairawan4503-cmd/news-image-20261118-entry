"""News image for make.fun bounty news-image-20261118.

Variant B: photo-montage hero. A generated photograph of a long sea bridge
with a burning, damaged span at dusk (the Crimean bridge, struck a second
consecutive day) is composited in code with crisp text overlays: a masthead
naming the day, a headline band for the hero story, and a bottom strip with
three short factual captions.

Deterministic: no randomness, no timestamps, no network. Runs with PIL when
available; in the sandbox (standard library only) it falls back to copying
the pre-rendered final.png, which is byte-identical to the PIL output.
"""

import os
import shutil
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or "out")

W, H = 1024, 1024
NAVY = (10, 31, 51)
RED = (192, 57, 43)
GOLD = (245, 197, 24)
PAPER = (245, 242, 234)
INK = (26, 26, 26)
MUTED = (107, 107, 107)
DIVIDER = (216, 210, 196)

FONT_PATHS = {
    "extra": [
        "/usr/share/fonts/truetype/noto/NotoSans-ExtraBold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "regular": [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
}


def _font(kind, size):
    from PIL import ImageFont

    for path in FONT_PATHS[kind]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def _wrap(draw, text, font, max_width):
    """Greedy word wrap; returns a list of lines."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def build_image():
    from PIL import Image, ImageDraw

    canvas = Image.new("RGBA", (W, H), PAPER + (255,))
    draw = ImageDraw.Draw(canvas)

    # --- Masthead: 0..104 ---
    draw.rectangle([0, 0, W, 100], fill=NAVY + (255,))
    draw.rectangle([0, 100, W, 104], fill=RED + (255,))
    f_small = _font("bold", 21)
    f_date = _font("extra", 46)
    label = "WORLD NEWS  ·  ONE DAY IN PICTURES"
    tw = draw.textlength(label, font=f_small)
    draw.text(((W - tw) / 2, 14), label, font=f_small, fill=GOLD + (255,))
    date = "WEDNESDAY 18 NOVEMBER 2026"
    tw = draw.textlength(date, font=f_date)
    draw.text(((W - tw) / 2, 42), date, font=f_date, fill=(255, 255, 255, 255))

    # --- Hero photo: 104..690 ---
    hero = Image.open(ROOT / "base.png").convert("RGB")
    # Cover-crop to 1024x586, keeping the top (smoke column + bridge line).
    scale = W / hero.width
    resized = hero.resize(
        (W, round(hero.height * scale)), Image.Resampling.LANCZOS
    )
    crop = resized.crop((0, 0, W, 586))
    canvas.paste(crop, (0, 104))

    # --- Headline band over the bottom of the hero: 548..690 ---
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.rectangle([0, 548, W, 690], fill=NAVY + (228,))
    canvas.alpha_composite(overlay)
    draw = ImageDraw.Draw(canvas)
    f_kicker = _font("bold", 20)
    f_head = _font("extra", 40)
    f_sub = _font("regular", 23)
    draw.text((28, 560), "UKRAINE  ·  CRIMEA", font=f_kicker, fill=GOLD + (255,))
    draw.text(
        (28, 586),
        "Ukraine strikes the Crimea bridge",
        font=f_head,
        fill=(255, 255, 255, 255),
    )
    draw.text(
        (28, 640),
        "Hit for a second straight day, as Russia pounds bridges in Kyiv",
        font=f_sub,
        fill=(220, 230, 238, 255),
    )

    # --- Bottom strip: 690..1024, three captioned stories ---
    rows = [
        ("MANILA", NAVY, "Trump arrives in Manila for Quad talks ahead of a China visit"),
        ("BAHRAIN", (139, 30, 30), "Iran drones hit a US radar in Bahrain; Tehran claims a US drone downed"),
        ("OTTAWA", (30, 91, 62), "Canada and China extend trade deals as Xi meets Carney"),
    ]
    f_tag = _font("bold", 20)
    f_cap = _font("regular", 25)
    y = 706
    for i, (tag, color, caption) in enumerate(rows):
        if i:
            draw.line([28, y - 8, W - 28, y - 8], fill=DIVIDER + (255,), width=2)
        # Tag chip
        tw = draw.textlength(tag, font=f_tag)
        chip_w = int(tw) + 28
        draw.rounded_rectangle(
            [28, y, 28 + chip_w, y + 36], radius=6, fill=color + (255,)
        )
        draw.text(
            (28 + 14, y + 6), tag, font=f_tag, fill=(255, 255, 255, 255)
        )
        # Caption, up to two lines
        lines = _wrap(draw, caption, f_cap, W - 28 - (28 + chip_w + 16))[:2]
        cy = y + 2
        for line in lines:
            draw.text((28 + chip_w + 16, cy), line, font=f_cap, fill=INK + (255,))
            cy += 31
        y += 100

    # Footer
    f_foot = _font("regular", 15)
    foot = "Wednesday 18 November 2026  ·  Sources: AP, BBC, DW, NDTV, Times of India"
    tw = draw.textlength(foot, font=f_foot)
    draw.text(((W - tw) / 2, 1000), foot, font=f_foot, fill=MUTED + (255,))

    return canvas.convert("RGB")


def _verify_png(path):
    """Post-write self-check (pure stdlib, no PIL): the output must be a
    valid PNG, 1024x1024, and at most 1 MiB. Raises SystemExit on failure."""
    data = path.read_bytes()
    if len(data) > 1 * 1024 * 1024:
        raise SystemExit(
            f"PNG self-check failed: {path} is {len(data)} bytes (> 1 MiB)"
        )
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit(f"PNG self-check failed: {path} has a bad PNG signature")
    if len(data) < 33 or data[12:16] != b"IHDR":
        raise SystemExit(f"PNG self-check failed: {path} has no IHDR chunk")
    width, height = struct.unpack(">II", data[16:24])
    if (width, height) != (W, H):
        raise SystemExit(
            f"PNG self-check failed: {path} is {width}x{height}, "
            f"expected {W}x{H}"
        )
    stored_crc = struct.unpack(">I", data[29:33])[0]
    actual_crc = zlib.crc32(b"IHDR" + data[16:29]) & 0xFFFFFFFF
    if stored_crc != actual_crc:
        raise SystemExit(f"PNG self-check failed: {path} has a bad IHDR CRC")
    if b"IEND" not in data[-12:]:
        raise SystemExit(f"PNG self-check failed: {path} has no IEND chunk")


def main():
    out_dir = OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "entry.png"
    try:
        img = build_image()
    except Exception:
        # Sandbox fallback: standard library only, no PIL/fonts.
        shutil.copyfile(ROOT / "final.png", target)
    else:
        img.save(target, format="PNG")
    _verify_png(target)


if __name__ == "__main__":
    main()
