#!/usr/bin/env python3
"""
Generates every sky preset used by Sky Select.

Each preset becomes a built-in resource pack in
src/main/resources/resourcepacks/<id>/ using the OptiFine custom-sky format
(assets/minecraft/optifine/sky/world0/skyN.properties + skyN.png), which is
what Skyboxify reads.

Skybox texture = 3x2 grid of square tiles. Tile order / orientation follows the
classic OptiFine/vanilla skybox layout:

    [ 0 bottom ][ 1 north ][ 2 south ]
    [ 3 top    ][ 4 east  ][ 5 west  ]

Every texture is computed from a 3D direction per pixel, so faces join
seamlessly. If your game shows seams or a flipped sky, build/enable the
"layout_test" preset and compare the labels with the direction you face (F3).

Usage:  python3 tools/gen_skies.py
Needs:  numpy, Pillow
"""
import json
import math
import os
import shutil

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "src", "main", "resources", "resourcepacks")
SKY_DIR = os.path.join("assets", "minecraft", "optifine", "sky", "world0")

# Set True if meteors appear to move tail-first in game (flips rotation sense).
REVERSE_METEORS = False

# --------------------------------------------------------------------------
# cube geometry
# --------------------------------------------------------------------------

def _rx(a, x, y, z):
    c, s = math.cos(a), math.sin(a)
    return x, y * c - z * s, y * s + z * c


def _rz(a, x, y, z):
    c, s = math.cos(a), math.sin(a)
    return x * c - y * s, x * s + y * c, z


_ROTS = [
    lambda x, y, z: (x, y, z),
    lambda x, y, z: _rx(math.radians(90), x, y, z),
    lambda x, y, z: _rx(math.radians(-90), x, y, z),
    lambda x, y, z: _rx(math.radians(180), x, y, z),
    lambda x, y, z: _rz(math.radians(90), x, y, z),
    lambda x, y, z: _rz(math.radians(-90), x, y, z),
]
TILE_NAMES = ["BOTTOM", "NORTH", "SOUTH", "TOP", "EAST", "WEST"]


def tile_dirs(n):
    """Unit direction for every pixel of every tile -> list of 6 arrays (n, n, 3)."""
    s = (np.arange(n) + 0.5) / n
    S, T = np.meshgrid(s, s)  # [row=t][col=s]
    x0, y0, z0 = -1 + 2 * S, -np.ones_like(S), -1 + 2 * T
    out = []
    for rot in _ROTS:
        x, y, z = rot(x0, y0, z0)
        d = np.stack([x, y, z], axis=-1)
        d /= np.linalg.norm(d, axis=-1, keepdims=True)
        out.append(d)
    return out


def dir_to_tile(d):
    """Inverse mapping: unit vector -> (tile, s, t) with s,t in 0..1."""
    x, y, z = d
    ax, ay, az = abs(x), abs(y), abs(z)
    if ay >= ax and ay >= az:
        xp, zp = x / ay, z / ay
        return (0, (xp + 1) / 2, (zp + 1) / 2) if y < 0 else (3, (xp + 1) / 2, (-zp + 1) / 2)
    if az >= ax:
        xp, yp = x / az, y / az
        return (1, (xp + 1) / 2, (-yp + 1) / 2) if z < 0 else (2, (xp + 1) / 2, (yp + 1) / 2)
    yp, zp = y / ax, z / ax
    return (4, (yp + 1) / 2, (zp + 1) / 2) if x > 0 else (5, (-yp + 1) / 2, (zp + 1) / 2)


