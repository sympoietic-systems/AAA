import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Load benchmark data
data_file = Path('backend/benchmarks/output/benchmark_results.json')
with open(data_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Two-letter abbreviations mapping for the 16 cybernetic dimensions
ABBREVS = ['HO', 'AM', 'CY', 'BI', 'DC', 'RH', 'BP', 'RD', 'VF', 'NC', 'TL', 'AD', 'SY', 'NO', 'CO', 'SM']
TITLES = [d['title'] for d in data['dimensions']]
DIM_LABELS = [f'{abbr}\n(s{idx+1:02d})' for idx, abbr in enumerate(ABBREVS)]

num_vars = len(ABBREVS)
angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
angles += angles[:1]

corpus = data['corpus_results']
selected_items = [
    corpus[0],  # Autopoietic Closure
    corpus[3],  # VSM Recursion Memory
    corpus[5],  # Paskian Conversational Alignment
]

# Set AAA dark cybernetic theme styling matching terminal / web app
plt.style.use('dark_background')
fig, axes = plt.subplots(1, 3, figsize=(22, 7.5), subplot_kw=dict(polar=True), facecolor='#06090e')
plt.subplots_adjust(wspace=0.38, top=0.80, bottom=0.18)

jev_color = '#10b981'  # Cybernetic Emerald Green
llm_color = '#f59e0b'  # Radiant Amber / Orange

for idx, (ax, item) in enumerate(zip(axes, selected_items)):
    ax.set_facecolor('#0a1017')
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    
    # Grid styling
    ax.grid(color='#1e293b', linestyle='--', linewidth=0.8, alpha=0.9)
    ax.spines['polar'].set_color('#334155')
    ax.spines['polar'].set_linewidth(1.2)
    
    # Title
    ax.set_title(f'[{item["category"].upper()}]\n{item["title"]}', size=13, weight='bold', color='#f8fafc', pad=24)
    
    # Ticks & labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(DIM_LABELS, size=9, weight='bold', color='#94a3b8')
    
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.25, 0.50, 0.75, 1.0])
    ax.set_yticklabels(['.25', '.50', '.75', '1.0'], size=7.5, color='#475569')

    # LLM profile
    llm_vals = item['scores']['llm'] + item['scores']['llm'][:1]
    ax.plot(angles, llm_vals, color=llm_color, linewidth=2.0, linestyle='-', marker='o', markersize=4, label='LLM (Gemini 2.5 Flash)', alpha=0.95)
    ax.fill(angles, llm_vals, color=llm_color, alpha=0.12)

    # Jev profile
    jev_vals = item['scores']['jev_power'] + item['scores']['jev_power'][:1]
    ax.plot(angles, jev_vals, color=jev_color, linewidth=2.5, linestyle='-', marker='s', markersize=4.5, label='Jev System One (RLCD)', alpha=0.95)
    ax.fill(angles, jev_vals, color=jev_color, alpha=0.22)

    # Legend for first chart
    if idx == 0:
        leg = ax.legend(loc='upper right', bbox_to_anchor=(0.02, 1.28), fontsize=10.5, frameon=True, facecolor='#0f172a', edgecolor='#334155')
        for text in leg.get_texts():
            text.set_color('#e2e8f0')

# Add bottom glossary explaining abbreviations
glossary_row1 = ' • '.join([f'{abbr}: {TITLES[i]}' for i, abbr in enumerate(ABBREVS[:8])])
glossary_row2 = ' • '.join([f'{abbr}: {TITLES[i]}' for i, abbr in enumerate(ABBREVS[8:], 8)])
fig.text(0.5, 0.08, glossary_row1, ha='center', color='#64748b', fontsize=8.5, family='monospace')
fig.text(0.5, 0.05, glossary_row2, ha='center', color='#64748b', fontsize=8.5, family='monospace')

out_path = Path('docs/reports/radar_jev_vs_llm_comparison.png')
plt.savefig(out_path, dpi=250, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.close()
print(f'Successfully generated: {out_path}')
