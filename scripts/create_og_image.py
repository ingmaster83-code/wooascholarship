"""
create_og_image.py — OG 이미지 생성 (1200x630)
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent.parent / "assets"

BG      = (30, 58, 138)
BG2     = (37, 99, 235)
ACCENT  = (245, 158, 11)
ACCENT2 = (219, 234, 254)
WHITE   = (255, 255, 255)
LIGHT   = (219, 234, 254)

W, H = 1200, 630


def load_font(size):
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "C:/Windows/Fonts/malgunbd.ttf",
        "C:/Windows/Fonts/malgun.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def draw_rounded_rect(draw, xy, radius, fill):
    x0, y0, x1, y1 = xy
    draw.rectangle([x0 + radius, y0, x1 - radius, y1], fill=fill)
    draw.rectangle([x0, y0 + radius, x1, y1 - radius], fill=fill)
    draw.ellipse([x0, y0, x0 + radius * 2, y0 + radius * 2], fill=fill)
    draw.ellipse([x1 - radius * 2, y0, x1, y0 + radius * 2], fill=fill)
    draw.ellipse([x0, y1 - radius * 2, x0 + radius * 2, y1], fill=fill)
    draw.ellipse([x1 - radius * 2, y1 - radius * 2, x1, y1], fill=fill)


def create_og_image():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw.ellipse([760, -180, 1420, 480], fill=BG2)
    draw.ellipse([880, 360, 1320, 800], fill=(30, 64, 175))

    badge_font = load_font(22)
    badge_text = "전국 3,000여 건 장학금 · 지역별 검색"
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = bbox[2] - bbox[0] + 32
    draw_rounded_rect(draw, (100, 110, 100 + bw, 150), 10, WHITE)
    draw.text((116, 118), badge_text, fill=(30, 64, 175), font=badge_font)

    title_font = load_font(72)
    draw.text((98, 195), "우아장학금", fill=WHITE, font=title_font)

    sub_font = load_font(32)
    draw.text((100, 305), "우리 동네 장학금이 있을까?", fill=LIGHT, font=sub_font)

    icon_font = load_font(24)
    boxes = ["대학생 장학금", "고등학생 장학금", "신청기간 확인", "지역별 검색"]
    cx, y = 100, 400
    for label in boxes:
        lbbox = draw.textbbox((0, 0), label, font=icon_font)
        lw = lbbox[2] - lbbox[0]
        bw = lw + 34
        draw_rounded_rect(draw, (cx, y, cx + bw, y + 46), 23, (30, 64, 175))
        draw.text((cx + 17, y + 10), label, fill=LIGHT, font=icon_font)
        cx += bw + 12
        if cx > 950:
            cx = 100
            y += 58

    domain_font = load_font(28)
    draw.text((100, 550), "wooascholarship.wooahouse.com", fill=ACCENT2, font=domain_font)

    ASSETS_DIR.mkdir(exist_ok=True)
    out = ASSETS_DIR / "og-image.png"
    img.save(str(out), "PNG", optimize=True)
    print(f"OG image created: {out} ({W}x{H})")


if __name__ == "__main__":
    create_og_image()