def _self_check(n=64):
    dirs = tile_dirs(n)
    for i, td in enumerate(dirs):
        for (r, c) in [(3, 5), (n // 2, n // 2), (n - 4, 10), (10, n - 4)]:
            t, s, tt = dir_to_tile(td[r, c])
            assert t == i, (i, t)
            assert abs(s * n - (c + 0.5)) < 1e-6 and abs(tt * n - (r + 0.5)) < 1e-6


def compose(fn, n):
    """Evaluate fn(dirs) -> (n,n,3) float RGB for every tile and tile them 3x2."""
    img = np.zeros((2 * n, 3 * n, 3), dtype=np.float32)
    for i, d in enumerate(tile_dirs(n)):
        r, c = divmod(i, 3)
        img[r * n:(r + 1) * n, c * n:(c + 1) * n] = fn(d)
    return img


def save_png(arr, path, opaque=False):
    """Layers are saved as RGBA (alpha = brightness) so they show over the bright day sky too."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    a = np.clip(arr, 0, 1)
    if opaque:
        Image.fromarray((a * 255 + 0.5).astype(np.uint8), "RGB").save(path, optimize=True)
        return
    m = a.max(axis=-1, keepdims=True)
    alpha = np.clip(m * 1.2, 0, 1) ** 0.9
    rgb = np.clip(a / np.maximum(m, 1e-4), 0, 1)
    rgba = np.concatenate([rgb, alpha], axis=-1)
    Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").save(path, optimize=True)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t[..., None]


def unit(v):
    v = np.array(v, dtype=np.float64)
    return v / np.linalg.norm(v)


def basis_for(axis):
    a = unit(axis)
    helper = np.array([0, 1, 0]) if abs(a[1]) < 0.9 else np.array([1, 0, 0])
    b1 = unit(np.cross(a, helper))
    b2 = np.cross(a, b1)  # right-handed: phi increases as the sky rotates about +axis
    return a, b1, b2


# --------------------------------------------------------------------------
# layers
# --------------------------------------------------------------------------

def value_noise3(p, lat):
    g = lat.shape[0]
    pi = np.floor(p).astype(np.int64)
    f = p - pi
    f = f * f * (3 - 2 * f)
    i0, i1 = pi % g, (pi + 1) % g
    x0, y0, z0 = i0[..., 0], i0[..., 1], i0[..., 2]
    x1, y1, z1 = i1[..., 0], i1[..., 1], i1[..., 2]
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    c00 = lat[x0, y0, z0] * (1 - fx) + lat[x1, y0, z0] * fx
    c10 = lat[x0, y1, z0] * (1 - fx) + lat[x1, y1, z0] * fx
    c01 = lat[x0, y0, z1] * (1 - fx) + lat[x1, y0, z1] * fx
    c11 = lat[x0, y1, z1] * (1 - fx) + lat[x1, y1, z1] * fx
    c0 = c00 * (1 - fy) + c10 * fy
    c1 = c01 * (1 - fy) + c11 * fy
    return c0 * (1 - fz) + c1 * fz


def fbm(d, seed, freq, octaves=5):
    rng = np.random.default_rng(seed)
    lat = rng.random((16, 16, 16)).astype(np.float32)
    total, amp, acc = 0.0, 1.0, 0.0
    off = rng.uniform(0, 16, size=3)
    for o in range(octaves):
        acc = acc + amp * value_noise3(d * freq * (2.03 ** o) + off + o * 3.7, lat)
        total += amp
        amp *= 0.52
    return acc / total


def aurora_layer(seed, base_deg, height_deg, low, mid, top, gain=1.0):
    low, mid, top = (np.array(c, dtype=np.float32) for c in (low, mid, top))

    def fn(d):
        rng = np.random.default_rng(seed)
        y = np.clip(d[..., 1], -1, 1)
        elev = np.degrees(np.arcsin(y))
        az = np.arctan2(d[..., 0], d[..., 2])
        wob = sum(rng.uniform(0.5, 1.0) / k * np.sin(k * az + rng.uniform(0, 6.28)) for k in (1, 2, 3, 4, 6))
        base = base_deg + 9.0 * wob
        h = (elev - base) / height_deg
        lower = smoothstep(0.0, 0.07, h)
        upper = np.exp(-2.1 * np.clip(h, 0, None))
        amps, acc = 0.0, 0.0
        for k in (23, 37, 59, 83):
            a = rng.uniform(0.5, 1.0)
            acc = acc + a * np.sin(k * az + rng.uniform(0, 6.28) + 2.5 * h)
            amps += a
        rays = np.clip(0.5 + 0.5 * acc / amps, 0, 1) ** 1.6
        patch = 0.5 + 0.5 * np.sin(2 * az + rng.uniform(0, 6.28)) * np.sin(5 * az + rng.uniform(0, 6.28))
        patch = 0.35 + 0.65 * np.clip(patch * 1.3, 0, 1)
        inten = lower * upper * (0.3 + 0.7 * rays) * patch
        inten = inten * smoothstep(1.0, 7.0, elev) * smoothstep(88.0, 62.0, elev)
        t = np.clip(h, 0, 1.6) / 1.6
        col = np.where((t < 0.45)[..., None], lerp(low, mid, t / 0.45), lerp(mid, top, np.clip((t - 0.45) / 0.55, 0, 1)))
        return (col * inten[..., None] * gain).astype(np.float32)

    return fn


def nebula_layer(seed, col_a, col_b, col_c, gain=0.85):
    col_a, col_b, col_c = (np.array(c, dtype=np.float32) for c in (col_a, col_b, col_c))

    def fn(d):
        n1 = fbm(d, seed, 1.5)
        n2 = fbm(d, seed + 11, 2.2)
        n3 = fbm(d, seed + 23, 3.4, 4)
        i1 = smoothstep(0.46, 0.80, n1) ** 1.3
        i2 = smoothstep(0.50, 0.82, n2) ** 1.4
        i3 = smoothstep(0.55, 0.85, n3) ** 1.6 * i1
        glow = smoothstep(0.35, 0.7, fbm(d, seed + 5, 0.8, 3)) * 0.18
        out = i1[..., None] * col_a + i2[..., None] * col_b + i3[..., None] * col_c
        out += glow[..., None] * (col_a + col_b) * 0.5
        return (out * gain).astype(np.float32)

    return fn


def meteor_layer(seed, axis, count, length_deg=(7, 13), polar_deg=(35, 145), bright=1.0):
    a, b1, b2 = basis_for(axis)
    rng = np.random.default_rng(seed)
    streaks = []
    for _ in range(count):
        streaks.append(dict(
            theta=math.radians(rng.uniform(*polar_deg)),
            phi0=rng.uniform(0, 2 * math.pi),
            length=math.radians(rng.uniform(*length_deg)),
            b=bright * rng.uniform(0.75, 1.0),
        ))
    sense = -1.0 if REVERSE_METEORS else 1.0

    def fn(d):
        c = np.clip(d @ a, -1, 1)
        polar = np.arccos(c)
        phi = np.arctan2(d @ b2, d @ b1) * sense
        out = np.zeros(d.shape, dtype=np.float32)
        for s in streaks:
            sin_t = max(math.sin(s["theta"]), 0.2)
            L = s["length"] / sin_t  # angular length along the circle
            delta = np.mod(s["phi0"] * sense - phi, 2 * math.pi)  # distance behind the head
            frac = delta / L
            on = frac < 1.0
            dtheta = polar - s["theta"]
            width = 0.0030 * (1.0 - 0.75 * np.clip(frac, 0, 1)) + 0.0004
            prof = np.exp(-(dtheta / width) ** 2)
            fade = (1.0 - np.clip(frac, 0, 1)) ** 2.2
            val = np.where(on, prof * fade, 0.0)
            # bright head
            head_d = np.hypot(dtheta, delta * sin_t)
            val = val + np.exp(-(head_d / 0.0065) ** 2) * 0.9
            hot = np.array([1.0, 0.96, 0.86], dtype=np.float32)
            cool = np.array([0.45, 0.78, 1.0], dtype=np.float32)
            col = lerp(hot, cool, np.clip(frac, 0, 1) ** 0.7)
            out += (col * val[..., None] * s["b"]).astype(np.float32)
        return out

    return fn


def star_layer(seed, n, count=2600, sigma_px=0.85):
    """Stars are splatted using the inverse cube mapping (not per-pixel evaluated)."""
    rng = np.random.default_rng(seed)
    img = np.zeros((2 * n, 3 * n, 3), dtype=np.float32)
    palette = np.array([[0.75, 0.85, 1.0], [1.0, 1.0, 1.0], [1.0, 0.92, 0.75], [1.0, 0.8, 0.7]], dtype=np.float32)
    w = 3
    for _ in range(count):
        v = rng.normal(size=3)
        v /= np.linalg.norm(v)
        tile, s, t = dir_to_tile(v)
        mag = rng.random() ** 3.2
        bright = 0.25 + 0.75 * mag
        sig = sigma_px * (0.8 + 0.9 * mag)
        col = palette[rng.choice(4, p=[0.35, 0.35, 0.2, 0.1])] * bright
        r0, c0 = divmod(tile, 3)
        fx, fy = s * n, t * n
        ix, iy = int(fx), int(fy)
        for yy in range(iy - w, iy + w + 1):
            for xx in range(ix - w, ix + w + 1):
                if 0 <= xx < n and 0 <= yy < n:
                    g = math.exp(-((xx + 0.5 - fx) ** 2 + (yy + 0.5 - fy) ** 2) / (2 * sig * sig))
                    img[r0 * n + yy, c0 * n + xx] += col * g
    return img


def layout_test(n=256):
    img = Image.new("RGB", (3 * n, 2 * n))
    d = ImageDraw.Draw(img)
    colors = [(60, 60, 60), (30, 60, 200), (200, 50, 40), (230, 230, 230), (40, 170, 70), (220, 180, 30)]
    try:
        font = ImageFont.load_default(size=n // 6)
    except TypeError:
        font = ImageFont.load_default()
    for i in range(6):
        r, c = divmod(i, 3)
        x0, y0 = c * n, r * n
        d.rectangle([x0, y0, x0 + n - 1, y0 + n - 1], fill=colors[i], outline=(255, 0, 255), width=4)
        d.text((x0 + n // 2, y0 + n // 2), f"{i}\n{TILE_NAMES[i]}", fill=(0, 0, 0) if i == 3 else (255, 255, 255),
               font=font, anchor="mm", align="center")
        d.text((x0 + 10, y0 + 6), "^ up", fill=(255, 255, 0), font=font)
    return np.asarray(img, dtype=np.float32) / 255.0


# --------------------------------------------------------------------------
# pack writer
# --------------------------------------------------------------------------

# Only used if write_props(fade=True): night-only layers.
NIGHT = dict(startFadeIn="19:00", endFadeIn="20:00", startFadeOut="4:00", endFadeOut="5:00")


def write_props(path, idx, blend="add", axis=(0, 1, 0), speed=1, rotate=True, fade=False):
    a = unit(axis)
    lines = [f"source=minecraft:optifine/sky/world0/sky{idx}.png", f"blend={blend}"]
    if fade:
        lines += [f"{k}={v}" for k, v in NIGHT.items()]
    lines += [f"rotate={'true' if rotate else 'false'}", f"speed={speed}", f"axis={a[0]:.5f} {a[1]:.5f} {a[2]:.5f}"]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def write_pack(pack_id, description, layers):
    base = os.path.join(OUT, pack_id)
    if os.path.isdir(base):
        shutil.rmtree(base)
    sky = os.path.join(base, SKY_DIR)
    os.makedirs(sky, exist_ok=True)
    with open(os.path.join(base, "pack.mcmeta"), "w") as f:
        json.dump({"pack": {"pack_format": 75, "description": description}}, f, indent=2)
    for i, L in enumerate(layers, start=1):
        save_png(L["img"], os.path.join(sky, f"sky{i}.png"), opaque=L["props"].get("blend") == "replace")
        write_props(os.path.join(sky, f"sky{i}.properties"), i, **L["props"])
    print(f"  {pack_id}: {len(layers)} layers")


def main():
    _self_check()
    N_AUR, N_MET, N_STAR, N_NEB = 512, 1024, 1024, 512
    print("rendering layers ...")

    green = dict(low=(0.10, 1.00, 0.45), mid=(0.12, 0.85, 0.75), top=(0.55, 0.25, 0.95))
    crimson = dict(low=(1.00, 0.18, 0.28), mid=(0.95, 0.20, 0.60), top=(0.45, 0.25, 0.95))

    def aur(seed, base, height, pal, gain=1.5):
        return compose(aurora_layer(seed, base, height, gain=gain, **pal), N_AUR)

    def met(seed, axis, count, bright=1.0):
        return compose(meteor_layer(seed, axis, count, bright=bright * 1.6), N_MET)

    stars = star_layer(7, N_STAR)

    # two aurora curtains rotating in opposite directions -> flowing, shimmering motion
    def aurora_pair(seed, pal):
        return [
            dict(img=aur(seed, 18, 34, pal), props=dict(axis=(0, -1, 0), speed=1)),
            dict(img=aur(seed + 40, 30, 26, pal, gain=1.2), props=dict(axis=(0, 1, 0), speed=2)),
        ]

    # meteor layers: different axes + integer speeds so streaks never sync up
    def meteor_set(seed, n_layers=3, count=4):
        axes = [(0.45, 0.80, 0.40), (-0.50, 0.75, 0.43), (0.10, 0.70, -0.70)]
        speeds = [97, 131, 163]
        out = []
        for k in range(n_layers):
            out.append(dict(img=met(seed + k, axes[k], count),
                            props=dict(axis=axes[k], speed=speeds[k])))
        return out

    write_pack("northern_lights", "Sky Select: Northern Lights", aurora_pair(1, green))
    write_pack("crimson_aurora", "Sky Select: Crimson Aurora", aurora_pair(5, crimson))
    write_pack("meteor_shower", "Sky Select: Meteor Shower",
               [dict(img=stars, props=dict(axis=(0.3, 1, 0.2), speed=1))] + meteor_set(100, 3, 5))
    write_pack("polar_night", "Sky Select: Polar Night (aurora + meteors)",
               aurora_pair(9, green) + meteor_set(200, 2, 3))
    neb = compose(nebula_layer(3, (0.75, 0.20, 0.85), (0.15, 0.40, 1.0), (1.0, 0.55, 0.25)), N_NEB)
    write_pack("cosmic_nebula", "Sky Select: Cosmic Nebula",
               [dict(img=neb, props=dict(axis=(0.2, 1, 0.1), speed=1)),
                dict(img=stars, props=dict(axis=(0.2, 1, 0.1), speed=1))] + meteor_set(300, 1, 3))
    write_pack("layout_test", "Sky Select: face layout test (always visible)",
               [dict(img=layout_test(), props=dict(blend="replace", rotate=False, fade=False))])
    print("done ->", OUT)


if __name__ == "__main__":
    main()
