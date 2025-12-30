# app.py
import threading
import tkinter as tk
from tkinter import ttk, messagebox

# Uses your functions exactly as you defined them in main.py
from main import get_growth_table, run_full_pipeline

OFFWHITE = "#F6F4EF"
BRIGHTER = "#FFFDF8"
TEXT = "#222222"
GREY = "#7A7A7A"
GREEN = "#1F8F4A"
RED = "#B23A3A"


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
        style.configure("TButton", padding=10)

        style.configure(
            "Treeview",
            background=OFFWHITE,
            fieldbackground=OFFWHITE,
            foreground=TEXT,
            rowheight=28,
            borderwidth=0
        )
        style.configure("Treeview.Heading", background=OFFWHITE, foreground=TEXT)
        style.map("Treeview", background=[("selected", "#EAE6DD")])

    def _build_layout(self):
        # Left list panel
        left = ttk.Frame(self.root_frame)
        left.place(relx=0.03, rely=0.22, relwidth=0.24, relheight=0.64)

        ttk.Label(left, text="Tickers", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 8))

        self.ticker_list = ttk.Treeview(left, show="tree", selectmode="browse")
        self.ticker_list.pack(fill="both", expand=True)

        # Tag colors for left list
        self.ticker_list.tag_configure("pos", foreground=GREEN)
        self.ticker_list.tag_configure("neg", foreground=RED)
        self.ticker_list.tag_configure("neu", foreground=GREY)
        self.ticker_list.tag_configure("na", foreground=GREY)

        # Center buttons (2 buttons stacked)
        btn_frame = ttk.Frame(self.root_frame)
        btn_frame.place(relx=0.34, rely=0.12, relwidth=0.62, relheight=0.14)

        self.btn_scan = ttk.Button(btn_frame, text="Run Reddit Scan + Update", command=self.run_scan)
        self.btn_refresh = ttk.Button(btn_frame, text="Refresh Growth Table", command=self.refresh_growth)

        self.btn_scan.pack(pady=(0, 8))
        self.btn_refresh.pack()

        # Right table panel
        right = ttk.Frame(self.root_frame)
        right.place(relx=0.30, rely=0.28, relwidth=0.67, relheight=0.58)

        ttk.Label(right, text="Growth Table", font=("Helvetica", 14, "bold")).pack(anchor="w", pady=(0, 8))

        self.table = ttk.Treeview(
            right,
            columns=("Ticker", "Price", "Original Run", "Growth%"),
            show="headings",
            selectmode="browse"
        )
        self.table.heading("Ticker", text="Ticker")
        self.table.heading("Price", text="Price")
        self.table.heading("Original Run", text="Original Run")
        self.table.heading("Growth%", text="Growth%")

        self.table.column("Ticker", width=90, anchor="w")
        self.table.column("Price", width=120, anchor="e")
        self.table.column("Original Run", width=140, anchor="w")
        self.table.column("Growth%", width=140, anchor="e")

        self.table.pack(fill="both", expand=True)

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

    def _clear_views(self):
        for item in self.ticker_list.get_children():
            self.ticker_list.delete(item)
        for item in self.table.get_children():
            self.table.delete(item)

    def _render_from_final_output_list(self, final_output_list):
        """
        final_output_list is exactly what your code returns: list of (ticker, stats_dict)
        stats_dict has keys: "Price", "Original Run", "Growth %"
        """
        self._clear_views()

        for ticker, stats in final_output_list:
            price = stats.get("Price", None)
            date = stats.get("Original Run", "")
            growth_str = stats.get("Growth %", None)

            growth_val = _parse_growth(growth_str)
            if growth_val is None:
                tag = "na"
                growth_display = "N/A"
            else:
                # Neutral band: very close to 0%
                if abs(growth_val) < 0.01:
                    tag = "neu"
                elif growth_val > 0:
                    tag = "pos"
                else:
                    tag = "neg"

                growth_display = f"{growth_val:.2f}%"

            # Left list item: "TICKER   +x.xx%"
            display = f"{ticker: <6}  {growth_display}"
            self.ticker_list.insert("", "end", text=display, tags=(tag,))

            # Right table row
            self.table.insert("", "end", values=(ticker, price, date, growth_display))

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
