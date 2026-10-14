#!/usr/bin/env python3
"""Schematic of the outside-debt-share layered family (m = 3). Writes paper/figure_layered.pdf/.png."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

OUT = Path(__file__).resolve().parent.parent / 'paper'
m = 3
fig, ax = plt.subplots(figsize=(9, 4.2)); ax.set_aspect('equal')
ax.set_xlim(-0.9, m + 1.4)
ax.set_ylim(-1.6, 1.9)
ax.axis('off')
xs = list(range(m + 1))
ys = [0.6, -0.6]
labels = {}
for j in xs:
    for k, y in enumerate(ys):
        idx = 2 * j + k
        ax.add_patch(plt.Circle((j, y), 0.22, fc='white', ec='black', lw=1.2, zorder=3))
        ax.text(j, y, str(idx), ha='center', va='center', fontsize=10, zorder=4)
# arrows between layers
for j in range(1, m + 1):
    t = f't_{j}'
    for k in range(2):
        for l in range(2):
            lab = t if k == l else f'1-{t}'
            style = '-' if k == l else '--'
            a = FancyArrowPatch((j - 1 + 0.22, ys[k]), (j - 0.22, ys[l]), arrowstyle='-|>', mutation_scale=10,
                                lw=1.0, color='black', linestyle=style, zorder=2, shrinkA=0, shrinkB=0)
            ax.add_patch(a)
    ax.text(j - 0.5, 1.05, f'$T(t_{j})$', ha='center', fontsize=10)
# layer captions
cap = ['sources\n$b_0$ outside\nassets 0, $1+b_0$',
       'intermediate\nβ outside\nassets β, β', 'intermediate\nβ outside\nassets β, β', 'final\n1 outside\nassets 0, 1']
for j in xs:
    ax.text(j, -1.05, cap[j], ha='center', va='top', fontsize=8.5)
ax.text(-0.75, 0.6, 'shock\n(1+b₀)', ha='center', va='center', fontsize=8.5, color='firebrick')
ax.annotate('', xy=(-0.25, 0.6), xytext=(-0.55, 0.6), arrowprops=dict(arrowstyle='-|>', color='firebrick'))
ax.text(m + 0.75, 0.6, 'bears deficit', ha='center', va='center', fontsize=8.5)
ax.text(m + 0.75, -0.6, 'slack 1', ha='center', va='center', fontsize=8.5)
ax.text((m) / 2, 1.6, 'Solid arrows carry $t_j$, dashed arrows $1-t_j$; each interlayer block has unit row and column sums', ha='center', fontsize=9)
fig.savefig(OUT / 'figure_layered.pdf', bbox_inches='tight')
fig.savefig(OUT / 'figure_layered.png', dpi=160, bbox_inches='tight')
print('written')
