#!/usr/bin/env python3
"""Render an 8-second landscape video: sunlight 'charging' the body with health benefits.

Single visual metaphor: a rising sun's rays fill a human silhouette like a
battery, glowing gold as it charges. Health-benefit icons light up at
charge milestones (bones, mood, immunity, energy).
"""
import math
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
FPS = 24
DURATION = 8.0
N_FRAMES = int(FPS * DURATION)

OUT_DIR = "/tmp/claude-0/-home-user-Claude-VIDEOS/3b265bcc-4aa0-5fe6-8283-9333b736ebb4/scratchpad/frames"
FINAL_VIDEO = "/home/user/Claude-VIDEOS/output/sunlight_benefits.mp4"

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(FINAL_VIDEO), exist_ok=True)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def ease(t):
    """smoothstep easing"""
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


SKY_TOP_DAWN = (25, 30, 70)
SKY_BOT_DAWN = (70, 55, 95)
SKY_TOP_DAY = (70, 150, 235)
SKY_BOT_DAY = (255, 210, 130)

SUN_START = (W * 0.82, H * 0.92)
SUN_END = (W * 0.82, H * 0.22)
SUN_RADIUS = 62

BODY_CX = W * 0.34
BODY_TOP = H * 0.20
BODY_BOTTOM = H * 0.86
HEAD_R = 46

GREY = (90, 96, 108)
GOLD_TOP = (255, 236, 150)
GOLD_BOTTOM = (255, 170, 60)

# Milestone icons: (fill_fraction_trigger, label, icon_kind)
MILESTONES = [
    (0.30, "Stronger Bones", "bone"),
    (0.52, "Better Mood", "star"),
    (0.74, "Immune Boost", "shield"),
    (0.95, "More Energy", "bolt"),
]


def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def draw_sky(draw, t):
    day_t = ease(min(t / 5.5, 1.0))
    top = lerp_color(SKY_TOP_DAWN, SKY_TOP_DAY, day_t)
    bot = lerp_color(SKY_BOT_DAWN, SKY_BOT_DAY, day_t)
    for y in range(H):
        f = y / H
        draw.line([(0, y), (W, y)], fill=lerp_color(top, bot, f))


def draw_ground(draw, t):
    day_t = ease(min(t / 5.5, 1.0))
    ground_col = lerp_color((30, 40, 35), (60, 120, 70), day_t)
    gy = int(H * 0.90)
    draw.rectangle([0, gy, W, H], fill=ground_col)


def sun_position(t):
    rise_t = ease(min(t / 5.0, 1.0))
    x = lerp(SUN_START[0], SUN_END[0], rise_t)
    y = lerp(SUN_START[1], SUN_END[1], rise_t)
    return x, y


def draw_sun_and_rays(img, draw, t, cx, cy):
    glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow_layer)
    for r, alpha in [(220, 26), (160, 40), (110, 60)]:
        gdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 220, 120, alpha))
    img.alpha_composite(glow_layer)
    draw = ImageDraw.Draw(img)

    n_rays = 16
    spin = t * 18
    for i in range(n_rays):
        ang = math.radians(i * (360 / n_rays) + spin)
        pulse = 0.85 + 0.15 * math.sin(t * 4 + i)
        r1 = SUN_RADIUS + 14
        r2 = (SUN_RADIUS + 46) * pulse
        x1 = cx + r1 * math.cos(ang)
        y1 = cy + r1 * math.sin(ang)
        x2 = cx + r2 * math.cos(ang)
        y2 = cy + r2 * math.sin(ang)
        draw.line([(x1, y1), (x2, y2)], fill=(255, 224, 130, 220), width=4)

    draw.ellipse(
        [cx - SUN_RADIUS, cy - SUN_RADIUS, cx + SUN_RADIUS, cy + SUN_RADIUS],
        fill=(255, 214, 90),
        outline=(255, 245, 210),
        width=3,
    )


def silhouette_mask():
    mask = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(mask)
    head_cx, head_cy = BODY_CX, BODY_TOP + HEAD_R
    d.ellipse(
        [head_cx - HEAD_R, head_cy - HEAD_R, head_cx + HEAD_R, head_cy + HEAD_R],
        fill=255,
    )
    body_top = head_cy + HEAD_R - 8
    body_w_top = 70
    body_w_bot = 100
    d.polygon(
        [
            (BODY_CX - body_w_top, body_top),
            (BODY_CX + body_w_top, body_top),
            (BODY_CX + body_w_bot, BODY_BOTTOM),
            (BODY_CX - body_w_bot, BODY_BOTTOM),
        ],
        fill=255,
    )
    # simple arms
    d.polygon(
        [
            (BODY_CX - body_w_top, body_top + 10),
            (BODY_CX - body_w_top - 34, body_top + 130),
            (BODY_CX - body_w_top - 12, body_top + 140),
            (BODY_CX - body_w_top + 18, body_top + 20),
        ],
        fill=255,
    )
    d.polygon(
        [
            (BODY_CX + body_w_top, body_top + 10),
            (BODY_CX + body_w_top + 34, body_top + 130),
            (BODY_CX + body_w_top + 12, body_top + 140),
            (BODY_CX + body_w_top - 18, body_top + 20),
        ],
        fill=255,
    )
    return mask


SIL_MASK = silhouette_mask()


