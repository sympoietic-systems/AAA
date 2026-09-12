"""
Shared visualization primitives, theme tokens, and headless Edge capture engine.
"""

import os
from pathlib import Path
import shutil
import subprocess
from typing import List, Optional
import numpy as np

# Core Cyberpunk Theme Palette
BG_COLOR = "#060709"
PANEL_BG = "#0C0E14"
TEXT_COLOR = "#E4E7EC"
SUBTEXT_COLOR = "#88909E"
GRID_COLOR = "rgba(255, 255, 255, 0.07)"

COLOR_GREEN = "#10B981"       # Terminal Emerald
COLOR_GREEN_ALT = "#34D399"   # Mint
COLOR_ORANGE = "#FF6B00"      # Hot Orange
COLOR_ORANGE_ALT = "#FB923C"  # Warm Amber
COLOR_ICE_CYAN = "#38BDF8"    # Ice Cyan
COLOR_SLATE = "#64748B"       # Neutral Slate
COLOR_VIOLET = "#A78BFA"      # Soft Violet

# Matplotlib-safe color tuples
MPL_GRID_COLOR = (1.0, 1.0, 1.0, 0.15)
MPL_BORDER_COLOR = (1.0, 1.0, 1.0, 0.15)


def find_edge_path() -> str:
    """Locates Microsoft Edge or Chrome binary for high-resolution headless snapshots."""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        shutil.which("msedge"),
        shutil.which("chrome"),
        shutil.which("google-chrome"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return ""


def capture_html_screenshot(
    html_file: Path,
    png_file: Path,
    width: int = 1720,
    height: int = 3380,
) -> bool:
    """Invokes headless browser to capture a pixel-perfect PNG snapshot of an HTML dashboard."""
    edge_bin = find_edge_path()
    if not edge_bin:
        return False

    cmd = [
        edge_bin,
        "--headless",
        "--disable-gpu",
        "--hide-scrollbars",
        f"--window-size={width},{height}",
        f"--screenshot={png_file}",
        f"file:///{str(html_file).replace(os.sep, '/')}",
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=30)
        return res.returncode == 0 and png_file.exists()
    except Exception:
        return False


def to_pts(values: List[float], left: float = 65, right: float = 745,
           top: float = 22, bottom: float = 188, y_max: float = 1.0) -> str:
    """Maps a 1D sequence of float values into SVG polyline coordinates."""
    if not values:
        return ""
    n = len(values)
    pts = []
    for i, v in enumerate(values):
        x = left + i * (right - left) / max(1, n - 1)
        clamped = max(0.0, min(y_max, float(v)))
        y = bottom - (clamped / y_max) * (bottom - top)
        pts.append(f"{x:.1f},{y:.1f}")
    return " ".join(pts)


def to_circ(values: List[float], color: str, r: float = 3.5, hollow: bool = False,
            left: float = 65, right: float = 745, top: float = 22, bottom: float = 188,
            y_max: float = 1.0) -> str:
    """Generates SVG circle markers for each turn along a trace."""
    if not values:
        return ""
    n = len(values)
    circs = []
    for i, v in enumerate(values):
        x = left + i * (right - left) / max(1, n - 1)
        clamped = max(0.0, min(y_max, float(v)))
        y = bottom - (clamped / y_max) * (bottom - top)
        if hollow:
            circs.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{PANEL_BG}" stroke="{color}" stroke-width="2.0" />')
        else:
            circs.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{color}" />')
    return "\n".join(circs)


def make_grid(left: float = 65, right: float = 745, top: float = 22, bottom: float = 188,
              y_max: float = 1.0, y_ticks: int = 4, num_turns: int = 10) -> str:
    """Generates SVG Cartesian grid lines and axis tick labels."""
    lines = []
    for i in range(y_ticks + 1):
        val = (y_ticks - i) * (y_max / y_ticks)
        y = top + i * (bottom - top) / y_ticks
        lines.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="{GRID_COLOR}" stroke-width="1" />')
        lines.append(f'<text x="{left - 10}" y="{y + 3.5:.1f}" fill="#717684" font-size="10" font-family="JetBrains Mono, monospace" text-anchor="end">{val:.2f}</text>')

    x_tick_step = max(1, num_turns // 10)
    for i in range(num_turns):
        if i % x_tick_step != 0 and i != num_turns - 1:
            continue
        x = left + i * (right - left) / max(1, num_turns - 1)
        lines.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{bottom}" stroke="rgba(255,255,255,0.05)" stroke-width="1" />')
        lines.append(f'<text x="{x:.1f}" y="{bottom + 17}" fill="#717684" font-size="10" font-family="JetBrains Mono, monospace" text-anchor="middle">T{i+1}</text>')

    return "\n".join(lines)
