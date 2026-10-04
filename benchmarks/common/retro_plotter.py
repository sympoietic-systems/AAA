"""
Protocol-compliant retro-cybernetic plotting engine for AAA.
Follows .agents/protocols/VISUALS.md:
- Pure matte black void (#000000 / #050505)
- Crisp high-luminance foreground (#FFFFFF / #E4E7EC)
- Monospace technical typography (Consolas / DejaVu Sans Mono)
- Minimalist crosshairs [+] and bracket corner marks
- Strict comparative dual accents:
    Baseline: Amber Orange (#FB923C)
    Candidate: Emerald Green (#4ADE80)
- Data-agnostic plotting primitives:
    - grouped_bar_chart
    - scorecard_bar_chart
    - multi_trajectory_chart
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Palette Constants
BG_VOID = "#050505"
PANEL_VOID = "#0A0B0E"
FG_WHITE = "#FFFFFF"
FG_LIGHT = "#E4E7EC"
TEXT_MUTED = "#88909E"
GRID_STIPPLE = (1.0, 1.0, 1.0, 0.12)
BORDER_LINE = (1.0, 1.0, 1.0, 0.20)

COLOR_BASELINE = "#FB923C"  # Amber Orange
COLOR_CANDIDATE = "#4ADE80"  # Emerald Green
COLOR_CYAN = "#38BDF8"
COLOR_YELLOW = "#FACC15"
COLOR_RED = "#F87171"


def set_retro_cybernetic_theme(font_family: str = "Consolas") -> None:
    """Configures matplotlib rcParams for retro-cybernetic telemetry aesthetics."""
    plt.rcParams.update(
        {
            "figure.facecolor": BG_VOID,
            "axes.facecolor": BG_VOID,
            "savefig.facecolor": BG_VOID,
            "axes.edgecolor": BORDER_LINE,
            "axes.linewidth": 1.0,
            "axes.labelcolor": FG_LIGHT,
            "axes.titlecolor": FG_WHITE,
            "xtick.color": TEXT_MUTED,
            "ytick.color": TEXT_MUTED,
            "text.color": FG_WHITE,
            "font.family": font_family,
            "font.size": 10,
            "grid.color": GRID_STIPPLE,
            "grid.linestyle": ":",
            "grid.linewidth": 0.8,
        }
    )


def add_telemetry_framing(
    fig: plt.Figure,
    ax: plt.Axes,
    title: str | None = None,
    subtitle: str | None = None,
    badge: str | None = None,
) -> None:
    """Adds minimal technical crosshairs [+] and bracket framing."""
    ax.text(
        0.01,
        0.98,
        "[+]",
        transform=ax.transAxes,
        fontsize=9,
        color=TEXT_MUTED,
        verticalalignment="top",
        fontfamily="Consolas",
    )
    if badge:
        ax.text(
            0.99,
            0.98,
            f"// {badge.upper()} //",
            transform=ax.transAxes,
            fontsize=9,
            color=TEXT_MUTED,
            horizontalalignment="right",
            verticalalignment="top",
            fontfamily="Consolas",
        )
    if title:
        fig.text(0.05, 0.96, title.upper(), fontsize=13, fontweight="bold", color=FG_WHITE, fontfamily="Consolas")
    if subtitle:
        fig.text(0.05, 0.925, subtitle, fontsize=9, color=TEXT_MUTED, fontfamily="Consolas")


def plot_grouped_bars(
    categories: Sequence[str],
    series_data: dict[str, Sequence[float]],
    series_colors: dict[str, str],
    title: str,
    ylabel: str,
    output_path: Path,
    subtitle: str | None = None,
    figsize: tuple[int, int] = (10, 5),
    ylim: tuple[float, float] | None = None,
    show_values: bool = True,
    badge: str | None = "TELEMETRY AUDIT",
) -> None:
    """Data-agnostic grouped bar chart generator respecting VISUALS.md."""
    set_retro_cybernetic_theme()
    fig, ax = plt.subplots(figsize=figsize)

    x = np.arange(len(categories))
    num_series = len(series_data)
    width = 0.35 if num_series == 2 else 0.8 / max(1, num_series)

    for i, (name, values) in enumerate(series_data.items()):
        offset = (i - (num_series - 1) / 2) * width
        color = series_colors.get(name, COLOR_CANDIDATE)
        bars = ax.bar(x + offset, values, width, label=name, color=color, alpha=0.92, edgecolor=BG_VOID, linewidth=1)
        if show_values:
            for bar in bars:
                height = bar.get_height()
                ax.annotate(
                    f"{height:.3f}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 4),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color=FG_LIGHT,
                    fontfamily="Consolas",
                )

    ax.set_ylabel(ylabel.upper(), fontfamily="Consolas", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels([c.upper() for c in categories], fontfamily="Consolas", fontsize=9)
    if ylim:
        ax.set_ylim(ylim)
    ax.grid(axis="y", color=GRID_STIPPLE, linestyle=":", linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=True, facecolor=BG_VOID, edgecolor=BORDER_LINE, fontsize=9)

    add_telemetry_framing(fig, ax, title, subtitle, badge=badge)
    plt.tight_layout(rect=(0.02, 0.02, 0.98, 0.91))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_dual_archetype_matrix(
    archetypes: Sequence[str],
    drr_legacy: Sequence[float],
    drr_paskian: Sequence[float],
    cp_legacy: Sequence[float],
    cp_paskian: Sequence[float],
    output_path: Path,
    title: str = "ARCHETYPE PHASE SPACE MATRIX: DIVERGENCE RESOLUTION & COLLAPSE PRESSURE",
    subtitle: str = "Evaluated on nvidia/nemotron-3-super-120b-a12b under 1:1 model parity (N=120 turns)",
) -> None:
    """Generates the canonical 2-panel matrix adhering strictly to visual grammar."""
    set_retro_cybernetic_theme()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    x = np.arange(len(archetypes))
    width = 0.35

    # Panel 1: DRR
    b1_leg = ax1.bar(x - width / 2, drr_legacy, width, label="Legacy Baseline", color=COLOR_BASELINE, alpha=0.9)
    b1_pas = ax1.bar(
        x + width / 2, drr_paskian, width, label="Paskian Controller (ADR-098)", color=COLOR_CANDIDATE, alpha=0.9
    )
    ax1.set_ylabel("DIVERGENCE RESOLUTION RATIO (DRR)", fontfamily="Consolas", fontsize=9)
    ax1.set_xticks(x)
    ax1.set_xticklabels([a.upper().replace("\n", "\n") for a in archetypes], fontfamily="Consolas", fontsize=8)
    ax1.set_ylim(0.0, 1.05)
    ax1.grid(axis="y", color=GRID_STIPPLE, linestyle=":", linewidth=0.8)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.legend(frameon=True, facecolor=BG_VOID, edgecolor=BORDER_LINE, fontsize=8, loc="upper right")
    ax1.text(
        0.02,
        0.97,
        "[+] DRR CONVERGENCE",
        transform=ax1.transAxes,
        fontsize=9,
        color=TEXT_MUTED,
        fontfamily="Consolas",
        va="top",
    )

    for bar in b1_leg:
        ax1.annotate(
            f"{bar.get_height():.3f}",
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=FG_LIGHT,
            fontfamily="Consolas",
        )
    for bar in b1_pas:
        ax1.annotate(
            f"{bar.get_height():.3f}",
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=COLOR_CANDIDATE,
            fontfamily="Consolas",
        )

    # Panel 2: Collapse Pressure
    b2_leg = ax2.bar(x - width / 2, cp_legacy, width, label="Legacy Baseline", color=COLOR_BASELINE, alpha=0.9)
    b2_pas = ax2.bar(
        x + width / 2, cp_paskian, width, label="Paskian Controller (ADR-098)", color=COLOR_CANDIDATE, alpha=0.9
    )
    ax2.set_ylabel("COLLAPSE PRESSURE (CP_t)", fontfamily="Consolas", fontsize=9)
    ax2.set_xticks(x)
    ax2.set_xticklabels([a.upper().replace("\n", "\n") for a in archetypes], fontfamily="Consolas", fontsize=8)
    ax2.set_ylim(0.0, 1.05)
    ax2.grid(axis="y", color=GRID_STIPPLE, linestyle=":", linewidth=0.8)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.legend(frameon=True, facecolor=BG_VOID, edgecolor=BORDER_LINE, fontsize=8, loc="upper right")
    ax2.text(
        0.02,
        0.97,
        "[+] CP DAMPENING",
        transform=ax2.transAxes,
        fontsize=9,
        color=TEXT_MUTED,
        fontfamily="Consolas",
        va="top",
    )

    for bar in b2_leg:
        ax2.annotate(
            f"{bar.get_height():.3f}",
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=FG_LIGHT,
            fontfamily="Consolas",
        )
    for bar in b2_pas:
        ax2.annotate(
            f"{bar.get_height():.3f}",
            (bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7.5,
            color=COLOR_CANDIDATE,
            fontfamily="Consolas",
        )

    fig.text(0.05, 0.96, title.upper(), fontsize=12, fontweight="bold", color=FG_WHITE, fontfamily="Consolas")
    fig.text(0.05, 0.925, subtitle, fontsize=8.5, color=TEXT_MUTED, fontfamily="Consolas")

    plt.tight_layout(rect=(0.02, 0.02, 0.98, 0.91))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_trajectories(
    turns_data: dict[str, dict[str, Sequence[float]]],
    output_path: Path,
    title: str = "TURN-BY-TURN TELEMETRY TRAJECTORIES ACROSS ARCHETYPES",
    subtitle: str = "Tracking dynamic deadlock severing and homeostatic stabilization across 6 dialogue turns",
) -> None:
    """Generates multi-scenario turn trajectories with CRT beam lines."""
    set_retro_cybernetic_theme()
    scenarios = list(turns_data.keys())
    fig_width = max(16.0, 4.0 * len(scenarios))
    fig, axes = plt.subplots(1, len(scenarios), figsize=(fig_width, 4.8), sharey=True)

    turns = np.arange(1, 7)

    for ax, scenario_name in zip(axes, scenarios, strict=False):
        s_data = turns_data[scenario_name]
        # Lines
        if "DRR" in s_data:
            ax.plot(turns, s_data["DRR"], color=COLOR_CANDIDATE, marker="o", linewidth=2.0, label="DRR (Resolution)")
        if "Hpask" in s_data:
            ax.plot(
                turns,
                s_data["Hpask"],
                color=COLOR_CYAN,
                marker="s",
                linestyle="--",
                linewidth=1.8,
                label="Paskian Health (Hpask)",
            )
        if "Boringness" in s_data:
            ax.plot(
                turns,
                s_data["Boringness"],
                color=COLOR_BASELINE,
                marker="^",
                linestyle=":",
                linewidth=1.8,
                label="Boringness / Deficit",
            )

        ax.set_title(scenario_name.upper(), loc="center", fontfamily="Consolas", fontsize=10, pad=10)
        ax.set_xlabel("DIALOGUE TURN (1 TO 6)", fontfamily="Consolas", fontsize=8.5)
        ax.set_xticks(turns)
        ax.set_ylim(-0.02, 1.05)
        ax.grid(color=GRID_STIPPLE, linestyle=":", linewidth=0.8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.text(
            0.03, 0.96, "[+]", transform=ax.transAxes, fontsize=8, color=TEXT_MUTED, fontfamily="Consolas", va="top"
        )

    axes[0].set_ylabel("TELEMETRY RATIO / SCORE", fontfamily="Consolas", fontsize=9)
    axes[-1].legend(frameon=True, facecolor=BG_VOID, edgecolor=BORDER_LINE, fontsize=8, loc="lower right")

    fig.text(0.04, 0.96, title.upper(), fontsize=12, fontweight="bold", color=FG_WHITE, fontfamily="Consolas")
    fig.text(0.04, 0.925, subtitle, fontsize=8.5, color=TEXT_MUTED, fontfamily="Consolas")

    plt.tight_layout(rect=(0.02, 0.02, 0.98, 0.91))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_homeostatic_sampling_vector(
    turns_data: dict[str, Sequence[float]],
    output_path: Path,
    title: str = "HOMEOSTATIC SAMPLING VECTOR DYNAMICS ACROSS TURNS",
    subtitle: str = "Allostatic parameter modulation & regime shifts under conversational stress (NVIDIA Nemotron-3 Super 120B)",
) -> None:
    """Renders a 3-tier oscilloscope tracking sampling temperature, penalties, and collapse pressure."""
    set_retro_cybernetic_theme()
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 9), sharex=True)

    turns = np.arange(1, len(turns_data["temperature"]) + 1)

    # Tier 1: Temperature & Baseline
    ax1.plot(
        turns,
        turns_data["temperature"],
        color=COLOR_CYAN,
        marker="o",
        linewidth=2.0,
        label="Modulated Temperature (T)",
    )
    if "base_temperature" in turns_data:
        ax1.axhline(
            turns_data["base_temperature"][0],
            color=TEXT_MUTED,
            linestyle="--",
            linewidth=1.2,
            label="Nominal Base Temperature (0.70)",
        )
    ax1.set_ylabel("TEMPERATURE (T)", fontfamily="Consolas", fontsize=9)
    ax1.set_title("TIER 1: SAMPLING ENTROPY & TEMPERATURE MODULATION", loc="left", fontfamily="Consolas", fontsize=9.5)
    ax1.grid(color=GRID_STIPPLE, linestyle=":", linewidth=0.8)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.legend(frameon=True, facecolor=BG_VOID, edgecolor=BORDER_LINE, fontsize=8, loc="upper right")

    # Tier 2: Penalties
    if "presence_penalty" in turns_data:
        ax2.plot(
            turns,
            turns_data["presence_penalty"],
            color=COLOR_CANDIDATE,
            marker="s",
            linewidth=2.0,
            label="Presence Penalty (P_pres)",
        )
    if "frequency_penalty" in turns_data:
        ax2.plot(
            turns,
            turns_data["frequency_penalty"],
            color=COLOR_YELLOW,
            marker="^",
            linestyle="--",
            linewidth=1.8,
            label="Frequency Penalty (P_freq)",
        )
    ax2.set_ylabel("PENALTY MAGNITUDE", fontfamily="Consolas", fontsize=9)
    ax2.set_title(
        "TIER 2: DIRECTIONAL PENALTY INJECTION (ATTRACTOR BASIN SHATTERING)",
        loc="left",
        fontfamily="Consolas",
        fontsize=9.5,
    )
    ax2.grid(color=GRID_STIPPLE, linestyle=":", linewidth=0.8)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.legend(frameon=True, facecolor=BG_VOID, edgecolor=BORDER_LINE, fontsize=8, loc="upper right")

    # Tier 3: Collapse Pressure & Deficit
    if "collapse_pressure" in turns_data:
        ax3.plot(
            turns,
            turns_data["collapse_pressure"],
            color=COLOR_BASELINE,
            marker="D",
            linewidth=2.0,
            label="Collapse Pressure (CP_t)",
        )
    if "deficit" in turns_data:
        ax3.plot(
            turns,
            turns_data["deficit"],
            color=COLOR_RED,
            marker="x",
            linestyle=":",
            linewidth=1.8,
            label="Homeostatic Deficit (D_t)",
        )
    ax3.axhline(0.65, color=COLOR_RED, linestyle="--", linewidth=1.0, alpha=0.7, label="Disruption Tripwire (0.65)")
    ax3.set_ylabel("PRESSURE & DEFICIT", fontfamily="Consolas", fontsize=9)
    ax3.set_xlabel("DIALOGUE INTERACTION TURN (t)", fontfamily="Consolas", fontsize=9.5)
    ax3.set_title(
        "TIER 3: SYSTEMIC DEFICIT VS. MINKOWSKI COLLAPSE PRESSURE", loc="left", fontfamily="Consolas", fontsize=9.5
    )
    ax3.set_xticks(turns)
    ax3.set_ylim(-0.05, 1.05)
    ax3.grid(color=GRID_STIPPLE, linestyle=":", linewidth=0.8)
    ax3.spines["top"].set_visible(False)
    ax3.spines["right"].set_visible(False)
    ax3.legend(frameon=True, facecolor=BG_VOID, edgecolor=BORDER_LINE, fontsize=8, loc="upper right")

    fig.text(0.04, 0.97, title.upper(), fontsize=12, fontweight="bold", color=FG_WHITE, fontfamily="Consolas")
    fig.text(0.04, 0.94, subtitle, fontsize=8.5, color=TEXT_MUTED, fontfamily="Consolas")

    plt.tight_layout(rect=(0.02, 0.02, 0.98, 0.93))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
