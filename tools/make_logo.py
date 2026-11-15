"""Draws the Antares Chess logo files into builds/logo/:

  antares-chess-banner.png          wide banner for the README
  antares-chess-icon.png / .ico      square icon (the .ico goes into the .exe files)
  antares-chess-social-preview.png   1280 x 640, for the GitHub page
  and builds/Antares-Chess-<variant>.bmp, the 100 x 50 logo Arena shows

The glowing orange star Antares, with thin rays of light, on navy.
Needs Pillow and the Windows fonts Segoe UI and Segoe UI Black.

  python tools/make_logo.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "builds" / "logo"
FONTS = Path("C:/Windows/Fonts")
NAVY_TOP, NAVY_BOTTOM = (16, 24, 48), (8, 12, 26)
KNIGHT = "\u265e"


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def background(w, h, radius=0):
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        c = tuple(int(NAVY_TOP[k] * (1 - t) + NAVY_BOTTOM[k] * t) for k in range(3))
        for x in range(w):
            px[x, y] = c + (255,)
    if radius:
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
        img.putalpha(mask)
    return img


def star(img, cx, cy, r):
    """The glowing star: rings of orange, blurred."""
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    # red-orange outside, white-hot in the middle; a wide blur makes it fade
    # into the dark with no edge
    for scale, col in [(1.25, (150, 45, 10, 45)), (1.0, (194, 65, 12, 80)), (0.72, (242, 106, 46, 150)),
                       (0.46, (255, 160, 80, 220)), (0.24, (255, 222, 180, 255))]:
        rr = r * scale
        g.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=col)
    glow = glow.filter(ImageFilter.GaussianBlur(r / 3.5))
    core = r * 0.10
    g2 = ImageDraw.Draw(glow)
    g2.ellipse((cx - core, cy - core, cx + core, cy + core), fill=(255, 250, 240, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(r / 40))
    base = img.copy()
    base.alpha_composite(glow)
    if img.mode == "RGBA" and img.getchannel("A").getextrema()[0] < 255:
        base.putalpha(img.getchannel("A"))
    return base


def rays(img, cx, cy, r):
    """Thin rays of light across the star: long ones up-down and left-right,
    short ones on the diagonals."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for (dx, dy, length, width) in [(1, 0, 1.05, 0.034), (0, 1, 1.05, 0.034), (0.7071, 0.7071, 0.5, 0.022), (0.7071, -0.7071, 0.5, 0.022)]:
        L, W = r * length, max(1.0, r * width)
        # a long thin diamond, wide in the middle and pointed at both ends
        px, py = -dy, dx
        pts = [(cx - dx * L, cy - dy * L), (cx + px * W, cy + py * W), (cx + dx * L, cy + dy * L), (cx - px * W, cy - py * W)]
        d.polygon(pts, fill=(255, 248, 236, 255))
    soft = layer.filter(ImageFilter.GaussianBlur(max(1, r / 90)))
    out = img.copy()
    out.alpha_composite(soft)
    if img.getchannel("A").getextrema()[0] < 255:
        out.putalpha(img.getchannel("A"))
    return out


def knight(img, cx, cy, size, shadow=True):
    d = ImageDraw.Draw(img)
    f = font("seguisym.ttf", size)
    box = d.textbbox((0, 0), KNIGHT, font=f)
    w, h = box[2] - box[0], box[3] - box[1]
    x, y = cx - w / 2 - box[0], cy - h / 2 - box[1]
    if shadow:
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((x + size * 0.03, y + size * 0.04), KNIGHT, font=f, fill=(0, 0, 0, 170))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(size / 40)))
    d.text((x, y), KNIGHT, font=f, fill=(248, 248, 252, 255))


def text(img, xy, s, size, fill, name="seguibl.ttf", anchor="la", spacing=0):
    d = ImageDraw.Draw(img)
    f = font(name, size)
    if not spacing:
        d.text(xy, s, font=f, fill=fill, anchor=anchor)
        return d.textbbox(xy, s, font=f, anchor=anchor)
    x, y = xy
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill, anchor="ls")
        x += d.textlength(ch, font=f) + spacing
    return (xy[0], y - size, x, y)


def emblem(size):
    """The square icon: the star on a rounded navy square."""
    s = size * 4
    img = background(s, s, radius=s // 5)
    img = star(img, s * 0.5, s * 0.5, s * 0.46)
    img = rays(img, s * 0.5, s * 0.5, s * 0.44)
    return img.resize((size, size), Image.LANCZOS)


def banner(w, h, tagline):
    img = background(w, h)
    img = star(img, h * 0.55, h * 0.5, h * 0.44)
    img = rays(img, h * 0.55, h * 0.5, h * 0.42)
    x = h * 1.08
    text(img, (x, h * 0.50), "ANTARES", int(h * 0.20), (248, 248, 252), anchor="ls")
    text(img, (x, h * 0.72), "CHESS", int(h * 0.20), (255, 138, 61), anchor="ls")
    text(img, (x + 4, h * 0.86), tagline, int(h * 0.055), (170, 180, 205), name="segoeui.ttf", anchor="ls")
    return img


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    banner(1774, 640, "A chess engine written in the Antares programming language").convert("RGB").save(OUT / "antares-chess-banner.png")
    banner(1280, 640, "A chess engine written in Antares").convert("RGB").save(OUT / "antares-chess-social-preview.png")
    icon = emblem(512)
    icon.save(OUT / "antares-chess-icon.png")
    icon.save(OUT / "antares-chess.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    # Arena's logo: 100 x 50, knight and name
    small = background(400, 200)
    small = star(small, 92, 100, 88)
    small = rays(small, 92, 100, 84)
    text(small, (182, 92), "ANTARES", 38, (248, 248, 252), anchor="ls")
    text(small, (182, 146), "CHESS", 38, (255, 138, 61), anchor="ls")
    arena = small.resize((100, 50), Image.LANCZOS).convert("RGB")
    for v in ("avx2", "sse42", "generic", "native"):
        arena.save(HERE / "builds" / f"Antares-Chess-{v}.bmp")
    print("logo files written")


if __name__ == "__main__":
    main()