def draw_silhouette(img, fill_frac):
    grey_layer = Image.new("RGBA", (W, H), GREY + (255,))
    img.paste(grey_layer, (0, 0), SIL_MASK)

    fill_h = int((BODY_BOTTOM - BODY_TOP) * fill_frac) + HEAD_R * 2
    fill_top_y = int(BODY_BOTTOM - fill_h)
    fill_top_y = max(int(BODY_TOP - 10), fill_top_y)

    gold_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gold_layer)
    for y in range(fill_top_y, int(BODY_BOTTOM) + 2):
        f = (y - fill_top_y) / max(1, (BODY_BOTTOM - fill_top_y))
        col = lerp_color(GOLD_TOP, GOLD_BOTTOM, f)
        gd.line([(0, y), (W, y)], fill=col + (255,))
    fill_region_mask = Image.new("L", (W, H), 0)
    frd = ImageDraw.Draw(fill_region_mask)
    frd.rectangle([0, fill_top_y, W, H], fill=255)
    combined_mask = Image.composite(SIL_MASK, Image.new("L", (W, H), 0), fill_region_mask)
    img.paste(gold_layer, (0, 0), combined_mask)

    if fill_frac > 0.03:
        rim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rim)
        rd.line([(0, fill_top_y), (W, fill_top_y)], fill=(255, 250, 220, 180), width=3)
        rim_masked = Image.new("L", (W, H), 0)
        rmd = ImageDraw.Draw(rim_masked)
        band_mask = Image.new("L", (W, H), 0)
        bmd = ImageDraw.Draw(band_mask)
        bmd.rectangle([0, fill_top_y - 4, W, fill_top_y + 4], fill=255)
        rim_masked = Image.composite(SIL_MASK, Image.new("L", (W, H), 0), band_mask)
        img.paste(rim, (0, 0), rim_masked)


def draw_icon(draw, kind, cx, cy, scale, alpha):
    col = (255, 250, 225, alpha)
    s = scale
    if kind == "bone":
        draw.line([(cx - 22 * s, cy), (cx + 22 * s, cy)], fill=col, width=int(10 * s))
        for dx in (-22, 22):
            for dy in (-9, 9):
                r = 8 * s
                x, y = cx + dx * s, cy + dy * s
                draw.ellipse([x - r, y - r, x + r, y + r], fill=col)
    elif kind == "star":
        pts = []
        for i in range(10):
            ang = math.pi / 2 + i * math.pi / 5
            r = 22 * s if i % 2 == 0 else 9 * s
            pts.append((cx + r * math.cos(ang), cy - r * math.sin(ang)))
        draw.polygon(pts, fill=col)
    elif kind == "shield":
        r = 22 * s
        draw.polygon(
            [
                (cx, cy - r),
                (cx + r, cy - r * 0.5),
                (cx + r, cy + r * 0.2),
                (cx, cy + r * 1.1),
                (cx - r, cy + r * 0.2),
                (cx - r, cy - r * 0.5),
            ],
            fill=col,
        )
    elif kind == "bolt":
        r = 24 * s
        draw.polygon(
            [
                (cx - 4 * s, cy - r),
                (cx + 10 * s, cy - 2 * s),
                (cx, cy - 2 * s),
                (cx + 6 * s, cy + r),
                (cx - 10 * s, cy + 4 * s),
                (cx, cy + 4 * s),
            ],
            fill=col,
        )


def text_with_alpha(base_img, text, fnt, xy, fill, alpha, anchor="mm"):
    txt_layer = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    td = ImageDraw.Draw(txt_layer)
    r, g, b = fill
    td.text(xy, text, font=fnt, fill=(r, g, b, alpha), anchor=anchor)
    base_img.alpha_composite(txt_layer)


def render_frame(i):
    t = i / FPS
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    draw_sky(draw, t)
    draw_ground(draw, t)

    sx, sy = sun_position(t)
    draw_sun_and_rays(img, draw, t, sx, sy)
    draw = ImageDraw.Draw(img)

    fill_frac = ease(min(max((t - 0.4) / 6.0, 0.0), 1.0))
    draw_silhouette(img, fill_frac)
    draw = ImageDraw.Draw(img)

    for frac, label, kind in MILESTONES:
        if fill_frac >= frac - 0.02:
            since = t - (0.4 + frac * 6.0)
            pop = ease(min(max(since / 0.35, 0), 1)) if since > 0 else 0
            if pop <= 0:
                continue
            idx = MILESTONES.index((frac, label, kind))
            icon_x = W * 0.60
            icon_y = H * 0.20 + idx * (H * 0.16)
            scale = 0.6 + 0.4 * pop
            alpha = int(255 * min(1.0, pop * 1.3))
            draw_icon(draw, kind, icon_x, icon_y, scale, alpha)
            text_with_alpha(
                img, label, font(26), (icon_x + 42, icon_y), (255, 255, 255), alpha, anchor="lm"
            )
            draw = ImageDraw.Draw(img)

    if t < 1.8:
        a = ease(min(t / 0.5, 1.0)) * (1 - ease(max((t - 1.3) / 0.5, 0)))
        alpha = int(255 * max(0, a))
        text_with_alpha(
            img, "Sunlight = Vitamin D", font(52), (W / 2, H * 0.10), (255, 255, 255), alpha
        )

    if t > 6.6:
        a = ease(min((t - 6.6) / 0.5, 1.0))
        alpha = int(255 * a)
        text_with_alpha(
            img,
            "Get 10–15 Min of Sun Daily",
            font(46),
            (W / 2, H * 0.94),
            (255, 255, 255),
            alpha,
        )

    img.convert("RGB").save(os.path.join(OUT_DIR, f"frame_{i:04d}.png"))


def main():
    for i in range(N_FRAMES):
        render_frame(i)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            os.path.join(OUT_DIR, "frame_%04d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            FINAL_VIDEO,
        ],
        check=True,
    )
    print("Saved:", FINAL_VIDEO)


if __name__ == "__main__":
    main()
