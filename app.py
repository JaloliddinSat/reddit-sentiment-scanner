# app.py
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# Uses your functions exactly as you defined them in main.py
from main import get_growth_table, run_full_pipeline

OFFWHITE = "#F6F4EF"
BRIGHTER = "#FFFDF8"
TEXT = "#222222"

# Row background tints (subtle, Apple-ish)
ROW_POS_BG = "#AFFFCD"   # light green tint
ROW_NEG_BG = "#FFC1C1"   # light red tint
ROW_NEU_BG = "#F0F0F0"   # light grey tint


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#%02x%02x%02x" % rgb


def _lerp(a, b, t):
    return int(a + (b - a) * t)


def _parse_growth(growth_str):
    """
    growth_str comes from your dict: stats["Growth %"] like "0.12345%"
    Returns float percent (e.g., 0.12345) or None if can't parse.
    """
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


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Reddit Scanner")
        self.geometry("980x560")
        self.minsize(920, 520)
        self.configure(bg=OFFWHITE)

        # background canvas for gradient
        self.bg_canvas = tk.Canvas(self, highlightthickness=0, bg=OFFWHITE)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bind("<Configure>", lambda e: self._redraw_background())

        # overlay frame for UI widgets
        self.root_frame = tk.Frame(self, bg=OFFWHITE)
        self.root_frame.place(relwidth=1, relheight=1)

        self._setup_styles()
        self._build_layout()

        # Auto-run growth table on startup (NO reddit scan)
        self.refresh_growth(auto=True)

    def _setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TFrame", background=OFFWHITE)
        style.configure("TLabel", background=OFFWHITE, foreground=TEXT)

        # Better button feel + fix vertical centering (padding controls this)
        style.configure(
            "Primary.TButton",
            padding=(18, 12),           # (x, y) padding; y fixes vertical centering
            anchor="center"
        )
        style.configure(
            "Secondary.TButton",
            padding=(18, 12),
            anchor="center"
        )

        style.configure(
            "Treeview",
            background=OFFWHITE,
            fieldbackground=OFFWHITE,
            foreground=TEXT,
            rowheight=34,
            borderwidth=0
        )
        style.configure("Treeview.Heading", background=OFFWHITE, foreground=TEXT)
        style.map("Treeview", background=[("selected", "#BAB4A7")])

    def _build_layout(self):
        # Center buttons near top
        btn_frame = ttk.Frame(self.root_frame)
        btn_frame.place(relx=0.5, rely=0.12, anchor="n")  # center horizontally

        self.btn_scan = ttk.Button(
            btn_frame,
            text="Run Reddit Scan + Update",
            style="Primary.TButton",
            command=self.run_scan
        )
        self.btn_refresh = ttk.Button(
            btn_frame,
            text="Refresh Growth Table",
            style="Secondary.TButton",
            command=self.refresh_growth
        )

        # stacked, centered
        self.btn_scan.pack(pady=(0, 10))
        self.btn_refresh.pack()

        # Centered table container
        table_frame = ttk.Frame(self.root_frame)
        table_frame.place(relx=0.5, rely=0.30, relwidth=0.78, relheight=0.60, anchor="n")

        header_row = ttk.Frame(table_frame)
        header_row.pack(fill="x", pady=(0, 10))

        ttk.Label(header_row, text="Growth Table", font=("Helvetica", 16, "bold")).pack(anchor="w")

        self.table = ttk.Treeview(
            table_frame,
            columns=("Ticker", "Price", "Original Run", "Growth%"),
            show="headings",
            selectmode="browse"
        )
        self.table.heading("Ticker", text="Ticker")
        self.table.heading("Price", text="Price")
        self.table.heading("Original Run", text="Original Run")
        self.table.heading("Growth%", text="Growth%")

        self.table.column("Ticker", width=90, anchor="w")
        self.table.column("Price", width=140, anchor="e")
        self.table.column("Original Run", width=160, anchor="w")
        self.table.column("Growth%", width=140, anchor="e")

        # Row background tags
        self.table.tag_configure("pos", background=ROW_POS_BG)
        self.table.tag_configure("neg", background=ROW_NEG_BG)
        self.table.tag_configure("neu", background=ROW_NEU_BG)
        self.table.tag_configure("na", background=ROW_NEU_BG)

        # scrollbar
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scroll.set)

        self.table.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _redraw_background(self):
        self.bg_canvas.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()

        # base fill
        self.bg_canvas.create_rectangle(0, 0, w, h, fill=OFFWHITE, outline="")

        # subtle gradient circle top-left
        base = _hex_to_rgb(OFFWHITE)
        bright = _hex_to_rgb(BRIGHTER)

        cx, cy = 40, 40
        max_r = 260
        steps = 26

        for i in range(steps, 0, -1):
            t = i / steps
            col = (
                _lerp(base[0], bright[0], t),
                _lerp(base[1], bright[1], t),
                _lerp(base[2], bright[2], t),
            )
            r = int(max_r * (i / steps))
            self.bg_canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=_rgb_to_hex(col), outline="")

    def _set_busy(self, busy: bool):
        state = "disabled" if busy else "normal"
        self.btn_scan.configure(state=state)
        self.btn_refresh.configure(state=state)
        self.config(cursor="watch" if busy else "")
        self.update_idletasks()

    def _clear_table(self):
        for item in self.table.get_children():
            self.table.delete(item)

    def _render_from_final_output_list(self, final_output_list):
        """
        final_output_list is exactly what your code returns: list of (ticker, stats_dict)
        stats_dict has keys: "Price", "Original Run", "Growth %"
        """
        self._clear_table()

        for ticker, stats in final_output_list:
            price = stats.get("Price", None)
            date = stats.get("Original Run", "")
            growth_str = stats.get("Growth %", None)

            growth_val = _parse_growth(growth_str)

            if growth_val is None:
                tag = "na"
                growth_display = "N/A"
            else:
                if abs(growth_val) < 0.01:
                    tag = "neu"
                elif growth_val > 0:
                    tag = "pos"
                else:
                    tag = "neg"
                growth_display = f"{growth_val:.2f}%"

            self.table.insert("", "end", values=(ticker, price, date, growth_display), tags=(tag,))

    def refresh_growth(self, auto=False):
        """
        Calls your get_growth_table() (NO reddit scan), then renders.
        """
        def worker():
            try:
                final_output_list, _df1 = get_growth_table()
                err = None
            except Exception as e:
                final_output_list = None
                err = str(e)

            def done():
                self._set_busy(False)
                if final_output_list is None:
                    messagebox.showerror("Error", err)
                    return
                if not final_output_list and not auto:
                    messagebox.showinfo("No data", "Database is empty. Run the Reddit scan first.")
                self._render_from_final_output_list(final_output_list)

            self.after(0, done)

        self._set_busy(True)
        threading.Thread(target=worker, daemon=True).start()

    def run_scan(self):
        """
        Calls your run_full_pipeline() (reddit scan + DB insert + then growth table), then renders.
        """
        def worker():
            try:
                final_output_list, _df1 = run_full_pipeline()
                err = None
            except Exception as e:
                final_output_list = None
                err = str(e)

            def done():
                self._set_busy(False)
                if final_output_list is None:
                    messagebox.showerror("Error", err)
                    return
                self._render_from_final_output_list(final_output_list)

            self.after(0, done)

        self._set_busy(True)
        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    App().mainloop()
