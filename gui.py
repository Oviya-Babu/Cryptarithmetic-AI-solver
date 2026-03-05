"""
gui.py — Enhanced PyQt5 GUI for the Cryptarithm Puzzle Solver
Features: side visualization panel, explanation mode, digit animations,
          themed dark UI with neon accents, modular layout.
"""

import sys
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy, QScrollArea, QTextEdit, QTabWidget, QApplication,
    QGridLayout, QSpacerItem
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve,
    QTimer, QRect, pyqtProperty, QSequentialAnimationGroup,
    QParallelAnimationGroup, QPointF
)
from PyQt5.QtGui import (
    QFont, QColor, QLinearGradient, QPainter, QBrush, QPen,
    QPainterPath, QFontMetrics, QTextCursor, QTextCharFormat
)

from solver import solve_cryptarithm, format_solution

# ──────────────────────────────────────────────────────────────
#  THEME
# ──────────────────────────────────────────────────────────────
C = {
    "bg":        "#0B0D1A",
    "bg2":       "#10132A",
    "card":      "#161A30",
    "input":     "#1C2040",
    "border":    "#252A50",
    "glow":      "#4455FF",
    "a1":        "#5C6EFF",   # electric indigo
    "a2":        "#FF3FC0",   # hot pink
    "a3":        "#00F0C0",   # cyan-mint
    "a4":        "#FFB020",   # amber
    "a5":        "#A855F7",   # violet
    "ok":        "#00E890",
    "err":       "#FF3355",
    "warn":      "#FFB020",
    "txt":       "#EEF0FF",
    "txt2":      "#7A88C0",
    "txt3":      "#3A4070",
}

FONTS = {
    "mono":   "Courier New",
    "ui":     "Segoe UI",
    "title":  "Segoe UI",
}

EXAMPLE_PUZZLES = [
    ("SEND",  "MORE",  "MONEY"),
    ("TWO",   "TWO",   "FOUR"),
    ("BASE",  "BALL",  "GAMES"),
    ("CROSS", "ROADS", "DANGER"),
    ("THIS",  "IS",    "HARD"),
    ("EAT",   "THAT",  "APPLE"),
    ("ODD",   "ODD",   "EVEN"),
]

# ──────────────────────────────────────────────────────────────
#  WORKER THREADS
# ──────────────────────────────────────────────────────────────
class SolverWorker(QThread):
    finished = pyqtSignal(object, float, int, object, list)

    def __init__(self, w1, w2, res, trace=False):
        super().__init__()
        self.w1, self.w2, self.res = w1, w2, res
        self.trace = trace

    def run(self):
        result = solve_cryptarithm(self.w1, self.w2, self.res, self.trace)
        self.finished.emit(*result)


