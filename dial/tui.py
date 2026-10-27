"""Interactive FSOT dial.

Type one expression. The pinned engine computes it. A selected published
row supplies the measured value and the bar. Nothing is sent.
"""

from __future__ import annotations

import curses
import json
import sys
from pathlib import Path

HUB_PATH = Path("/home/damian-palumbo/Desktop/fsot repos/FSOT-2.1-Lean")
ROWS_PATH = Path(
    "/home/damian-palumbo/Desktop/fsot repos/FSOT-2012-Mac-Mini/results/gemma4_q6_rows.json"
)


def boot() -> None:
    import dial.engine as engine

    engine.HUB = HUB_PATH
    engine.environment.cache_clear()


def load_rows() -> list[dict]:
    if not ROWS_PATH.exists():
        return []
    document = json.loads(ROWS_PATH.read_text(encoding="utf-8"))
    return list(document.get("proposals") or [])


def judge(formula: str, row: dict | None) -> dict:
    from dial.engine import gate
    from dial.score import kill_metric, score_row

    text = (formula or "").strip()
    result = gate(text)
    scored = {
        "formula": text,
        "gate_ok": bool(result["ok"]),
        "reasons": list(result["reasons"]),
        "value": result["value"],
        "error_pct": None,
        "z": None,
        "inside_bar": False,
        "kill_reason": "no_proposal" if not text else "gate",
        "row": row,
    }
    if result["ok"] and row is not None:
        measured = row.get("measured")
        bar = row.get("bar_pct")
        if isinstance(measured, (int, float)) and isinstance(bar, (int, float)):
            score = score_row(float(result["value"]), float(measured), float(bar))
            kill = kill_metric(score)
            scored["error_pct"] = score["error_pct"]
            scored["z"] = score["z"]
            scored["inside_bar"] = bool(score["inside_bar"])
            scored["kill_reason"] = kill["reason"]
    return scored


def check() -> int:
    boot()
    from dial.engine import environment

    names = environment()
    needed = ("h", "m_e", "mu_0", "k_b", "hbar", "c_light", "m_h", "nu_cs")
    missing = [name for name in needed if name not in names]
    rows = load_rows()
    permeability = next(
        (row for row in rows if row.get("name") == "vacuum_magnetic_permeability"),
        None,
    )
    scored = judge("4*pi*10^(-7)", permeability)
    if missing or not scored["gate_ok"] or not scored["inside_bar"]:
        print("missing", missing)
        print("scored", scored["gate_ok"], scored["z"], scored["reasons"])
        return 1
    print(
        f"names {len(names)} rows {len(rows)} "
        f"mu0 z {scored['z']:.6g} inside"
    )
    return 0


