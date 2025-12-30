# app.py
import threading
import tkinter as tk
from tkinter import messagebox

from main import get_growth_table, run_full_pipeline


# ===== Colors tuned to the screenshot =====
BG = "#F5F2EE"            # off-white page
CARD = "#FFFFFF"
BORDER = "#E7E3DD"
HEADER_BG = "#FBFAF9"
GRID = "#EFECE6"

TEXT = "#1F1F1F"
HEADER_TEXT = "#6B6B6B"

BTN_BLUE = "#3B82F6"
BTN_BLUE_HOVER = "#2F74E6"
BTN_BLUE_TEXT = "#FFFFFF"

BTN_WHITE = "#FFFFFF"
BTN_WHITE_BORDER = "#E6E2DC"
BTN_WHITE_HOVER = "#FAF8F5"
BTN_WHITE_TEXT = "#222222"

ROW_HOVER = "#F7F4EF"

PILL_RED_BG = "#F9E7E7"
PILL_RED_TEXT = "#D94B4B"
PILL_GREEN_BG = "#E2F4EA"
PILL_GREEN_TEXT = "#1F8F4A"
PILL_NEU_BG = "#F0EFED"
PILL_NEU_TEXT = "#6C6C6C"

LOADING_TEXT = "#8A8783"


def parse_growth(growth_str):
    if growth_str is None:
        return None
    s = str(growth_str).strip()
    if not s:
        return None
    if s.endswith("%"):
        s = s[:-1].strip()
    try:
        return float(s)
    except Exception:
        return None


