"""
Monta o banner completo do perfil, no estilo "terminal" da referência:
- barra de título com "semáforo" de janela
- painel esquerdo: retrato em pontilhado (VISUAL.MAP)
- painel direito: tabela de informações (SYSTEM.INFO)
- rodapé com status

Depende de build_portrait.py para a segmentação/pontilhado do retrato.
"""

import sys
import os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_portrait import segment_person, build_probability_map, sample_points
import cv2

SRC = "assets/source-photo.png"
OUT_SVG = "assets/banner.svg"

# ---------------- tema ----------------
THEME = {
    "bg": "#0a0e17",
    "panel": "#0d121e",
    "border": "#1f2937",
    "border_soft": "#182031",
    "text": "#c9d1d9",
    "subtext": "#5b6577",
    "accent": "#7dd3c0",     # ciano/verde-água dos títulos (VISUAL.MAP / SYSTEM.INFO)
    "value": "#dbe4f0",
    "dot": "#a9bef3",
    "green": "#3ddc84",
    "red": "#ff5f57",
    "yellow": "#febc2e",
    "font": "'JetBrains Mono','Fira Code',monospace",
}

FIELDS = [
    ("Subject", "Juan Rodrigues"),
    ("Role", "Estudante de ADS · Dev em formação"),
    ("Origin", "Cajazeiras, PB · Brasil"),
    ("Education", "IFPB · Campus Cajazeiras"),
    ("Status", "Estudando + Construindo + Entregando"),
    ("ToolChain", "VS Code · Git · Docker"),
    ("Core.Lang", "Java · JavaScript · TypeScript · Python"),
    ("Core.Frontend", "React · Vite · Tailwind"),
    ("Core.Backend", "Node.js · Express · Prisma"),
    ("Core.Database", "MySQL · PostgreSQL · MongoDB · SQLite"),
    ("Grid.Mail", "—"),
    ("Grid.LinkedIn", "/in/juangomes"),
    ("Grid.GitHub", "JuanRodrigues-Dev"),
]

USERNAME_PILL = "@JuanRodrigues-Dev"
N_POINTS = 7000


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_dot_points():
    img_full = cv2.imread(SRC)
    gray, fg_mask = segment_person(img_full)
    p, work_res = build_probability_map(gray, fg_mask, work_res=220)
    xs, ys = sample_points(p, work_res, N_POINTS)
    return xs, ys, work_res


def portrait_group(xs, ys, work_res, box_x, box_y, box_w, box_h):
    scale = min(box_w, box_h) / work_res
    offset_x = box_x + (box_w - work_res * scale) / 2
    offset_y = box_y + (box_h - work_res * scale) / 2

    rng = np.random.default_rng(11)
    radii = rng.uniform(0.45, 1.15, size=len(xs))
    opac = rng.uniform(0.55, 1.0, size=len(xs))

    parts = []
    for x, y, r, o in zip(xs, ys, radii, opac):
        cx = round(offset_x + x * scale, 2)
        cy = round(offset_y + y * scale, 2)
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{round(r,2)}" fill="{THEME["dot"]}" fill-opacity="{round(o,2)}"/>')
    return "".join(parts)