# ──────────────────────────────────────────────────────────────
#  CUSTOM WIDGETS
# ──────────────────────────────────────────────────────────────
class GlowButton(QPushButton):
    """Gradient button with animated glow and pulse during solving."""
    def __init__(self, text, color_a=None, color_b=None, parent=None):
        super().__init__(text, parent)
        self._ca = QColor(color_a or C["a1"])
        self._cb = QColor(color_b or C["a2"])
        self._glow = 0
        self._pulse_up = True
        self._solving = False
        self.setMinimumHeight(52)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)

        self._hover_anim = QPropertyAnimation(self, b"glow_val")
        self._hover_anim.setDuration(180)
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._tick_pulse)

    # pyqtProperty
    def _get_glow(self): return self._glow
    def _set_glow(self, v):
        self._glow = v; self.update()
    glow_val = pyqtProperty(int, _get_glow, _set_glow)

    def start_pulse(self):
        self._solving = True
        self._pulse_timer.start(25)

    def stop_pulse(self):
        self._solving = False
        self._pulse_timer.stop()
        self._glow = 0; self.update()

    def _tick_pulse(self):
        step = 10
        self._glow += step if self._pulse_up else -step
        if self._glow >= 220: self._pulse_up = False
        elif self._glow <= 0: self._pulse_up = True
        self.update()

    def enterEvent(self, e):
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._glow)
        self._hover_anim.setEndValue(160)
        self._hover_anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        if not self._solving:
            self._hover_anim.stop()
            self._hover_anim.setStartValue(self._glow)
            self._hover_anim.setEndValue(0)
            self._hover_anim.start()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect()
        radius = 13

        # Outer glow
        if self._glow > 0:
            gc = QColor(self._ca)
            gc.setAlpha(self._glow // 4)
            for i in range(10, 0, -2):
                p.setPen(Qt.NoPen)
                p.setBrush(gc)
                p.drawRoundedRect(r.adjusted(-i, -i, i, i), radius + i, radius + i)

        # Gradient body
        g = QLinearGradient(0, 0, r.width(), r.height())
        g.setColorAt(0.0, self._ca)
        g.setColorAt(1.0, self._cb)
        p.setPen(Qt.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(r, radius, radius)

        # Label
        f = QFont(FONTS["ui"], 11, QFont.Bold)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 0.8)
        p.setFont(f)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(r, Qt.AlignCenter, self.text())
        p.end()


class CryptoInput(QLineEdit):
    def __init__(self, placeholder="", min_w=140, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumHeight(50)
        self.setMinimumWidth(min_w)
        self.setFont(QFont(FONTS["mono"], 18, QFont.Bold))
        self.setStyleSheet(f"""
            QLineEdit {{
                background: {C['input']};
                color: {C['txt']};
                border: 2px solid {C['border']};
                border-radius: 12px;
                padding: 4px 10px;
                letter-spacing: 3px;
            }}
            QLineEdit:focus {{
                border: 2px solid {C['a1']};
                background: #20254A;
            }}
        """)
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(18)
        sh.setColor(QColor(80, 100, 255, 50))
        sh.setOffset(0, 3)
        self.setGraphicsEffect(sh)


class OpLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedWidth(34)
        self.setFont(QFont(FONTS["ui"], 22, QFont.Bold))
        self.setStyleSheet(f"color: {C['a2']}; background: transparent;")


class SectionTitle(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self.setFont(QFont(FONTS["ui"], 9, QFont.Bold))
        self.setStyleSheet(f"color: {C['txt3']}; letter-spacing: 3px; background: transparent;")


def card_frame(radius=18, border_color=None):
    f = QFrame()
    bc = border_color or C["border"]
    f.setStyleSheet(f"""
        QFrame {{
            background: {C['card']};
            border: 1px solid {bc};
            border-radius: {radius}px;
        }}
    """)
    sh = QGraphicsDropShadowEffect()
    sh.setBlurRadius(35)
    sh.setColor(QColor(0, 0, 0, 110))
    sh.setOffset(0, 6)
    f.setGraphicsEffect(sh)
    return f


# ──────────────────────────────────────────────────────────────
#  VISUALIZATION PANEL
# ──────────────────────────────────────────────────────────────
class VisualizationPanel(QFrame):
    """
    Right-side panel showing:
      - Word equation (SEND + MORE = MONEY)
      - After solve: animated digit reveal
      - Letter→digit badge grid
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['card']};
                border: 1px solid {C['border']};
                border-radius: 18px;
            }}
        """)
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(40)
        sh.setColor(QColor(0, 0, 0, 130))
        sh.setOffset(0, 8)
        self.setGraphicsEffect(sh)
        self.setMinimumWidth(280)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(22, 22, 22, 22)
        self._layout.setSpacing(16)

        # Panel title
        title = QLabel("PUZZLE BOARD")
        title.setFont(QFont(FONTS["ui"], 9, QFont.Bold))
        title.setStyleSheet(f"color: {C['txt3']}; letter-spacing: 3px; background: transparent;")
        self._layout.addWidget(title)

        # Equation display (word form)
        self.word_eq_frame = QFrame()
        self.word_eq_frame.setStyleSheet(f"""
            QFrame {{
                background: {C['input']};
                border: 1px solid {C['border']};
                border-radius: 12px;
            }}
        """)
        wef_layout = QVBoxLayout(self.word_eq_frame)
        wef_layout.setContentsMargins(14, 14, 14, 14)
        wef_layout.setSpacing(4)

        self.word_line1 = self._mono_label("", C["txt2"], 15)
        self.word_line2 = self._mono_label("", C["a2"], 15)
        self.word_sep   = self._mono_label("", C["txt3"], 11)
        self.word_line3 = self._mono_label("", C["txt2"], 15)

        for w in [self.word_line1, self.word_line2, self.word_sep, self.word_line3]:
            wef_layout.addWidget(w)
        self._layout.addWidget(self.word_eq_frame)

        # Numeric result (shown after solve)
        self.num_frame = QFrame()
        self.num_frame.setStyleSheet(f"""
            QFrame {{
                background: {C['input']};
                border: 1px solid {C['border']};
                border-radius: 12px;
            }}
        """)
        nf_layout = QVBoxLayout(self.num_frame)
        nf_layout.setContentsMargins(14, 14, 14, 14)
        nf_layout.setSpacing(4)

        num_title = QLabel("NUMERIC FORM")
        num_title.setFont(QFont(FONTS["ui"], 8, QFont.Bold))
        num_title.setStyleSheet(f"color: {C['txt3']}; letter-spacing: 2px; background: transparent;")
        num_title.setAlignment(Qt.AlignCenter)
        nf_layout.addWidget(num_title)

        self.num_line1 = self._mono_label("—", C["a3"], 17)
        self.num_line2 = self._mono_label("", C["a2"], 17)
        self.num_sep   = self._mono_label("", C["txt3"], 11)
        self.num_line3 = self._mono_label("—", C["a4"], 17)

        for w in [self.num_line1, self.num_line2, self.num_sep, self.num_line3]:
            nf_layout.addWidget(w)
        self._layout.addWidget(self.num_frame)

        # Badge grid for mapping
        self.badge_title = QLabel("LETTER → DIGIT MAP")
        self.badge_title.setFont(QFont(FONTS["ui"], 8, QFont.Bold))
        self.badge_title.setStyleSheet(f"color: {C['txt3']}; letter-spacing: 2px; background: transparent;")
        self._layout.addWidget(self.badge_title)

        self.badge_grid_frame = QFrame()
        self.badge_grid_frame.setStyleSheet("background: transparent; border: none;")
        self.badge_grid = QGridLayout(self.badge_grid_frame)
        self.badge_grid.setSpacing(6)
        self._layout.addWidget(self.badge_grid_frame)
        self._layout.addStretch()

        # Animation state
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick_digit_reveal)
        self._anim_digits = []
        self._anim_idx = 0
        self._anim_targets = []  # list of (label, full_text)

    def _mono_label(self, text, color, size):
        lbl = QLabel(text)
        lbl.setFont(QFont(FONTS["mono"], size, QFont.Bold))
        lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        lbl.setAlignment(Qt.AlignRight)
        return lbl

    def set_words(self, w1, w2, result):
        """Populate word-form equation."""
        max_len = max(len(w1), len(w2), len(result)) + 2
        self.word_line1.setText(w1.rjust(max_len))
        self.word_line2.setText(("+ " + w2).rjust(max_len))
        self.word_sep.setText("─" * max_len)
        self.word_line3.setText(result.rjust(max_len))

        self.num_line1.setText("—")
        self.num_line2.setText("")
        self.num_sep.setText("")
        self.num_line3.setText("—")
        self._clear_badges()

    def set_solution(self, numbers, mapping_dict):
        """Animate digit reveal and populate badges."""
        n1, n2, n3 = numbers
        max_len = max(len(str(n1)), len(str(n2)), len(str(n3))) + 2

        s1 = str(n1).rjust(max_len)
        s2 = ("+ " + str(n2)).rjust(max_len)
        sep = "─" * max_len
        s3 = str(n3).rjust(max_len)

        self._anim_targets = [
            (self.num_line1, s1),
            (self.num_line2, s2),
            (self.num_sep,   sep),
            (self.num_line3, s3),
        ]
        for lbl, _ in self._anim_targets:
            lbl.setText("")
        self._anim_idx = 0
        self._anim_timer.start(60)

        self._populate_badges(mapping_dict)

    def set_no_solution(self):
        self.num_line1.setText("No")
        self.num_line2.setText("")
        self.num_sep.setText("")
        self.num_line3.setText("Solution")
        self.num_line1.setStyleSheet(f"color: {C['err']}; background: transparent; border: none;")
        self.num_line3.setStyleSheet(f"color: {C['err']}; background: transparent; border: none;")
        self._clear_badges()

    def _tick_digit_reveal(self):
        if self._anim_idx >= len(self._anim_targets):
            self._anim_timer.stop()
            return
        lbl, full_text = self._anim_targets[self._anim_idx]
        lbl.setText(full_text)
        self._anim_idx += 1

    def _clear_badges(self):
        while self.badge_grid.count():
            item = self.badge_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _populate_badges(self, mapping_dict):
        self._clear_badges()
        letters = sorted(mapping_dict.keys())
        badge_colors = [C["a1"], C["a2"], C["a3"], C["a4"], C["a5"],
                        "#FF6B35", "#4CAF50", "#00BCD4", "#E91E63", "#9C27B0"]
        cols = 4
        for idx, ch in enumerate(letters):
            digit = mapping_dict[ch]
            color = badge_colors[idx % len(badge_colors)]
            badge = self._make_badge(ch, str(digit), color)
            row, col = divmod(idx, cols)
            self.badge_grid.addWidget(badge, row, col)

    def _make_badge(self, letter, digit, color):
        f = QFrame()
        f.setFixedSize(54, 46)
        f.setStyleSheet(f"""
            QFrame {{
                background: {color}22;
                border: 1px solid {color}88;
                border-radius: 10px;
            }}
        """)
        layout = QVBoxLayout(f)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)
        l_lbl = QLabel(letter)
        l_lbl.setAlignment(Qt.AlignCenter)
        l_lbl.setFont(QFont(FONTS["mono"], 9))
        l_lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        d_lbl = QLabel(digit)
        d_lbl.setAlignment(Qt.AlignCenter)
        d_lbl.setFont(QFont(FONTS["mono"], 14, QFont.Bold))
        d_lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        layout.addWidget(l_lbl)
        layout.addWidget(d_lbl)
        return f