def round_rect(canvas, x1, y1, x2, y2, r, **kwargs):
    points = [
        x1+r, y1,
        x2-r, y1,
        x2, y1,
        x2, y1+r,
        x2, y2-r,
        x2, y2,
        x2-r, y2,
        x1+r, y2,
        x1, y2,
        x1, y2-r,
        x1, y1+r,
        x1, y1
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=36, **kwargs)


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Reddit Scanner")
        self.geometry("1200x720")
        self.minsize(1100, 680)
        self.configure(bg=BG)

        self.canvas = tk.Canvas(self, highlightthickness=0, bg=BG)
        self.canvas.pack(fill="both", expand=True)

        # state
        self._busy = False
        self._row_data = []      # list of (ticker, stats)
        self._rows = []          # hitboxes for hover rows
        self._hover_idx = None

        # button hover + hitboxes
        self.btn_scan_box = (0, 0, 0, 0)
        self.btn_refresh_box = (0, 0, 0, 0)
        self._btn_scan_hover = False
        self._btn_refresh_hover = False

        # scrolling
        self._scroll_offset = 0          # row index offset
        self._visible_rows = 0
        self._rows_area = (0, 0, 0, 0)   # (x1,y1,x2,y2) rows-only area

        # scrollbar widget (positioned in redraw)
        self.vscroll = tk.Scrollbar(self, orient="vertical", command=self.on_scrollbar)

        # bindings
        self.bind("<Configure>", lambda e: self.redraw())
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Leave>", lambda e: self.clear_hover())
        self.canvas.bind("<Button-1>", self.on_click_buttons_only)

        # scroll wheel support (Win/Mac)
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        # Linux
        self.canvas.bind_all("<Button-4>", self.on_mousewheel)
        self.canvas.bind_all("<Button-5>", self.on_mousewheel)

        # initial draw + auto load
        self.redraw()
        self.refresh_growth(auto=True)

    # ---------- button clicks only ----------
    def on_click_buttons_only(self, e):
        if self.point_in_box(e.x, e.y, self.btn_scan_box):
            self.run_scan()
            return
        if self.point_in_box(e.x, e.y, self.btn_refresh_box):
            self.refresh_growth()
            return
        # no row selection

    # ---------- scrolling ----------
    def _clamp_scroll(self, total_rows, visible_rows):
        max_off = max(0, total_rows - visible_rows)
        if self._scroll_offset < 0:
            self._scroll_offset = 0
        if self._scroll_offset > max_off:
            self._scroll_offset = max_off
        return max_off

    def on_scrollbar(self, *args):
        if not self._row_data:
            return

        total = len(self._row_data)
        visible = self._visible_rows
        if visible <= 0:
            return

        max_off = self._clamp_scroll(total, visible)

        if args[0] == "moveto":
            frac = float(args[1])
            self._scroll_offset = int(frac * max_off) if max_off > 0 else 0
        elif args[0] == "scroll":
            amount = int(args[1])
            unit = args[2]
            if unit == "units":
                self._scroll_offset += amount
            elif unit == "pages":
                self._scroll_offset += amount * visible

        self._clamp_scroll(total, visible)
        self._hover_idx = None
        self.redraw()

    def on_mousewheel(self, e):
        # scroll only when mouse is over the rows area
        x1, y1, x2, y2 = self._rows_area
        mx = self.winfo_pointerx() - self.winfo_rootx()
        my = self.winfo_pointery() - self.winfo_rooty()
        if not (x1 <= mx <= x2 and y1 <= my <= y2):
            return

        if not self._row_data:
            return

        total = len(self._row_data)
        visible = self._visible_rows
        if visible <= 0:
            return

        # normalize direction
        if hasattr(e, "num") and e.num in (4, 5):
            direction = -1 if e.num == 4 else 1
        else:
            delta = getattr(e, "delta", 0)
            if delta == 0:
                return
            if abs(delta) < 120:
                direction = -1 if delta > 0 else 1
            else:
                direction = int(-delta / 120)

        self._scroll_offset += direction
        self._clamp_scroll(total, visible)
        self._hover_idx = None
        self.redraw()

    # ---------- drawing ----------
    def redraw(self):
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10 or h < 10:
            return

        self.canvas.delete("all")
        self.canvas.create_rectangle(0, 0, w, h, fill=BG, outline="")

        # main card geometry
        pad = 70
        card_x1 = pad
        card_y1 = pad + 40
        card_x2 = w - pad
        card_y2 = h - pad

        # shadow
        for dx, dy, col in [(10, 12, "#ECE9E4"), (6, 8, "#E2DED8"), (3, 4, "#D9D5CF")]:
            round_rect(self.canvas, card_x1+dx, card_y1+dy, card_x2+dx, card_y2+dy, 26, fill=col, outline="")

        # card
        round_rect(self.canvas, card_x1, card_y1, card_x2, card_y2, 26, fill=CARD, outline=BORDER, width=1)

        # buttons row (centered)
        btn_y = card_y1 + 65
        self.btn_scan_box = self.draw_button(
            cx=(w/2) - 145,
            y=btn_y,
            width=320,
            height=48,
            fill=(BTN_BLUE_HOVER if self._btn_scan_hover else BTN_BLUE),
            outline="",
            text="Run Reddit Scan + Update",
            text_color=BTN_BLUE_TEXT,
            shadow=True
        )

        self.btn_refresh_box = self.draw_button(
            cx=(w/2) + 230,
            y=btn_y,
            width=280,
            height=48,
            fill=(BTN_WHITE_HOVER if self._btn_refresh_hover else BTN_WHITE),
            outline=BTN_WHITE_BORDER,
            text="Refresh Growth Table",
            text_color=BTN_WHITE_TEXT,
            shadow=False
        )

        # title + loading (left-aligned with table)
        title_y = btn_y + 110
        title_x = card_x1 + 60
        self.canvas.create_text(title_x, title_y, text="Growth Table",
                                font=("Helvetica", 22, "bold"),
                                fill=TEXT, anchor="w")

        if self._busy:
            self.canvas.create_text(title_x, title_y + 26, text="Loading…",
                                    font=("Helvetica", 12),
                                    fill=LOADING_TEXT, anchor="w")

        # table card
        table_x1 = card_x1 + 60
        table_x2 = card_x2 - 60
        table_y1 = title_y + 50
        table_y2 = card_y2 - 70

        round_rect(self.canvas, table_x1, table_y1, table_x2, table_y2, 16,
                   fill="#FFFFFF", outline=BTN_WHITE_BORDER, width=1)

        header_h = 48
        round_rect(self.canvas, table_x1, table_y1, table_x2, table_y1 + header_h, 16,
                   fill=HEADER_BG, outline="", width=0)
        self.canvas.create_line(table_x1, table_y1 + header_h, table_x2, table_y1 + header_h, fill=GRID, width=1)

        # columns
        cols = [
            ("Ticker", 0.18, "left"),
            ("Price", 0.22, "center"),
            ("Original Run", 0.34, "center"),
            ("Growth%", 0.26, "right"),
        ]
        total_w = table_x2 - table_x1
        xs = [table_x1]
        x = table_x1
        for _, frac, _ in cols:
            x += total_w * frac
            xs.append(x)

        for i, (name, _frac, align) in enumerate(cols):
            cx1, cx2 = xs[i], xs[i+1]
            if align == "left":
                tx, anchor = cx1 + 24, "w"
            elif align == "right":
                tx, anchor = cx2 - 24, "e"
            else:
                tx, anchor = (cx1 + cx2) / 2, "center"

            self.canvas.create_text(tx, table_y1 + header_h/2 + 1,
                                    text=name, font=("Helvetica", 12),
                                    fill=HEADER_TEXT, anchor=anchor)

            if i != 0:
                self.canvas.create_line(cx1, table_y1 + 14, cx1, table_y1 + header_h - 14, fill=GRID, width=1)

        # rows area
        rows_y1 = table_y1 + header_h
        rows_y2 = table_y2 - 20
        row_h = 58

        self._rows_area = (table_x1, rows_y1, table_x2, rows_y2)

        self._rows = []
        self._visible_rows = max(0, int((rows_y2 - rows_y1) // row_h))
        total_rows = len(self._row_data)

        max_off = self._clamp_scroll(total_rows, self._visible_rows)
        start = self._scroll_offset
        end = start + self._visible_rows
        shown = self._row_data[start:end]

        # scrollbar update / placement
        if total_rows <= self._visible_rows or self._visible_rows == 0:
            self.vscroll.place_forget()
        else:
            sb_w = 14
            self.vscroll.place(x=table_x2 - sb_w - 8, y=rows_y1 + 6, width=sb_w, height=(rows_y2 - rows_y1) - 12)
            first = start / total_rows
            last = min(1.0, (start + self._visible_rows) / total_rows)
            self.vscroll.set(first, last)

        for i, (ticker, stats) in enumerate(shown):
            y1 = rows_y1 + i * row_h
            y2 = y1 + row_h

            bg = ROW_HOVER if self._hover_idx == i else "#FFFFFF"
            self.canvas.create_rectangle(table_x1+1, y1, table_x2-1, y2, fill=bg, outline="")
            self.canvas.create_line(table_x1 + 22, y2, table_x2 - 22, y2, fill=GRID, width=1)

            price = stats.get("Price", "N/A")
            date = stats.get("Original Run", "")
            growth_str = stats.get("Growth %", None)

            try:
                price_disp = f"{float(price):.2f}"
            except Exception:
                price_disp = str(price)

            g = parse_growth(growth_str)
            if g is None:
                g_disp = "N/A"
                pill_bg, pill_fg = PILL_NEU_BG, PILL_NEU_TEXT
                arrow = ""
            else:
                g_disp = f"{g:+.2f}%"
                if abs(g) < 0.01:
                    pill_bg, pill_fg = PILL_NEU_BG, PILL_NEU_TEXT
                    arrow = ""
                elif g > 0:
                    pill_bg, pill_fg = PILL_GREEN_BG, PILL_GREEN_TEXT
                    arrow = "▲"
                else:
                    pill_bg, pill_fg = PILL_RED_BG, PILL_RED_TEXT
                    arrow = "▲"

            self.canvas.create_text(xs[0] + 24, (y1+y2)/2 + 1,
                                    text=str(ticker),
                                    font=("Helvetica", 16),
                                    fill=TEXT, anchor="w")

            self.canvas.create_text((xs[1] + xs[2])/2, (y1+y2)/2 + 1,
                                    text=price_disp,
                                    font=("Helvetica", 16),
                                    fill=TEXT, anchor="center")

            self.canvas.create_text((xs[2] + xs[3])/2, (y1+y2)/2 + 1,
                                    text=str(date),
                                    font=("Helvetica", 16),
                                    fill=TEXT, anchor="center")

            pill_w, pill_h = 132, 34
            px2 = xs[4] - 26
            px1 = px2 - pill_w
            py1 = (y1+y2)/2 - pill_h/2
            py2 = py1 + pill_h

            round_rect(self.canvas, px1, py1, px2, py2, 10, fill=pill_bg, outline="", width=0)
            self.canvas.create_text(px1 + 16, (py1+py2)/2 + 1,
                                    text=g_disp, font=("Helvetica", 14),
                                    fill=pill_fg, anchor="w")
            if arrow:
                self.canvas.create_text(px2 - 18, (py1+py2)/2 + 1,
                                        text=arrow, font=("Helvetica", 10),
                                        fill=pill_fg, anchor="e")

            # hover hitbox (index is visible-row index, not global)
            self._rows.append((table_x1, y1, table_x2, y2))

        # ensure scroll offset always valid after resize
        if total_rows > 0:
            self._clamp_scroll(total_rows, self._visible_rows)

    def draw_button(self, cx, y, width, height, fill, outline, text, text_color, shadow=False):
        x1 = cx - width/2
        y1 = y
        x2 = cx + width/2
        y2 = y + height

        if shadow:
            round_rect(self.canvas, x1, y1+3, x2, y2+3, 12, fill="#D8D3CC", outline="", width=0)

        round_rect(self.canvas, x1, y1, x2, y2, 12, fill=fill,
                   outline=outline if outline else "", width=1 if outline else 0)

        self.canvas.create_text((x1+x2)/2, (y1+y2)/2 + 1,
                                text=text, font=("Helvetica", 13),
                                fill=text_color, anchor="center")

        return (x1, y1, x2, y2)

    # ---------- mouse interaction ----------
    def on_mouse_move(self, e):
        self._btn_scan_hover = self.point_in_box(e.x, e.y, self.btn_scan_box)
        self._btn_refresh_hover = self.point_in_box(e.x, e.y, self.btn_refresh_box)

        idx = self.hit_test_row(e.x, e.y)
        if idx != self._hover_idx:
            self._hover_idx = idx

        self.redraw()

    def clear_hover(self):
        self._hover_idx = None
        self._btn_scan_hover = False
        self._btn_refresh_hover = False
        self.redraw()

    def point_in_box(self, x, y, box):
        x1, y1, x2, y2 = box
        return x1 <= x <= x2 and y1 <= y <= y2

    def hit_test_row(self, x, y):
        for i, (x1, y1, x2, y2) in enumerate(self._rows):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return i
        return None

    # ---------- data ----------
    def set_busy(self, busy: bool):
        self._busy = busy
        self.redraw()

    def refresh_growth(self, auto=False):
        if self._busy:
            return

        def worker():
            try:
                final_output_list, _df = get_growth_table()
                err = None
            except Exception as e:
                final_output_list = None
                err = str(e)

            def done():
                self.set_busy(False)
                if final_output_list is None:
                    messagebox.showerror("Error", err)
                    return
                if not final_output_list and not auto:
                    messagebox.showinfo("No data", "Database is empty. Run the Reddit scan first.")
                self._row_data = final_output_list
                self._scroll_offset = 0
                self._hover_idx = None
                self.redraw()

            self.after(0, done)

        self.set_busy(True)
        threading.Thread(target=worker, daemon=True).start()

    def run_scan(self):
        if self._busy:
            return

        def worker():
            try:
                final_output_list, _df = run_full_pipeline()
                err = None
            except Exception as e:
                final_output_list = None
                err = str(e)

            def done():
                self.set_busy(False)
                if final_output_list is None:
                    messagebox.showerror("Error", err)
                    return
                self._row_data = final_output_list
                self._scroll_offset = 0
                self._hover_idx = None
                self.redraw()

            self.after(0, done)

        self.set_busy(True)
        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