def build_svg():
    xs, ys, work_res = build_dot_points()

    W, H = 900, 500
    pad = 22
    title_h = 40
    footer_h = 34
    gap = 16

    body_y = pad + title_h + gap
    body_h = H - body_y - footer_h - gap - pad

    left_w = 320
    left_x = pad
    right_x = left_x + left_w + gap
    right_w = W - pad - right_x

    portrait_svg = portrait_group(xs, ys, work_res, left_x + 14, body_y + 46, left_w - 28, body_h - 74)

    # ---- linhas da tabela ----
    row_h = (body_h - 70) / len(FIELDS)
    rows_svg = []
    for i, (label, value) in enumerate(FIELDS):
        y = body_y + 62 + i * row_h
        rows_svg.append(
            f'<text x="{right_x+22}" y="{y}" fill="{THEME["subtext"]}" font-size="12.5" font-family="{THEME["font"]}">{esc(label)}</text>'
            f'<text x="{right_x+right_w-22}" y="{y}" fill="{THEME["value"]}" font-size="12.5" font-family="{THEME["font"]}" text-anchor="end" font-weight="600">{esc(value)}</text>'
        )
        if i < len(FIELDS) - 1:
            ly = y + row_h * 0.42
            rows_svg.append(f'<line x1="{right_x+22}" y1="{ly}" x2="{right_x+right_w-22}" y2="{ly}" stroke="{THEME["border_soft"]}" stroke-width="1"/>')
    rows_svg = "\n  ".join(rows_svg)

    text_est_w = len(USERNAME_PILL) * 6.5
    pill_w = text_est_w + 26
    pill_x = right_x + right_w - 22 - pill_w
    live_font_w = len("LIVE") * 6.8
    live_text_x = pill_x - 14
    dot_cx = live_text_x - live_font_w - 10

    svg = f'''<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Banner de perfil">
  <rect width="{W}" height="{H}" rx="14" fill="{THEME["bg"]}"/>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{THEME["border"]}"/>

  <!-- barra de título -->
  <circle cx="{pad+10}" cy="{pad+title_h/2}" r="5.5" fill="{THEME["red"]}"/>
  <circle cx="{pad+30}" cy="{pad+title_h/2}" r="5.5" fill="{THEME["yellow"]}"/>
  <circle cx="{pad+50}" cy="{pad+title_h/2}" r="5.5" fill="{THEME["green"]}"/>
  <text x="{W/2}" y="{pad+title_h/2+4}" fill="{THEME["subtext"]}" font-size="13" font-family="{THEME["font"]}" text-anchor="middle">profile.sh --live</text>
  <line x1="{pad}" y1="{pad+title_h}" x2="{W-pad}" y2="{pad+title_h}" stroke="{THEME["border"]}" stroke-width="1"/>

  <!-- painel esquerdo: retrato -->
  <rect x="{left_x}" y="{body_y}" width="{left_w}" height="{body_h}" rx="10" fill="{THEME["panel"]}" stroke="{THEME["border"]}"/>
  <text x="{left_x+16}" y="{body_y+28}" fill="{THEME["accent"]}" font-size="13" font-family="{THEME["font"]}" font-weight="700">VISUAL.MAP</text>
  <text x="{left_x+left_w-16}" y="{body_y+28}" fill="{THEME["subtext"]}" font-size="10.5" font-family="{THEME["font"]}" text-anchor="end">{left_w-28}x{int(body_h-74)} · 1-BIT</text>
  <rect x="{left_x+14}" y="{body_y+46}" width="{left_w-28}" height="{body_h-74}" fill="{THEME["bg"]}"/>
  {portrait_svg}
  <rect x="{left_x+14}" y="{body_y+46}" width="{left_w-28}" height="{body_h-74}" fill="none" stroke="{THEME["border_soft"]}"/>
  <text x="{left_x+16}" y="{body_y+body_h-14}" fill="{THEME["subtext"]}" font-size="10" font-family="{THEME["font"]}">PTS {N_POINTS} · GRABCUT+STIPPLE</text>

  <!-- painel direito: informações -->
  <rect x="{right_x}" y="{body_y}" width="{right_w}" height="{body_h}" rx="10" fill="{THEME["panel"]}" stroke="{THEME["border"]}"/>
  <text x="{right_x+22}" y="{body_y+28}" fill="{THEME["accent"]}" font-size="13" font-family="{THEME["font"]}" font-weight="700">SYSTEM.INFO</text>
  <circle cx="{dot_cx}" cy="{body_y+24}" r="4" fill="{THEME["red"]}"/>
  <text x="{live_text_x}" y="{body_y+28}" fill="{THEME["red"]}" font-size="11" font-family="{THEME["font"]}" font-weight="700" text-anchor="end">LIVE</text>
  <rect x="{pill_x}" y="{body_y+12}" width="{pill_w}" height="20" rx="10" fill="{THEME["border_soft"]}"/>
  <text x="{pill_x+pill_w/2}" y="{body_y+26}" fill="{THEME["value"]}" font-size="10.5" font-family="{THEME["font"]}" text-anchor="middle">{esc(USERNAME_PILL)}</text>
  <line x1="{right_x+22}" y1="{body_y+40}" x2="{right_x+right_w-22}" y2="{body_y+40}" stroke="{THEME["border"]}" stroke-width="1"/>
  {rows_svg}

  <!-- rodapé -->
  <circle cx="{pad+6}" cy="{H-pad-footer_h/2+8}" r="4" fill="{THEME["green"]}"/>
  <text x="{pad+18}" y="{H-pad-footer_h/2+12}" fill="{THEME["subtext"]}" font-size="11" font-family="{THEME["font"]}">ALL SYSTEMS NOMINAL</text>
  <text x="{W-pad}" y="{H-pad-footer_h/2+12}" fill="{THEME["subtext"]}" font-size="11" font-family="{THEME["font"]}" text-anchor="end">UTC-3 · PB, BR</text>
</svg>'''
    return svg


def main():
    svg = build_svg()
    with open(OUT_SVG, "w") as f:
        f.write(svg)
    print(f"Gerado: {OUT_SVG} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
