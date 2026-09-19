"""Visualization suite for 16D Structural Scoring Benchmark results.

Generates:
1. radar_comparison.png: Radar/spider chart comparing Lexicon, Topology, LLM, and Jev profiles.
2. scorer_correlation.png: Cross-scorer cosine similarity and Pearson correlation heatmap.
3. power_vs_confidence.png: Jev epistemic certainty (Confidence) vs Intensity (Power) scatter.
4. latency_benchmark.png: Runtime latency comparison (ms) across scorers.
"""

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUTPUT_DIR = Path(__file__).resolve().parent / "output"
DATA_FILE = OUTPUT_DIR / "benchmark_results.json"


def load_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Data file not found: {DATA_FILE}")
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_radar_comparison(data):
    """Plot multi-scorer radar/spider chart for representative corpus items."""
    dims = [d["title"] for d in data["dimensions"]]
    num_vars = len(dims)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # complete loop

    corpus = data["corpus_results"]
    # Pick 3 representative items (1 belief, 1 memory, 1 message)
    selected_items = [
        corpus[0],  # Autopoietic Closure
        corpus[3],  # VSM Recursion Memory
        corpus[5],  # Paskian Conversational Alignment
    ]

    fig, axes = plt.subplots(1, 3, figsize=(21, 7), subplot_kw=dict(polar=True))
    plt.subplots_adjust(wspace=0.35)

    colors = {
        "lexicon": "#3498db",       # Blue
        "topology": "#95a5a6",      # Gray
        "llm": "#e67e22",           # Orange
        "jev_power": "#2ecc71",     # Green
    }

    for idx, (ax, item) in enumerate(zip(axes, selected_items)):
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_title(f"{item['category']}: {item['title']}", size=12, weight="bold", y=1.12)

        # Labels
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels([d[:12] for d in dims], size=8)
        ax.set_ylim(0, 1.0)
        ax.set_yticks([0.25, 0.50, 0.75, 1.0])
        ax.set_yticklabels(["0.25", "0.50", "0.75", "1.0"], size=7, color="#777777")

        # Plot each scorer
        for key, color in colors.items():
            vals = item["scores"].get(key, [])
            if not vals:
                continue
            vals_loop = vals + vals[:1]
            label = "Jev Power" if key == "jev_power" else key.capitalize()
            linewidth = 2.5 if key == "jev_power" else 1.5
            alpha = 0.25 if key == "jev_power" else 0.10
            ax.plot(angles, vals_loop, color=color, linewidth=linewidth, label=label)
            ax.fill(angles, vals_loop, color=color, alpha=alpha)

        if idx == 0:
            ax.legend(loc="upper right", bbox_to_anchor=(0.1, 1.15), fontsize=9)

    out_path = OUTPUT_DIR / "radar_comparison.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")


def plot_power_vs_confidence(data):
    """Plot Jev epistemic distribution: Confidence vs Power across all dimensions."""
    corpus = data["corpus_results"]
    dims = [d["title"] for d in data["dimensions"]]

    fig, ax = plt.subplots(figsize=(10, 6))

    all_powers = []
    all_confs = []
    labels = []

    for item in corpus:
        powers = item["scores"]["jev_power"]
        confs = item["scores"]["jev_confidence"]
        for p, c, dim_title in zip(powers, confs, dims):
            all_powers.append(p)
            all_confs.append(c)
            labels.append(dim_title)

    scatter = ax.scatter(
        all_powers,
        all_confs,
        c=all_confs,
        cmap="viridis",
        alpha=0.7,
        s=80,
        edgecolors="none",
    )
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Statistical Confidence", fontsize=10)

    # Highlight active high-confidence dimensions
    for p, c, lbl in zip(all_powers, all_confs, labels):
        if p > 0.60 and c > 0.75:
            ax.annotate(
                lbl,
                (p, c),
                fontsize=8,
                xytext=(5, 2),
                textcoords="offset points",
                weight="bold",
                color="#2c3e50",
            )

    ax.set_title("Jev System One: Cybernetic Power vs. Epistemic Confidence", fontsize=14, weight="bold")
    ax.set_xlabel("Dimension Power (Normalized Presence Score)", fontsize=11)
    ax.set_ylabel("Epistemic Confidence (Model Certainty)", fontsize=11)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(0.0, 1.05)
    ax.grid(True, linestyle="--", alpha=0.4)

    # Reference quadrants
    ax.axvline(0.5, color="#e74c3c", linestyle=":", alpha=0.5)
    ax.axhline(0.7, color="#e74c3c", linestyle=":", alpha=0.5)
    ax.text(0.75, 0.95, "Salient & Confident", color="#27ae60", fontsize=10, weight="bold")
    ax.text(0.75, 0.35, "Salient but Ambiguous", color="#d35400", fontsize=10, weight="bold")
    ax.text(0.10, 0.95, "Confident Absence", color="#2980b9", fontsize=10, weight="bold")

    out_path = OUTPUT_DIR / "power_vs_confidence.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")


