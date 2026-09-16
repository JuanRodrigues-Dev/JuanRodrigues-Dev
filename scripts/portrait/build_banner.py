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
    n = len(xs)
    radii = rng.uniform(0.45, 1.15, size=n)
    opac = rng.uniform(0.55, 1.0, size=n)

    # Agrupa os pontos em "faixas" para animar em blocos (mais leve que animar
    # cada ponto individualmente, mas ainda dá um efeito orgânico de "respiração").
    n_groups = 22
    group_ids = rng.integers(0, n_groups, size=n)

    KEYTIMES = "0;0.2;0.3;0.4;0.5;0.7;0.8;0.9;1"
    DUR = "14.2s"
    BEGIN = "1.2s"

    groups_svg = []
    for g in range(n_groups):
        mask = group_ids == g
        if not mask.any():
            continue
        dx = round(rng.uniform(-6, 6), 1)
        dy = round(rng.uniform(-10, 4), 1)
        circles = []
        for x, y, r, o in zip(xs[mask], ys[mask], radii[mask], opac[mask]):
            cx = round(offset_x + x * scale, 2)
            cy = round(offset_y + y * scale, 2)
            circles.append(f'<circle cx="{cx}" cy="{cy}" r="{round(r,2)}" fill="{THEME["dot"]}" fill-opacity="{round(o,2)}"/>')
        groups_svg.append(
            f'<g>{"".join(circles)}'
            f'<animateTransform attributeName="transform" type="translate" begin="{BEGIN}" dur="{DUR}" '
            f'repeatCount="indefinite" calcMode="linear" keyTimes="{KEYTIMES}" '
            f'values="0 0;0 0;{dx} {dy};{dx} {dy};0 0;0 0;0 0;0 0;0 0"/></g>'
        )
    return "".join(groups_svg)


def traveler_dots(box_x, box_y, box_w, box_h, count=26, seed=99):
    """Pequenas partículas que atravessam o retrato piscando, dando uma
    sensação de 'sinal ao vivo' durante a janela de animação."""
    rng = np.random.default_rng(seed)
    KEYTIMES = "0;0.2;0.3;0.4;0.5;0.7;0.8;0.9;1"
    DUR = "14.2s"
    BEGIN = "1.2s"
    parts = []
    for _ in range(count):
        x0 = rng.uniform(box_x + 10, box_x + box_w - 10)
        y0 = rng.uniform(box_y + 10, box_y + box_h - 10)
        x1 = x0 + rng.uniform(-24, 24)
        y1 = y0 + rng.uniform(-30, 10)
        parts.append(
            f'<circle cx="0" cy="0" r="1.1" fill="{THEME["dot"]}">'
            f'<animateTransform attributeName="transform" type="translate" begin="{BEGIN}" dur="{DUR}" '
            f'repeatCount="indefinite" calcMode="linear" keyTimes="{KEYTIMES}" '
            f'values="{x0:.1f} {y0:.1f};{x0:.1f} {y0:.1f};{x1:.1f} {y1:.1f};{x1:.1f} {y1:.1f};'
            f'{x0:.1f} {y0:.1f};{x0:.1f} {y0:.1f};{x0:.1f} {y0:.1f};{x0:.1f} {y0:.1f};{x0:.1f} {y0:.1f}"/>'
            f'<animate attributeName="opacity" begin="{BEGIN}" dur="{DUR}" repeatCount="indefinite" '
            f'keyTimes="{KEYTIMES}" values="0;0;1;1;1;1;0;0;0"/>'
            f'</circle>'
        )
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
    travelers_svg = traveler_dots(left_x + 14, body_y + 46, left_w - 28, body_h - 74)

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
  <text x="{W/2}" y="{pad+title_h/2+4}" fill="{THEME["subtext"]}" font-size="13" font-family="{THEME["font"]}" text-anchor="middle">profile.sh --live<tspan fill="{THEME["accent"]}">▍<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/></tspan></text>
  <line x1="{pad}" y1="{pad+title_h}" x2="{W-pad}" y2="{pad+title_h}" stroke="{THEME["border"]}" stroke-width="1"/>

  <!-- painel esquerdo: retrato -->
  <rect x="{left_x}" y="{body_y}" width="{left_w}" height="{body_h}" rx="10" fill="{THEME["panel"]}" stroke="{THEME["border"]}"/>
  <text x="{left_x+16}" y="{body_y+28}" fill="{THEME["accent"]}" font-size="13" font-family="{THEME["font"]}" font-weight="700">VISUAL.MAP</text>
  <text x="{left_x+left_w-16}" y="{body_y+28}" fill="{THEME["subtext"]}" font-size="10.5" font-family="{THEME["font"]}" text-anchor="end">{left_w-28}x{int(body_h-74)} · 1-BIT</text>
  <rect x="{left_x+14}" y="{body_y+46}" width="{left_w-28}" height="{body_h-74}" fill="{THEME["bg"]}"/>
  {portrait_svg}
  {travelers_svg}
  <rect x="{left_x+14}" y="{body_y+46}" width="{left_w-28}" height="{body_h-74}" fill="none" stroke="{THEME["border_soft"]}"/>
  <text x="{left_x+16}" y="{body_y+body_h-14}" fill="{THEME["subtext"]}" font-size="10" font-family="{THEME["font"]}">PTS {N_POINTS} · GRABCUT+STIPPLE</text>

  <!-- painel direito: informações -->
  <rect x="{right_x}" y="{body_y}" width="{right_w}" height="{body_h}" rx="10" fill="{THEME["panel"]}" stroke="{THEME["border"]}"/>
  <text x="{right_x+22}" y="{body_y+28}" fill="{THEME["accent"]}" font-size="13" font-family="{THEME["font"]}" font-weight="700">SYSTEM.INFO</text>
  <circle cx="{dot_cx}" cy="{body_y+24}" r="4" fill="{THEME["red"]}">
    <animate attributeName="opacity" values="1;1;0.25;1" keyTimes="0;0.4;0.7;1" dur="1.6s" repeatCount="indefinite"/>
  </circle>
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