# ──────────────────────────────────────────────────────────────
#  EXPLANATION PANEL
# ──────────────────────────────────────────────────────────────
class ExplanationPanel(QFrame):
    """Scrollable panel showing solver trace steps with syntax coloring."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['card']};
                border: 1px solid {C['border']};
                border-radius: 18px;
            }}
        """)
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(30)
        sh.setColor(QColor(0, 0, 0, 100))
        sh.setOffset(0, 5)
        self.setGraphicsEffect(sh)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        header_row = QHBoxLayout()
        title = QLabel("SOLVER TRACE")
        title.setFont(QFont(FONTS["ui"], 9, QFont.Bold))
        title.setStyleSheet(f"color: {C['txt3']}; letter-spacing: 3px; background: transparent;")
        header_row.addWidget(title)
        header_row.addStretch()

        self.step_count_lbl = QLabel("")
        self.step_count_lbl.setStyleSheet(f"color: {C['a4']}; font-size: 11px; background: transparent;")
        header_row.addWidget(self.step_count_lbl)
        layout.addLayout(header_row)

        self.trace_text = QTextEdit()
        self.trace_text.setReadOnly(True)
        self.trace_text.setFont(QFont(FONTS["mono"], 10))
        self.trace_text.setStyleSheet(f"""
            QTextEdit {{
                background: {C['input']};
                color: {C['txt']};
                border: 1px solid {C['border']};
                border-radius: 10px;
                padding: 10px;
            }}
            QScrollBar:vertical {{
                background: {C['bg2']};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {C['glow']};
                border-radius: 3px;
            }}
        """)
        self.trace_text.setMinimumHeight(260)
        layout.addWidget(self.trace_text)

        self._stream_timer = QTimer(self)
        self._stream_timer.timeout.connect(self._stream_next)
        self._pending_steps = []
        self._stream_idx = 0

    def clear(self):
        self.trace_text.clear()
        self._pending_steps = []
        self._stream_idx = 0
        self.step_count_lbl.setText("")
        self._stream_timer.stop()

    def load_trace(self, steps: list, total_nodes: int):
        self.clear()
        self._pending_steps = steps
        self.step_count_lbl.setText(f"{total_nodes:,} nodes explored")
        self._stream_timer.start(18)

    def _stream_next(self):
        BATCH = 8
        for _ in range(BATCH):
            if self._stream_idx >= len(self._pending_steps):
                self._stream_timer.stop()
                return
            step = self._pending_steps[self._stream_idx]
            self._stream_idx += 1
            self._append_step(step)
        self.trace_text.moveCursor(QTextCursor.End)

    def _append_step(self, step):
        cursor = self.trace_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = QTextCharFormat()

        t = step.get("type", "info")
        if t == "assign":
            fmt.setForeground(QColor(C["txt"]))
        elif t == "backtrack":
            fmt.setForeground(QColor(C["err"]))
        elif t == "prune":
            fmt.setForeground(QColor(C["warn"]))
        elif t == "solution":
            fmt.setForeground(QColor(C["ok"]))
            fmt.setFontWeight(QFont.Bold)
        elif t == "no_solution":
            fmt.setForeground(QColor(C["err"]))
            fmt.setFontWeight(QFont.Bold)
        else:
            fmt.setForeground(QColor(C["txt2"]))

        cursor.insertText(step.get("msg", "") + "\n", fmt)
        self.trace_text.setTextCursor(cursor)


