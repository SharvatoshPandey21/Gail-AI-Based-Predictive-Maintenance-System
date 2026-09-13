"""
style.py (v3 -- modern SaaS, cleaned up)

WHY THIS VERSION EXISTS:
Deep navy background with a soft glow, translucent "glass" cards, a
violet-to-cyan gradient on headings/key numbers, pill-shaped glowing
risk badges, sparkline trends and a top accent bar on asset cards, and
a circular fleet-health ring on the Overview page. Data renders in
JetBrains Mono so numbers stay easy to scan.

This file was previously corrupted by an editing mistake that silently
merged risk_pill_html's body into hero_ring_html as dead code and left
a duplicate sparkline_svg definition -- both are fixed here. Every
function below is defined exactly once.
"""

import streamlit as st

# ---- Color tokens ----
COLORS = {
    "bg": "#0A0E1A",
    "surface": "rgba(255,255,255,0.045)",
    "surface_solid": "#12172A",
    "border": "rgba(255,255,255,0.09)",
    "ink": "#F1F5F9",
    "muted": "#8E9BB3",
    "accent": "#22D3EE",
    "accent2": "#7C3AED",
    "success": "#10B981",
    "success_soft": "rgba(16,185,129,0.14)",
    "warning": "#F59E0B",
    "warning_soft": "rgba(245,158,11,0.14)",
    "danger": "#F43F5E",
    "danger_soft": "rgba(244,63,94,0.14)",
}

RISK_COLOR = {
    "LOW": COLORS["success"],
    "MEDIUM": COLORS["warning"],
    "HIGH": COLORS["danger"],
}
RISK_SOFT = {
    "LOW": COLORS["success_soft"],
    "MEDIUM": COLORS["warning_soft"],
    "HIGH": COLORS["danger_soft"],
}

GRADIENT = f"linear-gradient(90deg, {COLORS['accent2']}, {COLORS['accent']})"


