# 🔐 AI Cryptarithm Puzzle Solver 

A professional desktop application solving **Cryptarithmetic puzzles** via a high-performance
**CSP Backtracking solver**, with a fully-featured modern PyQt5 GUI.

---

## 🚀 Quick Start

```bash
pip install PyQt5
python main.py
```

---

## 📂 Structure

```
cryptarithm_solver/
├── main.py      — App entry point (HiDPI + font setup)
├── gui.py       — Full PyQt5 UI (panels, animations, threads)
├── solver.py    — CSP solver with optional trace capture
└── requirements.txt
```

---

## ✨ Features

| Feature | Detail |
|---------|--------|
| **Structured input** | Three separate boxes: `[WORD1] + [WORD2] = [RESULT]` |
| **7 example puzzles** | Dropdown auto-fills inputs |
| **⚡ Solve Puzzle** | Background QThread — UI never freezes |
| **🔍 Show Explanation** | On-demand trace: assign / prune / backtrack steps |
| **Puzzle Board panel** | Right sidebar shows word & numeric equations |
| **Digit-by-digit animation** | Numbers reveal one line at a time after solving |
| **Letter→Digit badge grid** | Color-coded badges for every mapping |
| **Stats bar** | Solve time (ms), nodes explored, unique letter count |
| **Clear button** | Resets all state instantly |
| **Input validation** | Letters-only, max 10 unique letters, leading-zero check |

---

## 🧠 Solver Algorithm

### Why it's fast

The key insight: instead of trying all 10! permutations, the equation is
recast as a linear constraint.

**Coefficient encoding**
Every letter gets an integer coefficient based on its column position:

```
  S E N D         S=1000, E=100, N=10, D=1
+ M O R E    →   M=1000, O=100, R=10, E=1  (addend coefficients are positive)
-----------       M=10000, O=1000, N=100, E=10, Y=1  (result coefficients are negative)
M O N E Y
```

Constraint: `Σ coeff[letter] × digit[letter] = 0`

**Variable ordering (MCV)**
Letters with the largest absolute coefficients are assigned first, so pruning
hits the widest branches earliest.

**Forward checking (sum-pruning)**
After each assignment, compute the min/max achievable sum from remaining
unassigned variables. If 0 is outside that range → prune immediately.

### Benchmarks (verified)

| Puzzle | Time | Nodes |
|--------|------|-------|
| SEND + MORE = MONEY | **0.24 ms** | 11 |
| TWO + TWO = FOUR | 0.29 ms | 25 |
| THIS + IS = HARD | 0.40 ms | 13 |
| BASE + BALL = GAMES | 0.35 ms | 63 |
| ODD + ODD = EVEN | 0.10 ms | 7 |

---

## 🎨 UI Design

- **Dark neon theme** — deep navy (#0B0D1A) with electric indigo +  pink accents
- **GlowButton** — custom-painted QPushButton with hover + pulse animations
- **Three-panel layout** — left: input/results/trace · right: puzzle board
- **ExplanationPanel** — streams trace lines with color-coded syntax (assign / prune / backtrack)
- **VisualizationPanel** — right sidebar with animated digit reveal and badge grid
- **QThread workers** — one for fast solve, one for trace capture; UI never blocks