def _clip(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return text[:1]
    return text[: width - 1] + "…"


def _try_curses(fn, *args) -> None:
    try:
        fn(*args)
    except curses.error:
        pass


def _put(screen, y: int, x: int, text: str, attr: int = 0) -> None:
    height, width = screen.getmaxyx()
    if y < 0 or y >= height or x >= width:
        return
    shown = _clip(text, width - x)
    try:
        screen.addstr(y, x, shown, attr)
    except curses.error:
        pass


class Dial:
    def __init__(self, screen) -> None:
        self.screen = screen
        self.rows = load_rows()
        from dial.engine import environment

        self.names = sorted(environment().items())
        self.view = "rows"
        self.selected = 0
        self.scroll = 0
        self.formula = ""
        self.cursor = 0
        self.editing = False
        self.result: dict | None = None
        for index, row in enumerate(self.rows):
            if row.get("inside_bar"):
                self.selected = index
                break
        self.screen.keypad(True)
        self.color = False
        _try_curses(curses.curs_set, 0)
        try:
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(1, curses.COLOR_GREEN, -1)
            curses.init_pair(2, curses.COLOR_YELLOW, -1)
            curses.init_pair(3, curses.COLOR_RED, -1)
            curses.init_pair(4, curses.COLOR_CYAN, -1)
            self.color = True
        except curses.error:
            self.color = False

    def items(self) -> list:
        return self.rows if self.view == "rows" else self.names

    def score_current(self) -> None:
        row = None
        if self.view == "rows" and self.rows:
            row = self.rows[self.selected]
            if not self.formula.strip():
                self.formula = str(row.get("reply") or "")
                self.cursor = len(self.formula)
        self.result = judge(self.formula, row)

    def move(self, delta: int) -> None:
        items = self.items()
        if not items:
            return
        self.selected = max(0, min(len(items) - 1, self.selected + delta))

    def edit_key(self, key) -> bool:
        if key in (27, curses.KEY_EXIT):
            self.editing = False
            return True
        if key in ("\n", "\r", curses.KEY_ENTER):
            self.editing = False
            self.score_current()
            return True
        if key in (curses.KEY_BACKSPACE, 127, "\b", "\x7f"):
            if self.cursor > 0:
                self.formula = self.formula[: self.cursor - 1] + self.formula[self.cursor :]
                self.cursor -= 1
            return True
        if key == curses.KEY_DC:
            self.formula = self.formula[: self.cursor] + self.formula[self.cursor + 1 :]
            return True
        if key == curses.KEY_LEFT:
            self.cursor = max(0, self.cursor - 1)
            return True
        if key == curses.KEY_RIGHT:
            self.cursor = min(len(self.formula), self.cursor + 1)
            return True
        if key == curses.KEY_HOME:
            self.cursor = 0
            return True
        if key == curses.KEY_END:
            self.cursor = len(self.formula)
            return True
        if key == "\x15":
            self.formula = ""
            self.cursor = 0
            return True
        if isinstance(key, str) and key.isprintable():
            self.formula = self.formula[: self.cursor] + key + self.formula[self.cursor :]
            self.cursor += 1
            return True
        return False

    def browse_key(self, key) -> bool:
        if key in ("q", "Q"):
            return False
        if key in ("i", "I", "/"):
            self.editing = True
            return True
        if key in ("n", "N"):
            self.view = "names"
            self.selected = 0
            self.scroll = 0
            return True
        if key in ("r", "R"):
            self.view = "rows"
            self.selected = 0
            self.scroll = 0
            return True
        if key in ("j", curses.KEY_DOWN):
            self.move(1)
            return True
        if key in ("k", curses.KEY_UP):
            self.move(-1)
            return True
        if key in (curses.KEY_NPAGE,):
            self.move(10)
            return True
        if key in (curses.KEY_PPAGE,):
            self.move(-10)
            return True
        if key in ("\n", "\r", curses.KEY_ENTER):
            self.score_current()
            return True
        return True

    def draw(self) -> None:
        screen = self.screen
        screen.erase()
        height, width = screen.getmaxyx()
        if height < 8 or width < 40:
            _put(screen, 0, 0, "Make the window larger.")
            screen.refresh()
            return
        title = "FSOT dial"
        hint = "i type   j/k move   r rows   n names   enter score   q quit"
        _put(screen, 0, 0, title, curses.A_BOLD | self._color(4))
        _put(screen, 0, len(title) + 2, _clip(hint, width - len(title) - 2))
        formula = self.formula if self.formula else "(empty — i to type, enter scores the row reply)"
        _put(screen, 2, 0, "formula  " + formula, curses.A_BOLD if self.editing else 0)
        if self.editing:
            _put(screen, 3, 0, "editing  enter scores   esc keeps the text   ctrl-u clears", self._color(4))
        self._draw_result(5)
        list_top = 11
        self._draw_list(list_top, height - 1)
        _put(
            screen,
            height - 1,
            0,
            "bare c and g are Catalan's constant    speed of light is c_light",
        )
        if self.editing:
            _try_curses(curses.curs_set, 1)
            cursor_x = min(9 + self.cursor, width - 1)
            _try_curses(screen.move, 2, cursor_x)
        else:
            _try_curses(curses.curs_set, 0)
        screen.refresh()

    def _draw_result(self, top: int) -> None:
        result = self.result
        if result is None:
            _put(self.screen, top, 0, "No score yet.")
            return
        if not result["formula"]:
            _put(self.screen, top, 0, "Type an expression first.", self._color(2))
            return
        if result["gate_ok"]:
            _put(self.screen, top, 0, f"gate ok    value {result['value']}", self._color(1))
        else:
            reasons = ", ".join(result["reasons"]) or "rejected"
            _put(self.screen, top, 0, "gate rejected  " + reasons, self._color(3))
        if result["z"] is None:
            _put(self.screen, top + 1, 0, "Pick a published row to score z.")
            return
        word = "inside the published bar" if result["inside_bar"] else "outside the published bar"
        color = self._color(1) if result["inside_bar"] else self._color(2)
        _put(
            self.screen,
            top + 1,
            0,
            f"z {result['z']:.6g}    percent error {result['error_pct']:.6g}    {word}",
            color,
        )
        row = result["row"] or {}
        _put(
            self.screen,
            top + 2,
            0,
            f"against {row.get('name')}    measured {row.get('measured')}    bar {row.get('bar_pct')} %",
        )

    def _draw_list(self, top: int, bottom: int) -> None:
        screen = self.screen
        _, width = screen.getmaxyx()
        visible = max(1, bottom - top)
        items = self.items()
        if self.selected < self.scroll:
            self.scroll = self.selected
        if self.selected >= self.scroll + visible:
            self.scroll = self.selected - visible + 1
        heading = "Published rows" if self.view == "rows" else "Engine names"
        _put(screen, top - 1, 0, heading, curses.A_BOLD)
        if not items:
            _put(screen, top, 0, "Nothing loaded.")
            return
        for offset, index in enumerate(range(self.scroll, min(len(items), self.scroll + visible))):
            y = top + offset
            attr = curses.A_REVERSE if index == self.selected else 0
            if self.view == "rows":
                row = items[index]
                if row.get("inside_bar"):
                    mark = "inside"
                elif row.get("gate_ok"):
                    mark = "outside"
                else:
                    mark = "rejected"
                label = (
                    f"{row.get('i'):>2}  {mark:<8}  {row.get('domain')}  "
                    f"{row.get('name')}  {row.get('reply')}"
                )
            else:
                name, value = items[index]
                label = f"{name:<16} {value}"
            _put(screen, y, 0, label, attr)

    def _color(self, pair: int) -> int:
        if not self.color:
            return 0
        return curses.color_pair(pair)

    def run(self) -> None:
        while True:
            self.draw()
            key = self.screen.get_wch()
            if self.editing:
                self.edit_key(key)
                continue
            if not self.browse_key(key):
                return


def run(screen) -> None:
    Dial(screen).run()


def main() -> int:
    if "--check" in sys.argv:
        return check()
    boot()
    curses.wrapper(run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