def inject_theme():
    st.markdown(
        f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20,500,0,0" rel="stylesheet">
        <style>
            .material-symbols-outlined {{
                font-family: 'Material Symbols Outlined';
                font-weight: 500;
                font-style: normal;
                vertical-align: middle;
                line-height: 1;
            }}
            html, body, [class*="css"] {{
                font-family: 'Sora', sans-serif;
            }}
            .stApp {{
                background:
                    radial-gradient(circle at 15% 0%, rgba(124,58,237,0.16), transparent 45%),
                    radial-gradient(circle at 85% 15%, rgba(34,211,238,0.10), transparent 40%),
                    {COLORS['bg']};
                color: {COLORS['ink']};
            }}
            [data-testid="stHeader"] {{
                background-color: transparent;
            }}
            [data-testid="stToolbar"] {{
                color: {COLORS['ink']};
            }}
            [data-testid="stSidebar"] {{
                background-color: rgba(10,14,26,0.85);
                border-right: 1px solid {COLORS['border']};
                backdrop-filter: blur(12px);
            }}
            [data-testid="stSidebar"] * {{
                color: {COLORS['ink']} !important;
            }}
            [data-testid="stMetricLabel"] {{
                color: {COLORS['muted']} !important;
                font-size: 0.78rem !important;
                text-transform: uppercase;
                letter-spacing: 0.06em;
            }}
            [data-testid="stMetricValue"] {{
                color: {COLORS['ink']} !important;
                font-family: 'JetBrains Mono', monospace;
                font-weight: 700 !important;
            }}
            [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] p,
            [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] li,
            [data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] p,
            [data-testid="stAppViewContainer"] [data-testid="stWidgetLabel"] p,
            [data-testid="stAppViewContainer"] label,
            [data-testid="stAppViewContainer"] .stSelectbox div {{
                color: {COLORS['ink']} !important;
            }}
            .mono-value {{
                font-family: 'JetBrains Mono', monospace;
                font-weight: 700;
            }}
            .panel-card {{
                position: relative;
                overflow: hidden;
                background: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 16px;
                padding: 22px 24px;
                margin-bottom: 14px;
                backdrop-filter: blur(14px);
                box-shadow: 0 4px 24px rgba(0,0,0,0.25);
                transition: border-color 0.15s ease, transform 0.15s ease;
            }}
            .panel-card:hover {{
                border-color: rgba(255,255,255,0.18);
                transform: translateY(-2px);
            }}
            .panel-card.with-accent::before {{
                content: "";
                position: absolute;
                top: 0; left: 0; right: 0;
                height: 3px;
                background: var(--accent-color, transparent);
            }}
            .risk-pill {{
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 4px 12px;
                border-radius: 999px;
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.04em;
                text-transform: uppercase;
            }}
            .status-dot {{
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
            }}
            .eyebrow {{
                text-transform: uppercase;
                letter-spacing: 0.1em;
                font-size: 0.7rem;
                font-weight: 600;
                color: {COLORS['muted']};
                margin-bottom: 4px;
            }}
            .gradient-heading {{
                background: {GRADIENT};
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-weight: 700;
                display: inline-block;
            }}
            hr {{ border-color: {COLORS['border']}; }}
            .stNumberInput input, .stTextInput input, .stSelectbox div[data-baseweb="select"] {{
                background-color: {COLORS['surface_solid']} !important;
                color: {COLORS['ink']} !important;
                border-color: {COLORS['border']} !important;
                border-radius: 10px !important;
            }}
            .stDataFrame {{
                background-color: {COLORS['surface_solid']};
                border-radius: 12px;
            }}
            .stButton button, .stFormSubmitButton button {{
                background: {GRADIENT} !important;
                color: #0A0E1A !important;
                font-weight: 700 !important;
                border: none !important;
                border-radius: 10px !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def icon_html(name: str, size: int = 18, color: str = None) -> str:
    """Renders a Material Symbols icon inline, e.g. icon_html('factory')."""
    style = f"font-size:{size}px;"
    if color:
        style += f" color:{color};"
    return f'<span class="material-symbols-outlined" style="{style}">{name}</span>'


def sparkline_svg(values: list, color: str, width: int = 140, height: int = 36) -> str:
    """Builds a minimal inline SVG line chart from a list of numbers --
    used on asset cards to show a quick trend shape (e.g. last 24h of
    vibration) alongside the headline health score."""
    if not values or len(values) < 2:
        return ""

    lo, hi = min(values), max(values)
    span = (hi - lo) or 1

    n = len(values)
    points = []
    for i, v in enumerate(values):
        x = (i / (n - 1)) * width
        y = height - ((v - lo) / span) * (height - 4) - 2
        points.append(f"{x:.1f},{y:.1f}")
    points_str = " ".join(points)
    fill_points = f"0,{height} {points_str} {width},{height}"
    last_x, last_y = points[-1].split(",")

    return f"""
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="display:block;">
        <polygon points="{fill_points}" fill="{color}" opacity="0.12"></polygon>
        <polyline points="{points_str}" fill="none" stroke="{color}" stroke-width="2"
                  stroke-linecap="round" stroke-linejoin="round"></polyline>
        <circle cx="{last_x}" cy="{last_y}" r="2.5" fill="{color}" />
    </svg>
    """


def hero_ring_html(avg_health: float) -> str:
    """A large circular progress ring showing average fleet health --
    the focal point at the top of the Overview page."""
    color = COLORS["success"] if avg_health >= 70 else (COLORS["warning"] if avg_health >= 40 else COLORS["danger"])
    pct = max(0, min(100, avg_health))
    return f"""
    <div style="display:flex; align-items:center; gap:24px; margin-bottom:22px;">
        <div style="
            width:104px; height:104px; border-radius:50%; flex-shrink:0;
            background: conic-gradient({color} {pct * 3.6:.0f}deg, rgba(255,255,255,0.08) 0deg);
            display:flex; align-items:center; justify-content:center;
        ">
            <div style="
                width:82px; height:82px; border-radius:50%; background:{COLORS['bg']};
                display:flex; align-items:center; justify-content:center; flex-direction:column;
            ">
                <div class="mono-value" style="font-size:1.5rem; color:{color};">{avg_health:.0f}%</div>
            </div>
        </div>
        <div>
            <div class="eyebrow">Fleet average</div>
            <div style="font-size:1.3rem; font-weight:700; color:{COLORS['ink']};">
                Overall health score
            </div>
            <div style="font-size:0.85rem; color:{COLORS['muted']}; margin-top:2px;">
                Averaged across every asset's most recent reading
            </div>
        </div>
    </div>
    """


def risk_pill_html(risk_level: str) -> str:
    """A pill-shaped glowing badge showing risk level -- used on both
    the Overview cards and the Manual Entry result card."""
    color = RISK_COLOR.get(risk_level, COLORS["muted"])
    soft = RISK_SOFT.get(risk_level, "rgba(255,255,255,0.08)")
    return (
        f'<span class="risk-pill" style="background:{soft}; color:{color};">'
        f'<span class="status-dot" style="background:{color}; box-shadow:0 0 6px {color}99;"></span>'
        f'{risk_level}</span>'
    )


def status_dot_html(risk_level: str) -> str:
    """Kept for backward compatibility -- prefer risk_pill_html() for new markup."""
    color = RISK_COLOR.get(risk_level, COLORS["muted"])
    return (
        f'<span class="status-dot" '
        f'style="background:{color}; box-shadow: 0 0 6px {color}99; margin-right:8px;"></span>'
    )


def asset_card_html(asset_id: str, risk_level: str, health_score: float, subtitle: str = "", trend_values: list = None) -> str:
    color = RISK_COLOR.get(risk_level, COLORS["muted"])
    spark = sparkline_svg(trend_values, color) if trend_values else ""
    return f"""
    <div class="panel-card with-accent" style="--accent-color:{color};">
        <div class="eyebrow">Asset</div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
            <div style="font-size:1.15rem; font-weight:700; color:{COLORS['ink']};">{asset_id}</div>
            {risk_pill_html(risk_level)}
        </div>
        <div style="display:flex; justify-content:space-between; align-items:flex-end;">
            <div>
                <div class="mono-value" style="font-size:2.1rem; color:{color};">
                    {health_score:.1f}<span style="font-size:1.1rem; opacity:0.7;">%</span>
                </div>
                <div style="font-size:0.8rem; color:{COLORS['muted']}; margin-top:4px;">
                    health score{(' &middot; ' + subtitle) if subtitle else ''}
                </div>
            </div>
            <div>{spark}</div>
        </div>
    </div>
    """


def section_header(eyebrow: str, title: str):
    st.markdown(
        f"""
        <div class="eyebrow">{eyebrow}</div>
        <h2 style="margin-top:0; margin-bottom:20px;">
            <span class="gradient-heading">{title}</span>
        </h2>
        """,
        unsafe_allow_html=True,
    )