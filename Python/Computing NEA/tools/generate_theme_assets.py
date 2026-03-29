from pathlib import Path
import math
import random

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent.parent


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def vertical_gradient(size, top_color, bottom_color):
    width, height = size
    image = Image.new("RGBA", size)
    pixels = image.load()
    for y in range(height):
        t = y / max(1, height - 1)
        color = tuple(int(top_color[i] + (bottom_color[i] - top_color[i]) * t) for i in range(4))
        for x in range(width):
            pixels[x, y] = color
    return image


def add_noise_bands(image, colors, alpha=28, step=24, seed=0):
    random.seed(seed)
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    for y in range(0, height, step):
        wave = []
        for x in range(-40, width + 40, 40):
            offset = random.randint(-14, 14)
            wave.append((x, y + offset))
        wave.extend([(width + 40, height), (-40, height)])
        color = random.choice(colors)
        draw.polygon(wave, fill=(color[0], color[1], color[2], alpha))
    return image


def generate_world1_background(path):
    image = vertical_gradient((1536, 768), (130, 210, 255, 255), (36, 98, 166, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow, "RGBA").ellipse((1080, 70, 1380, 370), fill=(255, 240, 170, 140))
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(24)))
    hill_colors = [(88, 148, 104), (62, 121, 84), (38, 88, 63)]
    for idx, color in enumerate(hill_colors):
        points = []
        baseline = 430 + idx * 90
        for x in range(-60, 1600, 120):
            wave = math.sin((x / 180.0) + idx) * (38 + idx * 10)
            crest = math.cos((x / 70.0) + idx * 2.1) * 15
            points.append((x, baseline + wave + crest))
        points.extend([(1600, 800), (-60, 800)])
        draw.polygon(points, fill=color + (255,))
    for cx, cy, scale in [(260, 130, 1.0), (560, 210, 0.8), (940, 155, 1.1), (1280, 220, 0.9)]:
        for dx, dy, r in [(-60, 0, 42), (-10, -16, 50), (42, -4, 44), (90, 8, 34)]:
            draw.ellipse((cx + dx - r * scale, cy + dy - r * scale, cx + dx + r * scale, cy + dy + r * scale), fill=(255, 255, 255, 150))
    for x in range(-20, 1550, 90):
        trunk_h = random.randint(90, 150)
        draw.rectangle((x + 20, 620 - trunk_h, x + 34, 620), fill=(76, 51, 30, 255))
        draw.ellipse((x - 16, 620 - trunk_h - 46, x + 70, 620 - trunk_h + 30), fill=(44, 112, 58, 210))
        draw.ellipse((x + 10, 620 - trunk_h - 66, x + 98, 620 - trunk_h + 6), fill=(70, 145, 74, 190))
    add_noise_bands(image, [(255, 255, 255), (120, 220, 255), (176, 240, 200)], alpha=18, step=36, seed=5)
    image.save(path)


