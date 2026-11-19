"""Dependency-free SVG charts shared by the HTML report and the web dashboard."""

from html import escape

PALETTE = {"bar": "#1f6f8b", "bar2": "#99c24d", "ink": "#1b2a35", "grid": "#d7dee3", "point": "#c0392b"}


def _fmt(v: float) -> str:
    if abs(v) >= 1e6:
        return f"{v / 1e6:.2f} mln"
    if abs(v) >= 1e3:
        return f"{v / 1e3:.0f} tys."
    return f"{v:.1f}".rstrip("0").rstrip(".")


def bar_chart(labels, values, title: str, unit: str = "", width: int = 560, color: str = None) -> str:
    n = len(values)
    if n == 0:
        return ""
    row_h, left, right, top = 22, 130, 70, 34
    height = top + n * row_h + 10
    vmax = max(max(values), 1e-9)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="{escape(title)}" class="chart">',
             f'<text x="0" y="16" font-size="13" font-weight="700" fill="{PALETTE["ink"]}">{escape(title)}</text>']
    for i, (label, value) in enumerate(zip(labels, values)):
        y = top + i * row_h
        w = (width - left - right) * value / vmax
        parts.append(f'<text x="{left - 8}" y="{y + 14}" font-size="11" text-anchor="end" '
                     f'fill="{PALETTE["ink"]}">{escape(str(label))}</text>')
        parts.append(f'<rect x="{left}" y="{y + 3}" width="{max(w, 1):.1f}" height="{row_h - 8}" '
                     f'fill="{color or PALETTE["bar"]}" rx="2"/>')
        parts.append(f'<text x="{left + w + 6:.1f}" y="{y + 14}" font-size="11" '
                     f'fill="{PALETTE["ink"]}">{_fmt(value)} {escape(unit)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def point_map(points, title: str, width: int = 560, height: int = 360) -> str:
    """Offline mini-map: points = [(lon, lat, label, size)] drawn in plate-carree with cos(lat) correction."""
    pts = [p for p in points if p[0] is not None and p[1] is not None]
    if not pts:
        return ""
    import math

    lon0 = min(p[0] for p in pts)
    lon1 = max(p[0] for p in pts)
    lat0 = min(p[1] for p in pts)
    lat1 = max(p[1] for p in pts)
    k = math.cos(math.radians((lat0 + lat1) / 2.0))
    span_x = max((lon1 - lon0) * k, 1e-6)
    span_y = max(lat1 - lat0, 1e-6)
    pad = 36
    scale = min((width - 2 * pad) / span_x, (height - 2 * pad - 14) / span_y)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
             f'aria-label="{escape(title)}" class="chart">',
             f'<rect x="0" y="0" width="{width}" height="{height}" fill="#f4f7f9" stroke="{PALETTE["grid"]}"/>',
             f'<text x="8" y="16" font-size="13" font-weight="700" fill="{PALETTE["ink"]}">{escape(title)}</text>']
    for lon, lat, label, size in pts:
        x = pad + (lon - lon0) * k * scale
        y = height - pad - (lat - lat0) * scale
        radius = 4 + 8 * size
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{PALETTE["point"]}" '
                     f'fill-opacity="0.65" stroke="#7b241c"/>')
        parts.append(f'<text x="{x:.1f}" y="{y + 3.5:.1f}" font-size="9" text-anchor="middle" fill="#fff" '
                     f'font-weight="700">{escape(str(label))}</text>')
    parts.append("</svg>")
    return "".join(parts)
