"""
Gera um retrato estilo "dot-matrix" (stippling) em SVG a partir de uma foto,
no mesmo espírito visual do banner de perfil de referência.

Usa GrabCut para isolar a pessoa do fundo antes de pontilhar, evitando que
elementos do ambiente (monitor, pôster, prateleira) virem ruído no resultado.
"""

import cv2
import numpy as np
from PIL import Image

SRC = "assets/source-photo.png"
OUT_SVG = "assets/visual-map.svg"

CANVAS = 340
N_POINTS = 8000
DOT_COLOR = "#a9bef3"
BG_COLOR = "#0a0e17"
MIN_R, MAX_R = 0.5, 1.3


def segment_person(img_full):
    H, W = img_full.shape[:2]
    x0, x1 = int(W * 0.18), int(W * 0.97)
    y0, y1 = int(H * 0.03), H
    img = img_full[y0:y1, x0:x1].copy()
    h, w = img.shape[:2]

    mask = np.full((h, w), cv2.GC_PR_BGD, np.uint8)

    pts = np.array([
        [int(w * 0.10), h],
        [int(w * 0.06), int(h * 0.66)],
        [int(w * 0.20), int(h * 0.50)],
        [int(w * 0.22), int(h * 0.16)],
        [int(w * 0.38), int(h * 0.03)],
        [int(w * 0.62), int(h * 0.03)],
        [int(w * 0.74), int(h * 0.20)],
        [int(w * 0.80), int(h * 0.42)],
        [int(w * 0.95), int(h * 0.55)],
        [w, h],
    ], np.int32)
    cv2.fillPoly(mask, [pts], cv2.GC_PR_FGD)

    cv2.rectangle(mask, (0, 0), (int(w * 0.22), int(h * 0.62)), cv2.GC_BGD, -1)
    cv2.rectangle(mask, (int(w * 0.68), 0), (w, int(h * 0.34)), cv2.GC_BGD, -1)
    cv2.rectangle(mask, (0, 0), (w, int(h * 0.02)), cv2.GC_BGD, -1)

    seeds_fgd = [
        (int(w * 0.50), int(h * 0.10), 18),
        (int(w * 0.35), int(h * 0.30), 14),
        (int(w * 0.63), int(h * 0.30), 14),
        (int(w * 0.50), int(h * 0.40), 16),
        (int(w * 0.50), int(h * 0.55), 16),
        (int(w * 0.50), int(h * 0.80), 30),
        (int(w * 0.20), int(h * 0.85), 20),
        (int(w * 0.80), int(h * 0.85), 20),
    ]
    for cx, cy, r in seeds_fgd:
        cv2.circle(mask, (cx, cy), r, cv2.GC_FGD, -1)

    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)
    cv2.grabCut(img, mask, None, bgdModel, fgdModel, 10, cv2.GC_INIT_WITH_MASK)

    fg = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype("uint8")
    kernel = np.ones((5, 5), np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel)

    n, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    if n > 1:
        largest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
        fg = np.where(labels == largest, 1, 0).astype("uint8")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return gray, fg


def build_probability_map(gray, fg_mask, work_res):
    gray_r = cv2.resize(gray, (work_res, work_res), interpolation=cv2.INTER_AREA)
    fg_r = cv2.resize(fg_mask, (work_res, work_res), interpolation=cv2.INTER_NEAREST)

    norm = 1.0 - (gray_r.astype(np.float64) / 255.0)  # 0 (claro) .. 1 (escuro)
    # piso mínimo para que peles claras ainda recebam uma textura leve de pontos,
    # em vez de ficarem completamente vazias
    floor = 0.22
    density = floor + (1 - floor) * norm
    density = density * fg_r  # zera tudo fora da silhueta

    p = density.flatten().astype(np.float64)
    if p.sum() == 0:
        raise RuntimeError("Máscara de primeiro plano vazia — ajuste as sementes do GrabCut.")
    p = p / p.sum()
    return p, work_res


def sample_points(p, work_res, n):
    idx = np.random.choice(len(p), size=n, replace=True, p=p)
    ys, xs = np.unravel_index(idx, (work_res, work_res))
    jitter = 0.9
    xs = xs.astype(np.float64) + np.random.uniform(-jitter, jitter, size=n)
    ys = ys.astype(np.float64) + np.random.uniform(-jitter, jitter, size=n)
    return xs, ys


def to_svg(xs, ys, work_res):
    scale = CANVAS / work_res
    circles = []
    rng = np.random.default_rng(42)
    radii = rng.uniform(MIN_R, MAX_R, size=len(xs))
    opac = rng.uniform(0.55, 1.0, size=len(xs))
    for x, y, r, o in zip(xs, ys, radii, opac):
        cx = round(x * scale, 2)
        cy = round(y * scale, 2)
        circles.append(f'<circle cx="{cx}" cy="{cy}" r="{round(r,2)}" fill="{DOT_COLOR}" fill-opacity="{round(o,2)}"/>')

    svg = f'''<svg width="{CANVAS}" height="{CANVAS}" viewBox="0 0 {CANVAS} {CANVAS}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Retrato em pontilhado">
  <rect width="{CANVAS}" height="{CANVAS}" fill="{BG_COLOR}"/>
  <g>
  {"".join(circles)}
  </g>
</svg>'''
    return svg


def main():
    np.random.seed(7)
    img_full = cv2.imread(SRC)
    gray, fg_mask = segment_person(img_full)
    p, work_res = build_probability_map(gray, fg_mask, work_res=220)
    xs, ys = sample_points(p, work_res, N_POINTS)
    svg = to_svg(xs, ys, work_res)
    with open(OUT_SVG, "w") as f:
        f.write(svg)
    print(f"Gerado: {OUT_SVG} ({len(svg)} bytes, {N_POINTS} pontos)")


if __name__ == "__main__":
    main()