def generate_world2_background(path):
    image = vertical_gradient((1536, 768), (24, 18, 42, 255), (102, 24, 16, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    smoke = Image.new("RGBA", image.size, (0, 0, 0, 0))
    smoke_draw = ImageDraw.Draw(smoke, "RGBA")
    for cx, cy, r in [(220, 170, 110), (540, 120, 130), (980, 190, 150), (1340, 130, 110)]:
        smoke_draw.ellipse((cx - r, cy - r * 0.6, cx + r, cy + r * 0.6), fill=(60, 54, 74, 100))
    image.alpha_composite(smoke.filter(ImageFilter.GaussianBlur(18)))
    for idx, color in enumerate([(44, 26, 32), (64, 32, 30), (96, 46, 24)]):
        points = []
        baseline = 360 + idx * 110
        for x in range(-80, 1620, 80):
            spike = random.randint(-55, 75)
            points.append((x, baseline + spike))
        points.extend([(1620, 800), (-80, 800)])
        draw.polygon(points, fill=color + (255,))
    river = [(0, 610), (160, 580), (310, 602), (520, 574), (720, 614), (930, 592), (1160, 620), (1360, 586), (1536, 606), (1536, 768), (0, 768)]
    draw.polygon(river, fill=(222, 76, 20, 255))
    for offset, color in [(0, (255, 145, 40, 110)), (18, (255, 210, 90, 80))]:
        ridge = [(x, y - offset) for (x, y) in river[:-2]]
        draw.line(ridge, fill=color, width=12)
    for _ in range(180):
        x = random.randint(0, 1535)
        y = random.randint(120, 700)
        r = random.randint(1, 3)
        c = random.choice([(255, 180, 90, 170), (255, 120, 60, 150), (255, 230, 120, 120)])
        draw.ellipse((x - r, y - r, x + r, y + r), fill=c)
    add_noise_bands(image, [(255, 120, 60), (140, 50, 40), (90, 36, 36)], alpha=18, step=32, seed=9)
    image.save(path)


def generate_world3_background(path):
    image = vertical_gradient((1536, 768), (178, 208, 232, 255), (90, 116, 140, 255))
    draw = ImageDraw.Draw(image, "RGBA")
    for idx, color in enumerate([(120, 136, 146), (96, 110, 122), (72, 82, 94)]):
        points = []
        baseline = 300 + idx * 85
        for x in range(-60, 1600, 90):
            peak = random.randint(-70, 90)
            points.append((x, baseline + peak))
        points.extend([(1600, 800), (-60, 800)])
        draw.polygon(points, fill=color + (255,))
    castle_color = (82, 78, 88, 255)
    draw.rectangle((1020, 220, 1180, 470), fill=castle_color)
    draw.rectangle((980, 250, 1028, 470), fill=castle_color)
    draw.rectangle((1170, 250, 1218, 470), fill=castle_color)
    for tx in (980, 1020, 1060, 1100, 1140, 1180):
        draw.rectangle((tx, 210, tx + 24, 240), fill=castle_color)
    draw.rectangle((1084, 370, 1116, 470), fill=(48, 36, 32, 255))
    for x in range(0, 1536, 140):
        draw.rectangle((x, 560, x + 30, 768), fill=(84, 74, 58, 255))
        draw.ellipse((x - 40, 500, x + 86, 620), fill=(34, 74, 40, 220))
    add_noise_bands(image, [(255, 255, 255), (180, 205, 226), (120, 145, 166)], alpha=15, step=38, seed=13)
    image.save(path)


def generate_platform(path, base_color, highlight_color, crack_color, moss=False, lava_glow=False, trim=False):
    image = Image.new("RGBA", (256, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rounded_rectangle((0, 10, 255, 63), radius=14, fill=base_color + (255,), outline=highlight_color + (255,), width=3)
    draw.rounded_rectangle((6, 14, 249, 30), radius=10, fill=tuple(min(255, c + 16) for c in highlight_color) + (210,))
    for x in range(18, 240, 26):
        y = random.randint(26, 52)
        draw.line((x, y, x + random.randint(10, 22), y + random.randint(6, 12)), fill=crack_color + (190,), width=2)
    if moss:
        for x in range(8, 248, 24):
            draw.ellipse((x, 4, x + 18, 18), fill=(84, 160, 76, 220))
    if lava_glow:
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow, "RGBA").rectangle((6, 50, 250, 62), fill=(255, 120, 45, 90))
        image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(8)))
        for x in range(24, 236, 34):
            draw.line((x, 18, x + 10, 60), fill=(255, 120, 55, 165), width=2)
    if trim:
        for x in range(8, 246, 30):
            draw.rectangle((x, 18, x + 10, 30), fill=(154, 126, 80, 255))
        draw.rectangle((0, 8, 255, 14), fill=(120, 100, 72, 255))
    image.save(path)


def generate_finish(path, pole_color, flag_a, flag_b, accent, topper='orb'):
    image = Image.new("RGBA", (96, 192), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.rectangle((18, 6, 28, 188), fill=pole_color + (255,))
    if topper == 'orb':
        draw.ellipse((10, 0, 36, 18), fill=accent + (255,))
    else:
        draw.polygon([(8, 16), (23, 0), (38, 16)], fill=accent + (255,))
    flag_rect = (28, 24, 82, 92)
    cols = 6
    rows = 5
    cell_w = (flag_rect[2] - flag_rect[0]) / cols
    cell_h = (flag_rect[3] - flag_rect[1]) / rows
    for row in range(rows):
        for col in range(cols):
            color = flag_a if (row + col) % 2 == 0 else flag_b
            draw.rectangle((flag_rect[0] + col * cell_w, flag_rect[1] + row * cell_h, flag_rect[0] + (col + 1) * cell_w, flag_rect[1] + (row + 1) * cell_h), fill=color + (255,))
    draw.rectangle((28, 24, 82, 92), outline=(245, 245, 245, 255), width=2)
    image.save(path)


def generate_humanoid(path, body, accent, eye, horn=False, skeleton=False, knight=False, weapon=False):
    image = Image.new("RGBA", (64, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    if skeleton:
        draw.ellipse((16, 8, 48, 34), fill=(230, 220, 196, 255), outline=(120, 98, 82, 255))
        draw.rectangle((28, 34, 36, 64), fill=(226, 214, 190, 255))
        for y in range(40, 60, 6):
            draw.line((22, y, 42, y), fill=(205, 194, 170, 255), width=2)
        draw.line((30, 62, 22, 88), fill=(220, 210, 188, 255), width=4)
        draw.line((34, 62, 42, 88), fill=(220, 210, 188, 255), width=4)
        draw.line((28, 44, 14, 62), fill=(220, 210, 188, 255), width=4)
        draw.line((36, 44, 50, 62), fill=(220, 210, 188, 255), width=4)
        draw.ellipse((23, 18, 29, 24), fill=(40, 22, 20, 255))
        draw.ellipse((35, 18, 41, 24), fill=(40, 22, 20, 255))
        draw.rectangle((29, 26, 35, 29), fill=(110, 62, 42, 255))
        if horn:
            draw.polygon([(20, 10), (26, 0), (28, 14)], fill=(255, 182, 92, 255))
            draw.polygon([(36, 14), (40, 0), (46, 10)], fill=(255, 182, 92, 255))
    else:
        draw.rounded_rectangle((12, 18, 52, 82), radius=14, fill=body + (255,), outline=accent + (255,), width=3)
        draw.ellipse((18, 10, 46, 34), fill=accent + (255,))
        if knight:
            draw.rectangle((18, 22, 46, 38), fill=(164, 170, 182, 255), outline=(90, 94, 108, 255))
            draw.rectangle((28, 18, 36, 38), fill=(90, 94, 108, 255))
            draw.rectangle((24, 40, 40, 80), fill=body + (255,))
            draw.rectangle((18, 80, 26, 94), fill=accent + (255,))
            draw.rectangle((38, 80, 46, 94), fill=accent + (255,))
        else:
            draw.ellipse((24, 24, 32, 32), fill=eye + (255,))
            draw.ellipse((34, 24, 42, 32), fill=eye + (255,))
            draw.rectangle((18, 82, 26, 94), fill=accent + (255,))
            draw.rectangle((38, 82, 46, 94), fill=accent + (255,))
            draw.rectangle((8, 42, 14, 66), fill=accent + (255,))
            draw.rectangle((50, 42, 56, 66), fill=accent + (255,))
        if weapon:
            draw.rectangle((50, 34, 54, 70), fill=(112, 74, 52, 255))
            draw.polygon([(46, 34), (62, 30), (58, 40)], fill=(220, 220, 228, 255))
    image.save(path)


def generate_melee_frame(path, body, accent, eye, pose=0, skeleton=False, knight=False, running=False):
    image = Image.new("RGBA", (64, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    if running:
        bob_vals = [0, -2, 0, 2, 1, -1]
        stride_vals = [-10, -5, 3, 10, 6, -4]
        arm_vals = [9, 4, -3, -9, -6, 4]
    else:
        bob_vals = [0, -1, 0, 1]
        stride_vals = [-3, -1, 1, 3]
        arm_vals = [3, 1, -1, -3]
    bob = bob_vals[pose % len(bob_vals)]
    stride = stride_vals[pose % len(stride_vals)]
    arm_swing = arm_vals[pose % len(arm_vals)]

    if skeleton:
        draw.ellipse((16, 8 + bob, 48, 34 + bob), fill=(230, 220, 196, 255), outline=(120, 98, 82, 255))
        draw.rectangle((28, 34 + bob, 36, 64 + bob), fill=(226, 214, 190, 255))
        for y in range(40 + bob, 60 + bob, 6):
            draw.line((22, y, 42, y), fill=(205, 194, 170, 255), width=2)
        draw.line((30, 62 + bob, 22, 88 - stride), fill=(220, 210, 188, 255), width=4)
        draw.line((34, 62 + bob, 42, 88 + stride), fill=(220, 210, 188, 255), width=4)
        draw.line((28, 44 + bob, 14, 62 + arm_swing), fill=(220, 210, 188, 255), width=4)
        draw.line((36, 44 + bob, 50, 62 - arm_swing), fill=(220, 210, 188, 255), width=4)
        draw.ellipse((23, 18 + bob, 29, 24 + bob), fill=(40, 22, 20, 255))
        draw.ellipse((35, 18 + bob, 41, 24 + bob), fill=(40, 22, 20, 255))
        draw.rectangle((29, 26 + bob, 35, 29 + bob), fill=(110, 62, 42, 255))
        draw.polygon([(20, 10 + bob), (26, 0 + bob), (28, 14 + bob)], fill=(255, 182, 92, 255))
        draw.polygon([(36, 14 + bob), (40, 0 + bob), (46, 10 + bob)], fill=(255, 182, 92, 255))
    elif knight:
        draw.rounded_rectangle((12, 18 + bob, 52, 82 + bob), radius=14, fill=body + (255,), outline=accent + (255,), width=3)
        draw.rectangle((18, 22 + bob, 46, 38 + bob), fill=(164, 170, 182, 255), outline=(90, 94, 108, 255))
        draw.rectangle((28, 18 + bob, 36, 38 + bob), fill=(90, 94, 108, 255))
        draw.line((24, 80 + bob, 22, 94 - stride), fill=accent + (255,), width=5)
        draw.line((40, 80 + bob, 42, 94 + stride), fill=accent + (255,), width=5)
        draw.line((22, 48 + bob, 12, 62 + arm_swing), fill=accent + (255,), width=5)
        draw.line((42, 48 + bob, 52, 62 - arm_swing), fill=accent + (255,), width=5)
    else:
        draw.rounded_rectangle((12, 18 + bob, 52, 82 + bob), radius=14, fill=body + (255,), outline=accent + (255,), width=3)
        draw.ellipse((18, 10 + bob, 46, 34 + bob), fill=accent + (255,))
        draw.line((24, 80 + bob, 22, 94 - stride), fill=accent + (255,), width=5)
        draw.line((40, 80 + bob, 42, 94 + stride), fill=accent + (255,), width=5)
        draw.line((20, 44 + bob, 10, 60 + arm_swing), fill=accent + (255,), width=5)
        draw.line((44, 44 + bob, 54, 60 - arm_swing), fill=accent + (255,), width=5)
        draw.ellipse((24, 24 + bob, 32, 32 + bob), fill=eye + (255,))
        draw.ellipse((34, 24 + bob, 42, 32 + bob), fill=eye + (255,))
    image.save(path)


def generate_ranged_frame(path, body, accent, eye, pose=0, skeleton=False, knight=False, running=False):
    image = Image.new("RGBA", (64, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    if running:
        bob_vals = [0, -3, 0, 3, 1, -2, 2, -1]
        stride_vals = [-10, -4, 4, 10, 8, 2, -6, -9]
        arm_vals = [-9, -4, 3, 9, 8, 2, -5, -8]
    else:
        bob_vals = [0, -1, 0, 1]
        stride_vals = [-4, -1, 2, 5]
        arm_vals = [-5, 0, 5, 2]
    bob = bob_vals[pose % len(bob_vals)]
    stride = stride_vals[pose % len(stride_vals)]
    arm_swing = arm_vals[pose % len(arm_vals)]
    if skeleton:
        draw.ellipse((16, 8 + bob, 48, 34 + bob), fill=(232, 222, 198, 255), outline=(126, 100, 82, 255))
        draw.rectangle((28, 34 + bob, 36, 62 + bob), fill=(226, 214, 190, 255))
        for y in range(40 + bob, 58 + bob, 6):
            draw.line((22, y, 42, y), fill=(205, 194, 170, 255), width=2)
        draw.line((32, 42 + bob, 18, 58 + arm_swing), fill=(220, 210, 188, 255), width=4)
        draw.line((34, 42 + bob, 50, 52 - arm_swing), fill=(220, 210, 188, 255), width=4)
        draw.line((30, 62 + bob, 22, 88 - stride), fill=(220, 210, 188, 255), width=4)
        draw.line((34, 62 + bob, 42, 88 + stride), fill=(220, 210, 188, 255), width=4)
        draw.ellipse((23, 18 + bob, 29, 24 + bob), fill=(40, 22, 20, 255))
        draw.ellipse((35, 18 + bob, 41, 24 + bob), fill=(40, 22, 20, 255))
        bow_color = (132, 82, 50, 255)
        draw.arc((44, 22, 62, 64), start=250, end=110, fill=bow_color, width=2)
        draw.line((47, 26, 56, 60), fill=(235, 222, 194, 255), width=1)
    elif knight:
        draw.rounded_rectangle((12, 18 + bob, 52, 82 + bob), radius=14, fill=body + (255,), outline=accent + (255,), width=3)
        draw.rectangle((18, 22 + bob, 46, 38 + bob), fill=(172, 178, 192, 255), outline=(96, 102, 116, 255))
        draw.rectangle((28, 18 + bob, 36, 38 + bob), fill=(98, 104, 118, 255))
        draw.rectangle((24, 40 + bob, 40, 80 + bob), fill=body + (255,))
        draw.line((28, 44 + bob, 16, 60 + arm_swing), fill=accent + (255,), width=5)
        draw.line((38, 46 + bob, 52, 56 - arm_swing), fill=accent + (255,), width=5)
        draw.line((28, 80 + bob, 24, 94 - stride), fill=accent + (255,), width=5)
        draw.line((38, 80 + bob, 42, 94 + stride), fill=accent + (255,), width=5)
        bow_color = (130, 92, 58, 255)
        draw.arc((44, 22, 62, 64), start=250, end=110, fill=bow_color, width=2)
        draw.line((47, 26, 56, 60), fill=(228, 220, 204, 255), width=1)
        draw.ellipse((48, 28 + bob, 54, 34 + bob), fill=eye + (255,))
        draw.ellipse((40, 28 + bob, 46, 34 + bob), fill=eye + (255,))
    else:
        draw.rounded_rectangle((12, 18 + bob, 52, 82 + bob), radius=14, fill=body + (255,), outline=accent + (255,), width=3)
        draw.ellipse((18, 10 + bob, 46, 34 + bob), fill=accent + (255,))
        draw.line((28, 42 + bob, 14, 58 + arm_swing), fill=accent + (255,), width=5)
        draw.line((36, 42 + bob, 52, 54 - arm_swing), fill=accent + (255,), width=5)
        draw.line((24, 80 + bob, 20, 94 - stride), fill=accent + (255,), width=5)
        draw.line((40, 80 + bob, 44, 94 + stride), fill=accent + (255,), width=5)
        draw.ellipse((24, 24 + bob, 32, 32 + bob), fill=eye + (255,))
        draw.ellipse((34, 24 + bob, 42, 32 + bob), fill=eye + (255,))
        draw.rectangle((48, 34 + bob, 58, 42 + bob), fill=(90, 90, 98, 255))
        draw.rectangle((56, 36 + bob, 63, 40 + bob), fill=(152, 110, 80, 255))
    image.save(path)


def generate_firewall_frame(path, outer_color, inner_color, spark_color, pose=0, metal_color=None):
    width, height = 160, 36
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    if metal_color is not None:
        draw.rounded_rectangle((0, 11, width - 1, height - 11), radius=10, fill=metal_color + (255,), outline=(50, 42, 40, 255), width=2)
    flame_offsets = [0, 3, -2, 4, -1, 2]
    shift = pose % len(flame_offsets)
    for idx, x in enumerate(range(8, width - 8, 18)):
        peak = 4 + flame_offsets[(idx + shift) % len(flame_offsets)]
        draw.polygon([(x, height // 2 + 7), (x + 8, peak), (x + 16, height // 2 + 7)], fill=outer_color + (220,))
        draw.polygon([(x + 3, height // 2 + 5), (x + 8, peak + 4), (x + 13, height // 2 + 5)], fill=inner_color + (240,))
    for spark_x in range(20, width - 10, 28):
        draw.ellipse((spark_x, 2 + ((spark_x // 7 + pose) % 6), spark_x + 4, 6 + ((spark_x // 7 + pose) % 6)), fill=spark_color + (220,))
    image = image.filter(ImageFilter.GaussianBlur(0.35))
    image.save(path)


def generate_boss_frame(path, body, armor, eye, pose=0, skeleton=False, knight=False):
    image = Image.new("RGBA", (128, 176), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image, "RGBA")
    bob = [0, -2, 0, 2][pose % 4]
    if skeleton:
        draw.ellipse((34, 18 + bob, 90, 64 + bob), fill=(224, 214, 190, 255), outline=(108, 88, 72, 255))
        draw.rectangle((56, 64 + bob, 68, 114 + bob), fill=(220, 210, 184, 255))
        for y in range(74 + bob, 108 + bob, 8):
            draw.line((42, y, 82, y), fill=(204, 192, 166, 255), width=3)
        draw.line((60, 112 + bob, 42, 156), fill=(220, 210, 184, 255), width=7)
        draw.line((64, 112 + bob, 82, 156), fill=(220, 210, 184, 255), width=7)
        draw.line((56, 78 + bob, 30, 116 + pose), fill=(220, 210, 184, 255), width=7)
        draw.line((68, 78 + bob, 102, 118 - pose), fill=(220, 210, 184, 255), width=7)
        draw.ellipse((48, 34 + bob, 58, 46 + bob), fill=(40, 26, 22, 255))
        draw.ellipse((66, 34 + bob, 76, 46 + bob), fill=(40, 26, 22, 255))
        draw.polygon([(42, 24 + bob), (54, 4 + bob), (58, 28 + bob)], fill=(255, 170, 88, 255))
        draw.polygon([(70, 28 + bob), (74, 4 + bob), (86, 24 + bob)], fill=(255, 170, 88, 255))
    elif knight:
        draw.rounded_rectangle((30, 24 + bob, 96, 156 + bob), radius=18, fill=body + (255,), outline=armor + (255,), width=4)
        draw.rectangle((42, 20 + bob, 84, 62 + bob), fill=(176, 182, 194, 255), outline=(96, 102, 116, 255))
        draw.rectangle((58, 24 + bob, 66, 62 + bob), fill=(94, 100, 112, 255))
        draw.rectangle((44, 68 + bob, 82, 126 + bob), fill=body + (255,))
        draw.rectangle((34, 156 + bob, 48, 174), fill=armor + (255,))
        draw.rectangle((78, 156 + bob, 92, 174), fill=armor + (255,))
        draw.rectangle((18, 82 + bob, 32, 132 + bob), fill=armor + (255,))
        draw.rectangle((94, 82 + bob, 108, 132 + bob), fill=armor + (255,))
        draw.ellipse((48, 36 + bob, 56, 42 + bob), fill=eye + (255,))
        draw.ellipse((70, 36 + bob, 78, 42 + bob), fill=eye + (255,))
    else:
        draw.rounded_rectangle((28, 30 + bob, 100, 156 + bob), radius=20, fill=body + (255,), outline=armor + (255,), width=4)
        draw.ellipse((38, 10 + bob, 90, 54 + bob), fill=armor + (255,))
        draw.rectangle((20, 86 + bob, 32, 134 + bob), fill=armor + (255,))
        draw.rectangle((96, 86 + bob, 108, 134 + bob), fill=armor + (255,))
        draw.rectangle((42, 154 + bob, 56, 176), fill=armor + (255,))
        draw.rectangle((74, 154 + bob, 88, 176), fill=armor + (255,))
        draw.ellipse((48, 28 + bob, 58, 38 + bob), fill=eye + (255,))
        draw.ellipse((70, 28 + bob, 80, 38 + bob), fill=eye + (255,))
    image.save(path)


def generate_animation_set(folder, maker, frame_count):
    ensure_dir(folder)
    for idx in range(frame_count):
        maker(Path(folder) / f"{idx:02d}.png", idx)


def build_preview(paths):
    preview = Image.new("RGBA", (1600, 1180), (14, 16, 28, 255))
    draw = ImageDraw.Draw(preview, "RGBA")
    draw.rectangle((0, 0, 1600, 86), fill=(24, 34, 52, 255))
    draw.text((42, 28), "Lost Horizon Theme Asset Preview", fill=(235, 240, 255, 255))
    backgrounds = [
        ("World 1 Background", paths["background.png"], (30, 110)),
        ("World 2 Background", paths["underworld background.png"], (530, 110)),
        ("World 3 Background", paths["medieval background.png"], (1030, 110)),
    ]
    for text, img_path, pos in backgrounds:
        draw.text((pos[0], pos[1] - 28), text, fill=(225, 230, 245, 255))
        img = Image.open(img_path).convert("RGBA").resize((440, 260))
        preview.alpha_composite(img, pos)
    rows = [
        ("World 1 Set", ["platform.png", "finish line.png", "melee enemy.png", "world1_boss.png"], 420),
        ("World 2 Set", ["underworld platform.png", "underworld finish.png", "w2_melee_enemy.png", "w2_boss.png"], 700),
        ("World 3 Set", ["medieval platform.png", "medieval finish.png", "medieval enemy.png", "medieval boss.png"], 980),
    ]
    for label, names, y in rows:
        draw.text((40, y - 28), label, fill=(225, 230, 245, 255))
        x = 40
        for idx, name in enumerate(names):
            img = Image.open(paths[name]).convert("RGBA")
            if idx == 0:
                sample = img.resize((240, 86))
            elif idx == 1:
                sample = img.resize((96, 180))
            else:
                sample = img.resize((140, 180))
            preview.alpha_composite(sample, (x, y))
            x += 180 if idx > 0 else 280
    preview.save(paths["theme_preview.png"])


def main():
    random.seed(42)
    outputs = {
        "background.png": ROOT / "background.png",
        "platform.png": ROOT / "platform.png",
        "finish line.png": ROOT / "finish line.png",
        "melee enemy.png": ROOT / "melee enemy.png",
        "world1_boss.png": ROOT / "world1_boss.png",
        "underworld background.png": ROOT / "underworld background.png",
        "underworld platform.png": ROOT / "underworld platform.png",
        "underworld finish.png": ROOT / "underworld finish.png",
        "w2_melee_enemy.png": ROOT / "w2_melee_enemy.png",
        "w2_ranged_enemy.png": ROOT / "w2_ranged_enemy.png",
        "w2_boss.png": ROOT / "w2_boss.png",
        "medieval background.png": ROOT / "medieval background.png",
        "medieval platform.png": ROOT / "medieval platform.png",
        "medieval finish.png": ROOT / "medieval finish.png",
        "medieval enemy.png": ROOT / "medieval enemy.png",
        "medieval ranged enemy.png": ROOT / "medieval ranged enemy.png",
        "medieval boss.png": ROOT / "medieval boss.png",
        "theme_preview.png": ROOT / "theme_preview.png",
    }
    generate_world1_background(outputs["background.png"])
    generate_world2_background(outputs["underworld background.png"])
    generate_world3_background(outputs["medieval background.png"])
    generate_platform(outputs["platform.png"], (96, 70, 48), (152, 118, 80), (78, 56, 44), moss=True)
    generate_platform(outputs["underworld platform.png"], (88, 54, 60), (136, 94, 80), (52, 24, 30), lava_glow=True)
    generate_platform(outputs["medieval platform.png"], (102, 88, 72), (162, 148, 126), (76, 62, 54), trim=True)
    generate_finish(outputs["finish line.png"], (108, 82, 56), (250, 248, 240), (78, 136, 72), (255, 214, 110), topper='orb')
    generate_finish(outputs["underworld finish.png"], (78, 54, 50), (255, 240, 205), (188, 68, 42), (255, 156, 84), topper='orb')
    generate_finish(outputs["medieval finish.png"], (102, 82, 64), (232, 224, 212), (146, 48, 38), (228, 188, 112), topper='spear')
    generate_humanoid(outputs["melee enemy.png"], (74, 112, 78), (36, 70, 42), (255, 244, 220))
    generate_humanoid(outputs["w2_melee_enemy.png"], (120, 68, 56), (62, 20, 24), (255, 220, 140), horn=True, skeleton=True)
    generate_humanoid(outputs["w2_ranged_enemy.png"], (114, 62, 50), (64, 24, 28), (255, 220, 140), skeleton=True)
    generate_humanoid(outputs["medieval enemy.png"], (74, 86, 112), (38, 48, 76), (250, 245, 232), knight=True)
    generate_humanoid(outputs["medieval ranged enemy.png"], (88, 72, 112), (56, 42, 78), (250, 245, 232), knight=True, weapon=True)
    generate_boss_frame(outputs["world1_boss.png"], (84, 108, 78), (48, 72, 42), (255, 245, 225), pose=0)
    generate_boss_frame(outputs["w2_boss.png"], (122, 72, 56), (70, 26, 24), (255, 222, 152), pose=0, skeleton=True)
    generate_boss_frame(outputs["medieval boss.png"], (84, 84, 106), (52, 54, 78), (255, 244, 230), pose=0, knight=True)
    generate_animation_set(ROOT / "images" / "entities" / "enemy" / "world2" / "idle", lambda p, i: generate_melee_frame(p, (120, 68, 56), (62, 20, 24), (255, 220, 140), pose=i, skeleton=True, running=False), 4)
    generate_animation_set(ROOT / "images" / "entities" / "enemy" / "world2" / "run", lambda p, i: generate_melee_frame(p, (120, 68, 56), (62, 20, 24), (255, 220, 140), pose=i, skeleton=True, running=True), 8)
    generate_animation_set(ROOT / "images" / "entities" / "enemy" / "world3" / "idle", lambda p, i: generate_humanoid(p, (74, 86, 112), (38, 48, 76), (250, 245, 232), knight=True), 4)
    generate_animation_set(ROOT / "images" / "entities" / "enemy" / "world3" / "run", lambda p, i: generate_humanoid(p, (74, 86, 112), (38, 48, 76), (250, 245, 232), knight=True, weapon=(i % 2 == 0)), 6)
    generate_animation_set(ROOT / "images" / "entities" / "ranged" / "world1" / "idle", lambda p, i: generate_ranged_frame(p, (88, 126, 96), (52, 78, 58), (255, 244, 220), pose=i, running=False), 4)
    generate_animation_set(ROOT / "images" / "entities" / "ranged" / "world1" / "run", lambda p, i: generate_ranged_frame(p, (88, 126, 96), (52, 78, 58), (255, 244, 220), pose=i, running=True), 8)
    generate_animation_set(ROOT / "images" / "entities" / "ranged" / "world2" / "idle", lambda p, i: generate_ranged_frame(p, (114, 62, 50), (64, 24, 28), (255, 220, 140), pose=i, skeleton=True, running=False), 4)
    generate_animation_set(ROOT / "images" / "entities" / "ranged" / "world2" / "run", lambda p, i: generate_ranged_frame(p, (114, 62, 50), (64, 24, 28), (255, 220, 140), pose=i, skeleton=True, running=True), 8)
    generate_animation_set(ROOT / "images" / "entities" / "ranged" / "world3" / "idle", lambda p, i: generate_ranged_frame(p, (88, 72, 112), (56, 42, 78), (250, 245, 232), pose=i, knight=True, running=False), 4)
    generate_animation_set(ROOT / "images" / "entities" / "ranged" / "world3" / "run", lambda p, i: generate_ranged_frame(p, (88, 72, 112), (56, 42, 78), (250, 245, 232), pose=i, knight=True, running=True), 8)
    generate_animation_set(ROOT / "images" / "hazards" / "firewall", lambda p, i: generate_firewall_frame(p, (255, 96, 34), (255, 214, 90), (255, 238, 160), pose=i, metal_color=(88, 58, 42)), 6)
    generate_animation_set(ROOT / "images" / "hazards" / "firewall" / "world2", lambda p, i: generate_firewall_frame(p, (255, 104, 36), (255, 228, 112), (255, 236, 176), pose=i, metal_color=(68, 36, 34)), 6)
    generate_animation_set(ROOT / "images" / "hazards" / "firewall" / "world3", lambda p, i: generate_firewall_frame(p, (255, 148, 64), (255, 232, 148), (255, 242, 194), pose=i, metal_color=(92, 92, 102)), 6)
    generate_animation_set(ROOT / "images" / "entities" / "boss" / "world1", lambda p, i: generate_boss_frame(p, (84, 108, 78), (48, 72, 42), (255, 245, 225), pose=i), 4)
    generate_animation_set(ROOT / "images" / "entities" / "boss" / "world2", lambda p, i: generate_boss_frame(p, (122, 72, 56), (70, 26, 24), (255, 222, 152), pose=i, skeleton=True), 4)
    generate_animation_set(ROOT / "images" / "entities" / "boss" / "world3", lambda p, i: generate_boss_frame(p, (84, 84, 106), (52, 54, 78), (255, 244, 230), pose=i, knight=True), 4)
    build_preview(outputs)
    print("Generated theme assets:")
    for key, path in outputs.items():
        print(f"- {key}: {path}")


if __name__ == "__main__":
    main()