def plot_latency_benchmark(data):
    """Plot runtime latency comparison (ms) across scorers."""
    corpus = data["corpus_results"]
    scorers = ["lexicon", "topology", "jev", "llm"]
    labels = ["Lexicon (Regex)", "Topology (Heuristic)", "Jev (System One)", "LLM (Generative)"]
    colors = ["#3498db", "#95a5a6", "#2ecc71", "#e67e22"]

    avg_latencies = []
    for s in scorers:
        times = [item["timings_ms"].get(s, 0.0) for item in corpus]
        avg_latencies.append(np.mean(times))

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(labels, avg_latencies, color=colors, width=0.55)

    for bar, val in zip(bars, avg_latencies):
        yval = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            yval + max(avg_latencies) * 0.02,
            f"{val:.1f} ms",
            ha="center",
            va="bottom",
            fontsize=10,
            weight="bold",
        )

    ax.set_title("16D Structural Scoring Latency Comparison", fontsize=13, weight="bold")
    ax.set_ylabel("Execution Time (milliseconds)", fontsize=11)
    ax.set_ylim(0, max(avg_latencies) * 1.18)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    out_path = OUTPUT_DIR / "latency_benchmark.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")


def plot_dimension_heatmap(data):
    """Plot 16D heatmap comparing Jev Power vs Lexicon for all corpus items."""
    corpus = data["corpus_results"]
    dims = [d["title"] for d in data["dimensions"]]
    titles = [f"{item['category'][:3]}: {item['title'][:18]}" for item in corpus]

    jev_matrix = np.array([item["scores"]["jev_power"] for item in corpus])
    lex_matrix = np.array([item["scores"]["lexicon"] for item in corpus])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 6), sharey=True)

    im1 = ax1.imshow(jev_matrix, cmap="YlGnBu", aspect="auto", vmin=0, vmax=1)
    ax1.set_title("Jev System One Power (Semantic Rubric)", fontsize=12, weight="bold")
    ax1.set_xticks(range(len(dims)))
    ax1.set_xticklabels([d[:10] for d in dims], rotation=60, ha="right", fontsize=8)
    ax1.set_yticks(range(len(titles)))
    ax1.set_yticklabels(titles, fontsize=9)

    im2 = ax2.imshow(lex_matrix, cmap="YlGnBu", aspect="auto", vmin=0, vmax=1)
    ax2.set_title("Lexicon Scorer (Stem Density Saturation)", fontsize=12, weight="bold")
    ax2.set_xticks(range(len(dims)))
    ax2.set_xticklabels([d[:10] for d in dims], rotation=60, ha="right", fontsize=8)

    fig.colorbar(im1, ax=[ax1, ax2], orientation="horizontal", fraction=0.05, pad=0.25, label="16D Value")

    out_path = OUTPUT_DIR / "dimension_heatmap.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_path}")


def main():
    data = load_data()
    plot_radar_comparison(data)
    plot_power_vs_confidence(data)
    plot_latency_benchmark(data)
    plot_dimension_heatmap(data)
    print("All plots generated successfully.")


if __name__ == "__main__":
    main()