# ──────────────────────────────────────────────────────────────
#  RESULT SECTION
# ──────────────────────────────────────────────────────────────
class ResultSection(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['card']};
                border: 1px solid {C['border']};
                border-radius: 18px;
            }}
        """)
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(35)
        sh.setColor(QColor(0, 0, 0, 110))
        sh.setOffset(0, 6)
        self.setGraphicsEffect(sh)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setFont(QFont(FONTS["ui"], 15, QFont.Bold))
        self.status_lbl.setStyleSheet("background: transparent;")
        layout.addWidget(self.status_lbl)

        # Mapping row
        self.map_frame = QFrame()
        self.map_frame.setStyleSheet(f"""
            QFrame {{
                background: {C['input']};
                border: 1px solid {C['border']};
                border-radius: 12px;
            }}
        """)
        mfl = QVBoxLayout(self.map_frame)
        mfl.setContentsMargins(18, 14, 18, 14)
        mfl.setSpacing(6)
        mt = QLabel("LETTER → DIGIT MAPPING")
        mt.setFont(QFont(FONTS["ui"], 8, QFont.Bold))
        mt.setAlignment(Qt.AlignCenter)
        mt.setStyleSheet(f"color: {C['txt3']}; letter-spacing: 2px; background: transparent; border: none;")
        mfl.addWidget(mt)
        self.map_lbl = QLabel("")
        self.map_lbl.setAlignment(Qt.AlignCenter)
        self.map_lbl.setWordWrap(True)
        self.map_lbl.setFont(QFont(FONTS["mono"], 14, QFont.Bold))
        self.map_lbl.setStyleSheet(f"color: {C['a3']}; letter-spacing: 2px; background: transparent; border: none;")
        mfl.addWidget(self.map_lbl)
        layout.addWidget(self.map_frame)

        # Equation row
        self.eq_frame = QFrame()
        self.eq_frame.setStyleSheet(f"""
            QFrame {{
                background: {C['input']};
                border: 1px solid {C['border']};
                border-radius: 12px;
            }}
        """)
        efl = QVBoxLayout(self.eq_frame)
        efl.setContentsMargins(18, 14, 18, 14)
        efl.setSpacing(6)
        et = QLabel("NUMERIC EQUATION")
        et.setFont(QFont(FONTS["ui"], 8, QFont.Bold))
        et.setAlignment(Qt.AlignCenter)
        et.setStyleSheet(f"color: {C['txt3']}; letter-spacing: 2px; background: transparent; border: none;")
        efl.addWidget(et)
        self.eq_lbl = QLabel("")
        self.eq_lbl.setAlignment(Qt.AlignCenter)
        self.eq_lbl.setFont(QFont(FONTS["mono"], 18, QFont.Bold))
        self.eq_lbl.setStyleSheet(f"color: {C['a4']}; letter-spacing: 3px; background: transparent; border: none;")
        efl.addWidget(self.eq_lbl)
        layout.addWidget(self.eq_frame)

        # Stats row
        self.stats_row = QHBoxLayout()
        self.time_badge  = self._stat_badge("⏱ TIME", "—")
        self.nodes_badge = self._stat_badge("🔍 NODES", "—")
        self.letters_badge = self._stat_badge("🔤 LETTERS", "—")
        for b in [self.time_badge, self.nodes_badge, self.letters_badge]:
            self.stats_row.addWidget(b)
        layout.addLayout(self.stats_row)

        self.setVisible(False)

    def _stat_badge(self, title, value):
        f = QFrame()
        f.setStyleSheet(f"""
            QFrame {{
                background: {C['input']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
        """)
        vl = QVBoxLayout(f)
        vl.setContentsMargins(12, 8, 12, 8)
        vl.setSpacing(2)
        tl = QLabel(title)
        tl.setFont(QFont(FONTS["ui"], 8, QFont.Bold))
        tl.setStyleSheet(f"color: {C['txt3']}; letter-spacing: 1px; background: transparent; border: none;")
        tl.setAlignment(Qt.AlignCenter)
        vl.add = vl  # trick to store ref
        vl.addWidget(tl)
        vl2 = QLabel(value)
        vl2.setFont(QFont(FONTS["ui"], 13, QFont.Bold))
        vl2.setStyleSheet(f"color: {C['txt']}; background: transparent; border: none;")
        vl2.setAlignment(Qt.AlignCenter)
        vl.addWidget(vl2)
        f._val_lbl = vl2
        return f

    def show_result(self, solution, elapsed, nodes, words):
        self.setVisible(True)
        n_letters = len(set("".join(words)))
        self.letters_badge._val_lbl.setText(str(n_letters))
        self.time_badge._val_lbl.setText(f"{elapsed*1000:.2f} ms")
        self.nodes_badge._val_lbl.setText(f"{nodes:,}")

        if solution is None:
            self.status_lbl.setText("✗   No Solution Found")
            self.status_lbl.setStyleSheet(f"color: {C['err']}; background: transparent;")
            self.map_lbl.setText("This puzzle has no valid digit assignment.")
            self.eq_lbl.setText("—")
            self.map_frame.setStyleSheet(f"background: {C['input']}; border: 1px solid {C['err']}40; border-radius: 12px;")
        else:
            self.status_lbl.setText("✓   Solution Found!")
            self.status_lbl.setStyleSheet(f"color: {C['ok']}; background: transparent;")
            self.map_lbl.setText(solution["mapping"])
            self.eq_lbl.setText(solution["numeric_equation"])
            self.map_frame.setStyleSheet(f"background: {C['input']}; border: 1px solid {C['a3']}40; border-radius: 12px;")

    def show_error(self, msg):
        self.setVisible(True)
        self.status_lbl.setText("⚠   Input Error")
        self.status_lbl.setStyleSheet(f"color: {C['warn']}; background: transparent;")
        self.map_lbl.setText(msg)
        self.eq_lbl.setText("")
        self.time_badge._val_lbl.setText("—")
        self.nodes_badge._val_lbl.setText("—")
        self.letters_badge._val_lbl.setText("—")


# ──────────────────────────────────────────────────────────────
#  MAIN WINDOW
# ──────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Cryptarithm Puzzle Solver")
        self.setMinimumSize(1060, 720)
        self.resize(1200, 820)
        self._worker = None
        self._last_solution = None
        self._last_words = []
        self._setup_style()
        self._setup_ui()

    # ── Style ────────────────────────────────────────────────────────────────
    def _setup_style(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background: {C['bg']};
                color: {C['txt']};
                font-family: '{FONTS["ui"]}', Arial, sans-serif;
            }}
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                background: {C['bg2']}; width: 6px; border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {C['glow']}; border-radius: 3px;
            }}
            QComboBox {{
                background: {C['input']};
                color: {C['txt']};
                border: 2px solid {C['border']};
                border-radius: 10px;
                padding: 7px 14px;
                font-size: 13px;
                min-height: 36px;
            }}
            QComboBox:hover {{ border-color: {C['a1']}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {C['txt2']};
                margin-right: 8px;
            }}
            QComboBox QAbstractItemView {{
                background: {C['card']};
                color: {C['txt']};
                border: 1px solid {C['border']};
                selection-background-color: {C['a1']};
                padding: 4px;
                font-size: 13px;
            }}
        """)

    # ── Root layout ─────────────────────────────────────────────────────────
    def _setup_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Left scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        root_layout.addWidget(scroll, stretch=3)

        left_widget = QWidget()
        left_widget.setStyleSheet(f"background: {C['bg']};")
        scroll.setWidget(left_widget)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(38, 32, 20, 36)
        left_layout.setSpacing(0)

        # Header
        left_layout.addWidget(self._build_header())
        left_layout.addSpacing(24)

        # Input card
        left_layout.addWidget(self._build_input_card())
        left_layout.addSpacing(16)

        # Button row
        btn_row = self._build_button_row()
        left_layout.addLayout(btn_row)
        left_layout.addSpacing(18)

        # Result section
        self.result_section = ResultSection()
        left_layout.addWidget(self.result_section)
        left_layout.addSpacing(16)

        # Explanation panel
        self.explain_panel = ExplanationPanel()
        self.explain_panel.setVisible(False)
        left_layout.addWidget(self.explain_panel)

        left_layout.addStretch()

        # Right visualization panel
        right_container = QWidget()
        right_container.setStyleSheet(f"background: {C['bg2']};")
        right_container.setFixedWidth(300)
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(8, 32, 24, 32)
        right_layout.setSpacing(0)

        self.viz_panel = VisualizationPanel()
        right_layout.addWidget(self.viz_panel)
        right_layout.addStretch()
        root_layout.addWidget(right_container, stretch=0)

    # ── Header ───────────────────────────────────────────────────────────────
    def _build_header(self):
        frame = QFrame()
        frame.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setAlignment(Qt.AlignLeft)

        icon = QLabel("🔐")
        icon.setFont(QFont("Segoe UI Emoji", 26))
        icon.setStyleSheet("background: transparent;")
        title_row.addWidget(icon)
        title_row.addSpacing(8)

        title = QLabel("AI Cryptarithm Puzzle Solver")
        title.setFont(QFont(FONTS["title"], 22, QFont.Bold))
        title.setStyleSheet(f"color: {C['txt']}; background: transparent; letter-spacing: 0.5px;")
        title_row.addWidget(title)
        layout.addLayout(title_row)

        sub = QLabel(
            "Constraint Satisfaction Problem  ·  Backtracking + Forward Checking  ·  Instant Results"
        )
        sub.setFont(QFont(FONTS["ui"], 10))
        sub.setStyleSheet(f"color: {C['txt2']}; background: transparent; letter-spacing: 1.5px;")
        layout.addWidget(sub)

        sep = QFrame()
        sep.setFixedHeight(2)
        sep.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 transparent, stop:0.25 {C['a1']},
                stop:0.65 {C['a2']}, stop:1 transparent);
            border-radius: 1px;
        """)
        layout.addSpacing(8)
        layout.addWidget(sep)
        return frame

    # ── Input Card ───────────────────────────────────────────────────────────
    def _build_input_card(self):
        card = card_frame(20)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        layout.addWidget(SectionTitle("PUZZLE INPUT"))

        # Three-box input row
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        input_row.setAlignment(Qt.AlignCenter)

        self.w1_inp = CryptoInput("WORD 1", min_w=150)
        self.w2_inp = CryptoInput("WORD 2", min_w=150)
        self.res_inp = CryptoInput("RESULT", min_w=170)

        input_row.addWidget(self.w1_inp)
        input_row.addWidget(OpLabel("+"))
        input_row.addWidget(self.w2_inp)
        input_row.addWidget(OpLabel("="))
        input_row.addWidget(self.res_inp)
        layout.addLayout(input_row)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {C['border']}; border-radius: 1px;")
        layout.addWidget(div)

        # Dropdown row
        dd_row = QHBoxLayout()
        dd_row.setSpacing(12)
        dd_lbl = QLabel("✦  Quick Load:")
        dd_lbl.setStyleSheet(f"color: {C['txt2']}; font-size: 13px; background: transparent;")
        dd_row.addWidget(dd_lbl)

        self.combo = QComboBox()
        self.combo.addItem("— Select an example puzzle —")
        for w1, w2, res in EXAMPLE_PUZZLES:
            self.combo.addItem(f"{w1}  +  {w2}  =  {res}")
        self.combo.currentIndexChanged.connect(self._load_example)
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        dd_row.addWidget(self.combo)
        layout.addLayout(dd_row)
        return card

    # ── Button Row ───────────────────────────────────────────────────────────
    def _build_button_row(self):
        row = QHBoxLayout()
        row.setSpacing(12)

        self.solve_btn = GlowButton("⚡  Solve Puzzle", C["a1"], C["a2"])
        self.solve_btn.clicked.connect(self._on_solve)
        row.addWidget(self.solve_btn, stretch=2)

        self.explain_btn = GlowButton("🔍  Show Explanation", C["a5"], C["a1"])
        self.explain_btn.clicked.connect(self._on_explain)
        self.explain_btn.setEnabled(False)
        row.addWidget(self.explain_btn, stretch=1)

        self.clear_btn = GlowButton("✕  Clear", C["txt3"], "#444870")
        self.clear_btn.clicked.connect(self._on_clear)
        row.addWidget(self.clear_btn, stretch=1)

        return row

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _load_example(self, idx):
        if idx == 0:
            return
        w1, w2, res = EXAMPLE_PUZZLES[idx - 1]
        self.w1_inp.setText(w1)
        self.w2_inp.setText(w2)
        self.res_inp.setText(res)
        self.result_section.setVisible(False)
        self.explain_panel.setVisible(False)
        self.explain_btn.setEnabled(False)
        self._last_solution = None
        self._last_words = [w1, w2, res]
        self.viz_panel.set_words(w1, w2, res)

    def _get_inputs(self):
        return (
            self.w1_inp.text().strip().upper(),
            self.w2_inp.text().strip().upper(),
            self.res_inp.text().strip().upper(),
        )

    def _validate(self, w1, w2, res):
        if not (w1 and w2 and res):
            return "Please fill in all three word fields."
        for w in [w1, w2, res]:
            if not w.isalpha():
                return f"'{w}' contains non-letter characters."
        if len(set(w1 + w2 + res)) > 10:
            return f"Too many unique letters ({len(set(w1+w2+res))}). Maximum is 10."
        return None

    # ── Actions ──────────────────────────────────────────────────────────────
    def _on_clear(self):
        self.w1_inp.clear()
        self.w2_inp.clear()
        self.res_inp.clear()
        self.combo.setCurrentIndex(0)
        self.result_section.setVisible(False)
        self.explain_panel.setVisible(False)
        self.explain_btn.setEnabled(False)
        self._last_solution = None
        self._last_words = []

    def _on_solve(self):
        w1, w2, res = self._get_inputs()
        err = self._validate(w1, w2, res)
        if err:
            self.result_section.show_error(err)
            return

        self._last_words = [w1, w2, res]
        self.viz_panel.set_words(w1, w2, res)
        self.result_section.setVisible(False)
        self.explain_panel.setVisible(False)
        self.explain_btn.setEnabled(False)

        self.solve_btn.setEnabled(False)
        self.solve_btn.setText("⟳  Solving…")
        self.solve_btn.start_pulse()

        self._worker = SolverWorker(w1, w2, res, trace=False)
        self._worker.finished.connect(self._on_solved)
        self._worker.start()

    def _on_solved(self, assignment, elapsed, nodes, error, trace):
        self.solve_btn.setEnabled(True)
        self.solve_btn.setText("⚡  Solve Puzzle")
        self.solve_btn.stop_pulse()

        if error:
            self.result_section.show_error(error)
            return

        words = self._last_words
        solution = format_solution(words, assignment) if assignment else None
        self._last_solution = solution
        self.result_section.show_result(solution, elapsed, nodes, words)

        if solution:
            self.viz_panel.set_solution(solution["numbers"], solution["mapping_dict"])
            self.explain_btn.setEnabled(True)
        else:
            self.viz_panel.set_no_solution()

    def _on_explain(self):
        w1, w2, res = self._get_inputs()
        err = self._validate(w1, w2, res)
        if err:
            return

        self.explain_panel.setVisible(True)
        self.explain_panel.clear()

        self.explain_btn.setEnabled(False)
        self.explain_btn.setText("⟳  Building trace…")

        self._trace_worker = SolverWorker(w1, w2, res, trace=True)
        self._trace_worker.finished.connect(self._on_trace_ready)
        self._trace_worker.start()

    def _on_trace_ready(self, assignment, elapsed, nodes, error, trace):
        self.explain_btn.setEnabled(True)
        self.explain_btn.setText("🔍  Show Explanation")
        if error or not trace:
            return
        self.explain_panel.load_trace(trace, nodes)