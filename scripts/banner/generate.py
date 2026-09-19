#!/usr/bin/env python3
"""Generate the animated GitHub profile banners.

Run from the repository root:
    python scripts/banner/generate.py
"""

from __future__ import annotations

import html
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets/source/mrr.png"
ASSETS = ROOT / "assets"
LOGOS = Path(__file__).resolve().parent / "logos"
DATA = Path(__file__).resolve().parent / "data"

W, H = 1180, 610
LOOP_SECONDS = 14.2
INTRO_SECONDS = 3.2
TRAVELLER_COUNT = 900
SEED = 314159

ROWS = [
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

THEMES = {
    "dark": {
        "bg": "#0A101F",
        "panel": "#0D1628",
        "panel2": "#101B30",
        "line": "#25344C",
        "muted": "#8291A8",
        "text": "#DDE7F5",
        "portrait": "#AA9BEF",
        "chrome": "#22D3EE",
        "accent": "#10B981",
        "shadow": "#02050B",
    },
    "light": {
        "bg": "#F6F8FA",
        "panel": "#FFFFFF",
        "panel2": "#EDF3F7",
        "line": "#CBD7E1",
        "muted": "#64748B",
        "text": "#172033",
        "portrait": "#4A3D7A",
        "chrome": "#0891B2",
        "accent": "#10B981",
        "shadow": "#AAB7C4",
    },
}


def make_logos() -> dict[str, Image.Image]:
    """Create clean 400px black-on-transparent silhouette sources."""
    LOGOS.mkdir(parents=True, exist_ok=True)
    size = 400
    logos: dict[str, Image.Image] = {}

    # Rust-inspired gear: twelve teeth, heavy annulus, and hub cutout.
    rust = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(rust)
    center = np.array([200.0, 200.0])
    outer: list[tuple[float, float]] = []
    for tooth in range(12):
        base = tooth * math.tau / 12
        for offset, radius in [
            (-0.42, 150), (-0.30, 178), (0.30, 178), (0.42, 150)
        ]:
            a = base + offset * math.tau / 12
            outer.append(tuple(center + radius * np.array([math.cos(a), math.sin(a)])))
    d.polygon(outer, fill="black")
    d.ellipse((70, 70, 330, 330), fill="black")
    d.ellipse((128, 128, 272, 272), fill=(0, 0, 0, 0))
    d.ellipse((174, 174, 226, 226), fill="black")
    logos["rust"] = rust

    # </> mark built from broad, rounded strokes.
    code = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(code)
    stroke = 42
    d.line([(154, 95), (66, 200), (154, 305)], fill="black", width=stroke, joint="curve")
    d.line([(246, 95), (334, 200), (246, 305)], fill="black", width=stroke, joint="curve")
    d.line([(225, 72), (174, 328)], fill="black", width=stroke)
    logos["code"] = code

    # Stellar-inspired four-point star with a small connected node network.
    stellar = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(stellar)
    star: list[tuple[float, float]] = []
    for i in range(16):
        a = -math.pi / 2 + i * math.pi / 8
        radius = 137 if i % 4 == 0 else (45 if i % 2 == 0 else 25)
        star.append((200 + math.cos(a) * radius, 200 + math.sin(a) * radius))
    d.polygon(star, fill="black")
    nodes = [(82, 112), (322, 106), (326, 300), (88, 316)]
    for a, b in zip(nodes, nodes[1:] + nodes[:1]):
        d.line([a, b], fill="black", width=12)
    for x, y in nodes:
        d.ellipse((x - 19, y - 19, x + 19, y + 19), fill="black")
    logos["stellar"] = stellar

    for name, image in logos.items():
        image.save(LOGOS / f"{name}.png", optimize=True)
    return logos


def floyd_steinberg(gray: np.ndarray) -> np.ndarray:
    """Serpentine 1-bit Floyd-Steinberg diffusion; True means a lit pixel."""
    work = gray.astype(np.float32) / 255.0
    out = np.zeros_like(work, dtype=bool)
    height, width = work.shape
    for y in range(height):
        left_to_right = y % 2 == 0
        xs = range(width) if left_to_right else range(width - 1, -1, -1)
        direction = 1 if left_to_right else -1
        for x in xs:
            old = work[y, x]
            new = 1.0 if old >= 0.5 else 0.0
            out[y, x] = bool(new)
            err = old - new
            nx = x + direction
            if 0 <= nx < width:
                work[y, nx] += err * 7 / 16
            if y + 1 < height:
                if 0 <= x - direction < width:
                    work[y + 1, x - direction] += err * 3 / 16
                work[y + 1, x] += err * 5 / 16
                if 0 <= nx < width:
                    work[y + 1, nx] += err * 1 / 16
    return out


def portrait_points(theme: str, rng: np.random.Generator) -> np.ndarray:
    """Return sampled x/y banner coordinates, dithered at higher internal
    resolution than the 300x340 display grid and then scaled down (a
    supersampled stipple: finer error-diffusion grid = smoother gradients
    and thinner features survive, e.g. eyebrows, individual hair strands)."""
    source = Image.open(SOURCE).convert("RGBA")

    # Corte centralizado que casa a proporção alvo (300x340) com o tamanho real
    # da imagem de origem, em vez de coordenadas fixas em pixels calibradas
    # pra uma foto específica — assim funciona com qualquer recorte/foto.
    w, h = source.size
    target_ratio = 300 / 340
    if w / h > target_ratio:
        new_w = round(h * target_ratio)
        x0 = (w - new_w) // 2
        crop_box = (x0, 0, x0 + new_w, h)
    else:
        new_h = round(w / target_ratio)
        y0 = (h - new_h) // 2
        crop_box = (0, y0, w, y0 + new_h)

    # Faz o dithering numa grade mais fina que a caixa final de exibição
    # (300x340) e só depois encolhe as posições pra caber nela — em vez de
    # já reduzir a imagem para 300x340 antes de decidir onde vai cada ponto.
    SUPERSAMPLE = 2.0
    work_w, work_h = round(300 * SUPERSAMPLE), round(340 * SUPERSAMPLE)
    scale = 300 / work_w  # == 340/work_h; usado pra remapear pro grid visual

    crop = source.crop(crop_box).resize((work_w, work_h), Image.Resampling.LANCZOS)
    rgb = crop.convert("RGB")
    alpha = np.asarray(crop.getchannel("A"), dtype=np.float32) / 255.0

    # Realce de contraste local antes do dithering: sem isso, o Floyd-Steinberg
    # sozinho tende a produzir um resultado "borrado" nas áreas de meio-tom
    # (rosto, sombras suaves). Equalizar só dentro da máscara do sujeito (não
    # do quadro todo, que é maior parte fundo transparente) usa a faixa tonal
    # inteira nos tons de pele/cabelo, e o unsharp bota de volta bordas nítidas
    # (contorno de óculos, fios de cabelo) que a equalização tende a suavizar.
    # (Testei CLAHE por blocos aqui — em fotos com boa resolução mas luz mais
    # uniforme, ele amplifica ruído de interpolação em manchas falsas ao redor
    # dos olhos em vez de detalhe real. Equalização global + unsharp mask deu
    # um resultado mais fiel à foto de verdade.)
    unsharp_radius = max(1, round(2 * SUPERSAMPLE))
    gray_img = ImageOps.grayscale(rgb)
    binmask = Image.fromarray((alpha > 0.5).astype(np.uint8) * 255)
    equalized = ImageOps.equalize(gray_img, mask=binmask)
    sharpened = equalized.filter(ImageFilter.UnsharpMask(radius=unsharp_radius, percent=180, threshold=2))
    contrasted = ImageEnhance.Contrast(sharpened).enhance(1.25)

    # Dithering Floyd-Steinberg de verdade (a mesma técnica anunciada em
    # "PTS ... · FS/SERPENTINE" no rodapé do VISUAL.MAP): inverte o cinza pra
    # que tons escuros (cabelo, sombra, roupa) recebam mais pontos, e usa o
    # alpha do recorte pra nunca desenhar fora da silhueta da pessoa.
    gray = np.asarray(contrasted, dtype=np.float32)
    inverted = 255.0 - gray
    dithered = floyd_steinberg(inverted)
    active = dithered & (alpha > 0.08)

    ys, xs = np.where(active)
    if len(xs) == 0:
        return np.zeros((0, 2), dtype=np.float32)
    points = np.column_stack((74 + xs * scale, 154 + ys * scale)).astype(np.float32)
    # Sem corte de quantidade: usa todo o detalhe real que o dithering
    # encontrou nessa foto. O SVG cresce em tamanho de arquivo, mas não em
    # número de elementos (os pontos são agrupados em faixas/paths), então
    # o navegador não fica mais pesado pra renderizar ou animar.
    return points


def sample_logo_points(
    image: Image.Image, rng: np.random.Generator, count: int
) -> np.ndarray:
    """Sample a silhouette into the portrait frame's visual coordinate space."""
    alpha = np.asarray(image.getchannel("A"))
    ys, xs = np.where(alpha > 127)
    chosen = rng.choice(len(xs), count, replace=len(xs) < count)
    # Logo occupies a centered 270x270 square inside VISUAL.MAP.
    return np.column_stack((89 + xs[chosen] * 0.675, 188 + ys[chosen] * 0.675)).astype(
        np.float32
    )


def transport(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Order target points by minimum-cost assignment from source points."""
    rows, cols = linear_sum_assignment(cdist(source, target, metric="sqeuclidean"))
    ordered = np.empty_like(target)
    ordered[rows] = target[cols]
    return ordered


def num(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def point_path(points: np.ndarray) -> str:
    """Aggregate adjacent horizontal one-pixel dots into compact SVG path runs."""
    if not len(points):
        return ""
    integer = np.rint(points).astype(int)
    unique = sorted({(int(x), int(y)) for x, y in integer}, key=lambda p: (p[1], p[0]))
    chunks: list[str] = []
    i = 0
    while i < len(unique):
        x0, y = unique[i]
        x1 = x0
        i += 1
        while i < len(unique) and unique[i][1] == y and unique[i][0] <= x1 + 1:
            x1 = unique[i][0]
            i += 1
        chunks.append(f"M{x0} {y}h{x1 - x0 + 1}")
    return "".join(chunks)


def dotted_leader(x1: float, x2: float, y: float) -> str:
    if x2 <= x1:
        return ""
    return "".join(f"M{x} {num(y)}h1" for x in np.arange(x1, x2, 5.0))


def text_width(text: str, font_size: float) -> float:
    """Stable monospace width used both for textLength and leader placement."""
    return len(text) * font_size * 0.605


def animate_values(points: list[np.ndarray], index: int) -> str:
    return ";".join(f"{num(p[index, 0])} {num(p[index, 1])}" for p in points)


def render_svg(
    theme_name: str,
    portrait: np.ndarray,
    logo_points: dict[str, np.ndarray],
    rng: np.random.Generator,
) -> str:
    t = THEMES[theme_name]
    n = min(TRAVELLER_COUNT, len(portrait))
    source = portrait[rng.choice(len(portrait), n, replace=False)]
    rust = transport(source, logo_points["rust"][:n])
    code = transport(rust, logo_points["code"][:n])
    stellar = transport(code, logo_points["stellar"][:n])

    # Explicit uneven phase boundaries: 3.0 portrait, 2.0 per logo,
    # and four 1.3 transitions = 14.2 seconds.
    times = [0, 3.0, 4.3, 6.3, 7.6, 9.6, 10.9, 12.9, 14.2]
    key_times = ";".join(num(v / LOOP_SECONDS) for v in times)
    # Returning each traveller to its exact starting portrait coordinate keeps
    # the repeat boundary seamless. All logo-to-logo morphs use optimal transport.
    frames = [source, source, rust, rust, code, code, stellar, stellar, source]
    opacity_values = "0;0;1;1;1;1;1;1;0"

    parts: list[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        'aria-labelledby="title desc">',
        "<title id=\"title\">Juan Rodrigues's live system profile</title>",
        '<desc id="desc">Animated terminal profile with a dithered portrait and '
        "code-related silhouettes.</desc>",
        "<defs>",
        '<filter id="shadow" x="-20%" y="-20%" width="140%" height="150%">'
        f'<feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="{t["shadow"]}" '
        'flood-opacity=".28"/></filter>',
        '<filter id="glow" x="-100%" y="-100%" width="300%" height="300%">'
        f'<feGaussianBlur stdDeviation="3" result="b"/><feFlood flood-color="{t["chrome"]}" '
        'flood-opacity=".35"/><feComposite in2="b" operator="in"/>'
        '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        '<clipPath id="visualClip"><rect x="49" y="124" width="390" height="414" rx="3"/></clipPath>',
        "</defs>",
        f'<rect width="{W}" height="{H}" rx="18" fill="{t["bg"]}"/>',
        f'<rect x="13" y="13" width="1154" height="584" rx="13" fill="{t["panel"]}" '
        f'stroke="{t["line"]}" filter="url(#shadow)"/>',
        f'<path d="M13 62H1167" stroke="{t["line"]}"/>',
        '<circle cx="38" cy="38" r="6" fill="#FF5F57"/>'
        '<circle cx="59" cy="38" r="6" fill="#FEBC2E"/>'
        '<circle cx="80" cy="38" r="6" fill="#28C840"/>',
        f'<text x="590" y="43" text-anchor="middle" fill="{t["muted"]}" '
        'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="13" '
        'letter-spacing=".4">profile.sh --live</text>',
        # Left visual frame.
        f'<rect x="35" y="88" width="418" height="472" rx="6" fill="{t["panel2"]}" '
        f'stroke="{t["line"]}"/>',
        f'<path d="M35 124H453" stroke="{t["line"]}"/>',
        f'<text x="49" y="111" fill="{t["chrome"]}" '
        'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="13" '
        'font-weight="700" letter-spacing="1.2">VISUAL.MAP</text>',
        f'<text x="438" y="111" text-anchor="end" fill="{t["muted"]}" '
        'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="11">300×340 / 1-BIT</text>',
        f'<path d="M49 141h12M49 141v12M439 141h-12M439 141v12M49 539h12M49 539v-12'
        f'M439 539h-12M439 539v-12" fill="none" stroke="{t["chrome"]}" opacity=".55"/>',
        '<g clip-path="url(#visualClip)" shape-rendering="crispEdges">',
        # Loop layer stays visible at t=0 so camo/static first frames still show the face.
        # Intro duplicate below shimmers on top, then hands off at 3.2s.
        '<g opacity="1">',
    ]

    # Dense portrait drift: 94 independently noisy bands moving toward Rust's centroid.
    rust_centroid = rust.mean(axis=0)
    band_ids = rng.integers(0, 94, size=len(portrait))
    noise = rng.normal(0, 4, size=(94, 2))
    for band in range(94):
        pts = portrait[band_ids == band]
        if not len(pts):
            continue
        centroid = pts.mean(axis=0)
        delta = (rust_centroid - centroid) * 0.18 + noise[band]
        d = point_path(pts)
        parts.append(
            f'<path d="{d}" fill="none" stroke="{t["portrait"]}" stroke-width="1" '
            'opacity=".94">'
            f'<animateTransform attributeName="transform" type="translate" begin="{INTRO_SECONDS}s" '
            f'dur="{LOOP_SECONDS}s" repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="{key_times}" values="0 0;0 0;{num(delta[0])} {num(delta[1])};'
            f'{num(delta[0])} {num(delta[1])};0 0;0 0;0 0;0 0;0 0"/>'
            f'<animate attributeName="opacity" begin="{INTRO_SECONDS}s" dur="{LOOP_SECONDS}s" '
            f'repeatCount="indefinite" keyTimes="{key_times}" '
            'values=".94;.94;0;0;0;0;0;0;.94"/></path>'
        )

    # Optimal-transport travellers, represented as tiny path squares (never glyphs).
    for i in range(n):
        positions = animate_values(frames, i)
        parts.append(
            f'<path d="M-.65-.65h1.3v1.3h-1.3z" fill="{t["portrait"]}">'
            f'<animateTransform attributeName="transform" type="translate" begin="{INTRO_SECONDS}s" '
            f'dur="{LOOP_SECONDS}s" repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="{key_times}" values="{positions}"/>'
            f'<animate attributeName="opacity" begin="{INTRO_SECONDS}s" dur="{LOOP_SECONDS}s" '
            f'repeatCount="indefinite" calcMode="linear" keyTimes="{key_times}" '
            f'values="{opacity_values}"/></path>'
        )
    parts.append("</g>")

    # One-shot scattered intro: sixty random, interleaved point groups.
    intro_ids = rng.integers(0, 60, size=len(portrait))
    order = rng.permutation(60)
    starts = np.empty(60)
    starts[order] = np.linspace(0.05, 1.2, 60)
    for group in range(60):
        pts = portrait[intro_ids == group]
        if not len(pts):
            continue
        parts.append(
            f'<path d="{point_path(pts)}" fill="none" stroke="{t["portrait"]}" '
            'stroke-width="1" opacity="0">'
            f'<animate attributeName="opacity" begin="{num(starts[group])}s" dur=".8s" '
            'values="0;1" fill="freeze"/>'
            '<animate attributeName="opacity" begin="3.08s" dur=".12s" values="1;0" fill="freeze"/>'
            "</path>"
        )
    parts.extend(
        [
            "</g>",
            # Small frame telemetry.
            f'<text x="58" y="551" fill="{t["muted"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="10">'
            f'PTS {len(portrait):05d} · FS/SERPENTINE</text>',
            # Right information panel.
            f'<rect x="474" y="88" width="672" height="472" rx="6" fill="{t["panel2"]}" '
            f'stroke="{t["line"]}"/>',
            f'<path d="M474 124H1146" stroke="{t["line"]}"/>',
            f'<text x="490" y="111" fill="{t["chrome"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="13" '
            'font-weight="700" letter-spacing="1.2">SYSTEM.INFO</text>',
            # LIVE badge and handle pill.
            '<g filter="url(#glow)"><circle cx="893" cy="106" r="4" fill="#FF4D5A">'
            '<animate attributeName="opacity" values="1;.3;1" dur="1.6s" repeatCount="indefinite"/>'
            '</circle></g>',
            '<text x="905" y="111" fill="#FF4D5A" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="12" '
            'font-weight="700">LIVE</text>',
            f'<rect x="{944}" y="94" width="184" height="24" rx="12" fill="{t["chrome"]}" opacity=".16" '
            f'stroke="{t["chrome"]}"/>',
            f'<text x="{944+92}" y="111" text-anchor="middle" fill="{t["chrome"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="14" '
            'font-weight="700">@JuanRodrigues-Dev</text>',
        ]
    )

    value_right = 1127.0
    row_y = 153.0
    row_step = (497.0 - row_y) / max(len(ROWS) - 1, 1)
    for label, value in ROWS:
        value_len = text_width(value, 14)
        label_len = text_width(label, 14)
        leader_start = 491 + label_len + 12
        leader_end = value_right - value_len - 12
        parts.extend(
            [
                f'<text x="491" y="{num(row_y)}" fill="{t["muted"]}" '
                'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="14">'
                f"{html.escape(label)}</text>",
                f'<path d="{dotted_leader(leader_start, leader_end, row_y - 4)}" '
                f'fill="none" stroke="{t["line"]}" stroke-width="1" shape-rendering="crispEdges"/>',
                f'<text x="{num(value_right)}" y="{num(row_y)}" text-anchor="end" '
                f'fill="{t["text"]}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
                f'font-size="14" textLength="{num(value_len)}" lengthAdjust="spacingAndGlyphs">'
                f"{html.escape(value)}</text>",
            ]
        )
        row_y += row_step

    parts.extend(
        [
            f'<path d="M490 530H1130" stroke="{t["line"]}"/>',
            f'<text x="491" y="548" fill="{t["accent"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="11">'
            "● ALL SYSTEMS NOMINAL</text>",
            f'<text x="1128" y="548" text-anchor="end" fill="{t["muted"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="11">'
            "UTC-4 · LATAM NODE</text>",
            "</svg>",
        ]
    )
    return "".join(parts)


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing source portrait: {SOURCE}")
    ASSETS.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    logos = make_logos()

    # Cache theme-specific dither points as reproducible source data.
    portraits: dict[str, np.ndarray] = {}
    for index, theme in enumerate(THEMES):
        rng = np.random.default_rng(SEED + index)
        points = portrait_points(theme, rng)
        portraits[theme] = points
        np.save(DATA / f"portrait-{theme}.npy", points)

    for index, theme in enumerate(THEMES):
        rng = np.random.default_rng(SEED + 100 + index)
        sampled = {
            name: sample_logo_points(image, rng, TRAVELLER_COUNT)
            for name, image in logos.items()
        }
        for name, points in sampled.items():
            np.save(DATA / f"{name}-{theme}.npy", points)
        svg = render_svg(theme, portraits[theme], sampled, rng)
        output = ASSETS / f"banner-{theme}.v9.svg"
        output.write_text(svg, encoding="utf-8")
        byte_size = output.stat().st_size
        print(
            f"{output.relative_to(ROOT)}: {byte_size:,} bytes "
            f"({byte_size / 1024:.1f} KiB), {len(portraits[theme]):,} portrait dots, "
            f"{TRAVELLER_COUNT} travellers"
        )

    for name in logos:
        output = LOGOS / f"{name}.png"
        print(f"{output.relative_to(ROOT)}: {output.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
