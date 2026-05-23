import ctypes
import math
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

from PIL import Image, ImageDraw, ImageOps, ImageTk


APP_NAME = "证件照排版工具"
APP_VERSION = "1.1"
REPO_URL = "https://github.com/sunchangqing666-ux/photo-layout-tool"
BASE_DIR = Path(__file__).resolve().parent
ICON_PATH = BASE_DIR / "assets" / "app.ico"
LOGO_PATH = BASE_DIR / "assets" / "logo.png"

DPI = 300
MARGIN = 30
GAP = 0
BACKGROUND = (255, 255, 255)
CROP_LINE = (77, 77, 77)
DEFAULT_CUSTOM_PAPER_MM = (89, 127)
SYSTEM_DEFAULT_PRINTER = "系统默认打印机"

APP_BG = "#F6F0FF"
PANEL_BG = "#FBFDFF"
PREVIEW_BG = "#F8FBFF"
TEXT = "#172033"
MUTED = "#667085"
BORDER = "#FFFFFF"
PRIMARY = "#7C3AED"
PRIMARY_HOVER = "#6D28D9"
SUCCESS = "#14B8A6"
SUCCESS_HOVER = "#0F9F90"
NEUTRAL = "#F6F8FF"
NEUTRAL_HOVER = "#EEF2FF"
PINK = "#EC4899"
CYAN = "#38BDF8"
GLASS_SHADOW = "#D9D4F1"

ID_SIZES = {
    "一寸": (25, 35),
    "二寸": (35, 49),
}

ID_PIXEL_SIZES = {
    "一寸": (295, 413),
    "二寸": (413, 578),
}

PAPER_SIZES = {
    "5寸": (89, 127),
    "6寸": (102, 152),
    "自定义": DEFAULT_CUSTOM_PAPER_MM,
}

PAPER_PIXEL_SIZES = {
    "5寸": (1050, 1500),
    "6寸": (1200, 1800),
}

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text,
        command,
        bg=PRIMARY,
        fg="#FFFFFF",
        hover=PRIMARY_HOVER,
        active_fg="#FFFFFF",
        width=108,
        height=42,
        radius=18,
        font=("Microsoft YaHei UI", 10, "bold"),
    ):
        super().__init__(parent, width=width, height=height, bg=PANEL_BG, highlightthickness=0, cursor="hand2")
        self.text = text
        self.command = command
        self.default_bg = bg
        self.hover_bg = hover
        self.default_fg = fg
        self.hover_fg = active_fg
        self.radius = radius
        self.button_height = height
        self.button_font = font
        self.current_bg = bg
        self.current_fg = fg

        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<Enter>", lambda _event: self._set_hover(True))
        self.bind("<Leave>", lambda _event: self._set_hover(False))
        self.bind("<Button-1>", lambda _event: self.command())
        self._draw()

    def set_colors(self, bg, fg, hover, active_fg=None):
        self.default_bg = bg
        self.hover_bg = hover
        self.default_fg = fg
        self.hover_fg = active_fg if active_fg is not None else fg
        self.current_bg = bg
        self.current_fg = fg
        self._draw()

    def _set_hover(self, hovered):
        self.current_bg = self.hover_bg if hovered else self.default_bg
        self.current_fg = self.hover_fg if hovered else self.default_fg
        self._draw()

    def _draw(self):
        self.delete("all")
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        radius = min(self.radius, width // 2, height // 2)
        self._round_rect(1, 1, width - 1, height - 1, radius, fill=self.current_bg, outline="#FFFFFF")
        self.create_text(width / 2, height / 2, text=self.text, fill=self.current_fg, font=self.button_font)

    def _round_rect(self, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return self.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


def mm_to_px(mm):
    return int(round(mm / 25.4 * DPI))


def size_to_px(size_mm):
    return mm_to_px(size_mm[0]), mm_to_px(size_mm[1])


def enable_dpi_awareness():
    if not sys.platform.startswith("win"):
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def load_printers():
    if not sys.platform.startswith("win"):
        return []
    try:
        import win32print

        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return [printer[2] for printer in win32print.EnumPrinters(flags)]
    except Exception:
        return []


class PhotoLayoutTool(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        if ICON_PATH.exists():
            try:
                self.iconbitmap(str(ICON_PATH))
            except tk.TclError:
                pass

        self.geometry("1080x760")
        self.minsize(1000, 700)
        self.configure(bg=APP_BG)

        self.source_path = None
        self.source_image = None
        self.layout_image = None
        self.preview_photo = None
        self.layout_stats = None
        self.batch_items = []
        self.preview_index = 0
        self.preview_draw_after = None
        self.drop_after = None
        self.logo_photo = None
        self.switches = {}

        self.is_topmost = tk.BooleanVar(value=False)
        self.crop_lines = tk.BooleanVar(value=True)
        self.auto_save = tk.BooleanVar(value=True)
        self.id_size_name = tk.StringVar(value="二寸")
        self.paper_name = tk.StringVar(value="5寸")
        self.custom_w = tk.StringVar(value=str(DEFAULT_CUSTOM_PAPER_MM[0]))
        self.custom_h = tk.StringVar(value=str(DEFAULT_CUSTOM_PAPER_MM[1]))
        self.printer_name = tk.StringVar(value="")

        self._setup_styles()
        self._build_ui()
        self._setup_drag_drop()
        self._refresh_printers()
        self._update_preview()

    def _setup_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=PANEL_BG)
        style.configure("Panel.TFrame", background=PANEL_BG)
        style.configure("TLabel", background=PANEL_BG, foreground=TEXT, font=("Microsoft YaHei UI", 10))
        style.configure("Muted.TLabel", background=PANEL_BG, foreground=MUTED, font=("Microsoft YaHei UI", 10))
        style.configure("Title.TLabel", background=PANEL_BG, foreground=TEXT, font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("Section.TLabel", background=PANEL_BG, foreground=TEXT, font=("Microsoft YaHei UI", 11, "bold"))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=(10, 7))
        style.configure("TEntry", padding=(8, 4))
        style.configure("TCombobox", padding=(8, 4))
        style.configure("TCheckbutton", background=PANEL_BG, foreground=TEXT, font=("Microsoft YaHei UI", 10))
        style.map("TCheckbutton", background=[("active", PANEL_BG)], foreground=[("active", TEXT)])

    def _build_ui(self):
        self.bg_canvas = tk.Canvas(self, bg=APP_BG, highlightthickness=0)
        self.bg_canvas.pack(fill=tk.BOTH, expand=True)
        self.bg_canvas.bind("<Configure>", self._layout_glass_panels)

        self.left_shell = tk.Frame(self.bg_canvas, bg=PANEL_BG, highlightbackground=BORDER, highlightthickness=1)
        self.left_canvas = tk.Canvas(self.left_shell, bg=PANEL_BG, highlightthickness=0)
        self.left_scrollbar = ttk.Scrollbar(self.left_shell, orient=tk.VERTICAL, command=self.left_canvas.yview)
        self.left_canvas.configure(yscrollcommand=self.left_scrollbar.set)
        self.left_scrollbar_visible = True
        self.left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.left = ttk.Frame(self.left_canvas, padding=14, style="Panel.TFrame")
        self.left_content_window = self.left_canvas.create_window(0, 0, window=self.left, anchor=tk.NW)
        self.left.bind("<Configure>", self._update_left_scroll_region)
        self.left_canvas.bind("<Configure>", self._fit_left_content_width)
        self.left_canvas.bind("<MouseWheel>", self._on_left_wheel)
        self.left.bind("<MouseWheel>", self._on_left_wheel)

        self.right_shell = tk.Frame(self.bg_canvas, bg=PANEL_BG, highlightbackground=BORDER, highlightthickness=1)
        self.right = ttk.Frame(self.right_shell, padding=20, style="Panel.TFrame")
        self.right.pack(fill=tk.BOTH, expand=True)

        self.left_window = self.bg_canvas.create_window(20, 20, window=self.left_shell, anchor=tk.NW)
        self.right_window = self.bg_canvas.create_window(400, 20, window=self.right_shell, anchor=tk.NW)

        self._build_left_panel()
        self._build_right_panel()

    def _update_left_scroll_region(self, _event=None):
        bbox = self.left_canvas.bbox("all")
        self.left_canvas.configure(scrollregion=bbox)
        if not bbox:
            return

        content_h = bbox[3] - bbox[1]
        canvas_h = max(1, self.left_canvas.winfo_height())
        needs_scroll = content_h > canvas_h + 2
        if needs_scroll and not self.left_scrollbar_visible:
            self.left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.left_scrollbar_visible = True
        elif not needs_scroll and self.left_scrollbar_visible:
            self.left_scrollbar.pack_forget()
            self.left_scrollbar_visible = False
            self.left_canvas.yview_moveto(0)

    def _fit_left_content_width(self, event):
        self.left_canvas.itemconfigure(self.left_content_window, width=event.width)
        self.after_idle(self._update_left_scroll_region)

    def _on_left_wheel(self, event):
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = int(-1 * (event.delta / 120))
        self.left_canvas.yview_scroll(delta, "units")
        return "break"

    def _layout_glass_panels(self, event):
        width = max(event.width, 940)
        height = max(event.height, 620)
        margin = 18
        gap = 16
        left_w = 360
        panel_h = max(1, height - margin * 2)
        right_x = margin + left_w + gap
        right_w = max(1, width - right_x - margin)

        self.bg_canvas.delete("bg")
        self.bg_canvas.delete("panel_shadow")
        self._draw_fast_background(width, height)

        for x, w in ((margin, left_w), (right_x, right_w)):
            self.bg_canvas.create_rectangle(
                x + 8,
                margin + 10,
                x + w + 8,
                margin + panel_h + 10,
                fill=GLASS_SHADOW,
                outline="",
                stipple="gray50",
                tags="panel_shadow",
            )
            self.bg_canvas.create_rectangle(
                x,
                margin,
                x + w,
                margin + panel_h,
                outline="#FFFFFF",
                width=1,
                tags="panel_shadow",
            )
        self.bg_canvas.tag_raise("panel_shadow", "bg")
        self.bg_canvas.tag_raise(self.left_window)
        self.bg_canvas.tag_raise(self.right_window)
        self.bg_canvas.coords(self.left_window, margin, margin)
        self.bg_canvas.itemconfigure(self.left_window, width=left_w, height=panel_h)
        self.bg_canvas.coords(self.right_window, right_x, margin)
        self.bg_canvas.itemconfigure(self.right_window, width=right_w, height=panel_h)

    def _draw_fast_background(self, width, height):
        top = self._hex_to_rgb("#EAF8FF")
        middle = self._hex_to_rgb("#F3E8FF")
        bottom = self._hex_to_rgb("#FFEAF4")
        bands = 28
        band_h = max(1, math.ceil(height / bands))

        for index in range(bands):
            t = index / max(1, bands - 1)
            if t < 0.55:
                local = t / 0.55
                start, end = top, middle
            else:
                local = (t - 0.55) / 0.45
                start, end = middle, bottom
            color = self._rgb_to_hex(tuple(int(start[i] * (1 - local) + end[i] * local) for i in range(3)))
            y = index * band_h
            self.bg_canvas.create_rectangle(0, y, width, y + band_h + 1, fill=color, outline="", tags="bg")

        self.bg_canvas.create_oval(
            -width * 0.08,
            -height * 0.16,
            width * 0.34,
            height * 0.42,
            fill="#DFF4FF",
            outline="",
            tags="bg",
        )
        self.bg_canvas.create_oval(
            width * 0.56,
            -height * 0.2,
            width * 1.08,
            height * 0.46,
            fill="#F3D7FF",
            outline="",
            tags="bg",
        )
        self.bg_canvas.create_oval(
            width * 0.68,
            height * 0.58,
            width * 1.08,
            height * 1.14,
            fill="#FFE0F0",
            outline="",
            tags="bg",
        )
        self.bg_canvas.create_oval(
            width * 0.12,
            height * 0.72,
            width * 0.42,
            height * 1.12,
            fill="#E5EEFF",
            outline="",
            tags="bg",
        )
        self.bg_canvas.tag_lower("bg")

    def _build_left_panel(self):
        logo_row = ttk.Frame(self.left)
        logo_row.pack(fill=tk.X, pady=(0, 12))
        self.logo_photo = self._load_logo_photo(46)
        if self.logo_photo:
            tk.Label(logo_row, image=self.logo_photo, bg=PANEL_BG, bd=0).pack(side=tk.LEFT, padx=(0, 12))

        title_box = ttk.Frame(logo_row)
        title_box.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            title_box,
            text=APP_NAME,
            bg=PANEL_BG,
            fg=TEXT,
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor=tk.W)
        self._gradient_strip(title_box, 68, 4).pack(anchor=tk.W, pady=(4, 4))
        ttk.Label(title_box, text="证件照自动排版与打印", style="Muted.TLabel").pack(anchor=tk.W)

        self.upload_box = tk.Frame(
            self.left,
            bg="#F8FBFF",
            highlightbackground="#93C5FD",
            highlightthickness=1,
            height=132,
            cursor="hand2",
        )
        self.upload_box.pack(fill=tk.X, pady=(0, 12))
        self.upload_box.pack_propagate(False)
        self.upload_box.bind("<Button-1>", lambda _event: self.choose_file())
        self.upload_content = tk.Frame(self.upload_box, bg="#F8FBFF", cursor="hand2")
        self.upload_content.pack(fill=tk.BOTH, expand=True)
        self.upload_content.bind("<Button-1>", lambda _event: self.choose_file())
        self.upload_icon = tk.Label(
            self.upload_content,
            text="+",
            bg="#F8FBFF",
            fg=PRIMARY,
            font=("Microsoft YaHei UI", 28, "bold"),
            cursor="hand2",
        )
        self.upload_icon.pack(pady=(14, 0))
        self.upload_title = tk.Label(
            self.upload_content,
            text="点击或拖拽上传证件照",
            bg="#F8FBFF",
            fg=TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
            wraplength=260,
            justify=tk.CENTER,
            cursor="hand2",
        )
        self.upload_title.pack(pady=(4, 0))
        self.upload_hint = tk.Label(
            self.upload_content,
            text="JPG / PNG / BMP / TIFF",
            bg="#F8FBFF",
            fg=MUTED,
            font=("Microsoft YaHei UI", 9),
            cursor="hand2",
        )
        self.upload_hint.pack(pady=(4, 0))
        for widget in (self.upload_icon, self.upload_title, self.upload_hint, self.upload_content):
            widget.bind("<Button-1>", lambda _event: self.choose_file())

        self._solid_button(self.left, "批量排版", self.choose_batch_files, bg=PRIMARY, hover=PRIMARY_HOVER).pack(
            fill=tk.X, pady=(0, 12)
        )

        self.file_label = ttk.Label(self.left, text="", style="Muted.TLabel", wraplength=340)
        self.status_label = ttk.Label(self.left, text="", style="Muted.TLabel", wraplength=340)

        self._section("证件尺寸")
        self.id_button_frame = ttk.Frame(self.left)
        self.id_button_frame.pack(fill=tk.X, pady=(0, 12))
        self.id_buttons = {}
        for name in ID_SIZES:
            self.id_buttons[name] = self._pill_button(self.id_button_frame, name, lambda n=name: self._select_id_size(n))

        self._section("相纸设置")
        self.paper_button_frame = ttk.Frame(self.left)
        self.paper_button_frame.pack(fill=tk.X, pady=(0, 10))
        self.paper_buttons = {}
        for name in PAPER_SIZES:
            self.paper_buttons[name] = self._pill_button(
                self.paper_button_frame, name, lambda n=name: self._select_paper(n)
            )

        self.custom_frame = ttk.Frame(self.left)
        self.custom_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(self.custom_frame, text="宽").pack(side=tk.LEFT)
        self.custom_w_entry = ttk.Entry(self.custom_frame, width=7, textvariable=self.custom_w)
        self.custom_w_entry.pack(side=tk.LEFT, padx=(6, 8))
        ttk.Label(self.custom_frame, text="mm   高").pack(side=tk.LEFT)
        self.custom_h_entry = ttk.Entry(self.custom_frame, width=7, textvariable=self.custom_h)
        self.custom_h_entry.pack(side=tk.LEFT, padx=(6, 8))
        ttk.Label(self.custom_frame, text="mm").pack(side=tk.LEFT)
        for var in (self.custom_w, self.custom_h):
            var.trace_add("write", lambda *_args: self._update_preview())

        crop_row = ttk.Frame(self.left)
        crop_row.pack(fill=tk.X, pady=(2, 10))
        ttk.Label(crop_row, text="裁切角线").pack(side=tk.LEFT)
        self.crop_switch = self._switch(crop_row, self.crop_lines, self._update_preview)
        self.crop_switch.pack(side=tk.RIGHT)
        crop_row.bind("<Button-1>", lambda _event: self._toggle_switch(self.crop_lines, self._update_preview))

        auto_row = ttk.Frame(self.left)
        auto_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(auto_row, text="自动保存").pack(side=tk.LEFT)
        self.auto_save_switch = self._switch(auto_row, self.auto_save, self._update_auto_save_status)
        self.auto_save_switch.pack(side=tk.RIGHT)
        auto_row.bind("<Button-1>", lambda _event: self._toggle_switch(self.auto_save, self._update_auto_save_status))

        printer_row = ttk.Frame(self.left)
        printer_row.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(printer_row, text="打印机").pack(anchor=tk.W, pady=(0, 6))
        self.printer_combo = ttk.Combobox(printer_row, textvariable=self.printer_name, state="readonly")
        self.printer_combo.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self._solid_button(
            printer_row,
            "刷新",
            self._refresh_printers,
            bg=NEUTRAL,
            fg="#334155",
            hover=NEUTRAL_HOVER,
            active_fg="#0F172A",
        ).pack(side=tk.LEFT, padx=(8, 0))

        printer_actions = ttk.Frame(self.left)
        printer_actions.pack(fill=tk.X)
        self._solid_button(
            printer_actions,
            "打印机属性",
            self.open_printer_settings,
            bg=NEUTRAL,
            fg="#334155",
            hover=NEUTRAL_HOVER,
            active_fg="#0F172A",
        ).pack(side=tk.LEFT)

        self._refresh_toggle_buttons()
        self._bind_left_wheel_recursive(self.left)

    def _load_logo_photo(self, size):
        if not LOGO_PATH.exists():
            return None
        try:
            with Image.open(LOGO_PATH) as image:
                image = ImageOps.contain(image.convert("RGBA"), (size, size), method=Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
            x = (size - image.width) // 2
            y = (size - image.height) // 2
            canvas.alpha_composite(image, (x, y))
            return ImageTk.PhotoImage(canvas)
        except Exception:
            return None

    def _bind_left_wheel_recursive(self, widget):
        widget.bind("<MouseWheel>", self._on_left_wheel)
        widget.bind("<Button-4>", self._on_left_wheel)
        widget.bind("<Button-5>", self._on_left_wheel)
        for child in widget.winfo_children():
            self._bind_left_wheel_recursive(child)

    def _build_right_panel(self):
        title_row = ttk.Frame(self.right)
        title_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(title_row, text="排版预览", style="Title.TLabel").pack(side=tk.LEFT)

        self.topmost_button = self._solid_button(
            title_row,
            "置顶",
            self.toggle_topmost,
            bg=NEUTRAL,
            fg="#334155",
            hover=NEUTRAL_HOVER,
            active_fg="#0F172A",
            padx=14,
            pady=8,
        )
        self.topmost_button.pack(side=tk.RIGHT)
        self._solid_button(
            title_row,
            "开源地址",
            self.open_project_home,
            bg=NEUTRAL,
            fg="#334155",
            hover=NEUTRAL_HOVER,
            active_fg="#0F172A",
            padx=14,
            pady=8,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        self._solid_button(
            title_row,
            "清除",
            self.clear_all,
            bg=NEUTRAL,
            fg="#334155",
            hover=NEUTRAL_HOVER,
            active_fg="#0F172A",
            padx=14,
            pady=8,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        self._solid_button(
            title_row,
            "开始打印",
            self.print_layout,
            bg=SUCCESS,
            hover=SUCCESS_HOVER,
            padx=18,
            pady=8,
        ).pack(side=tk.RIGHT, padx=(0, 10))
        self._solid_button(
            title_row,
            "保存排版",
            self.save_layout,
            bg=PRIMARY,
            hover=PRIMARY_HOVER,
            padx=18,
            pady=8,
        ).pack(side=tk.RIGHT, padx=(0, 10))

        self.stats_label = ttk.Label(self.right, text="", style="Muted.TLabel")
        self.stats_label.pack(fill=tk.X, pady=(0, 12))

        self.preview_frame = tk.Frame(self.right, bg=PREVIEW_BG, highlightbackground=BORDER, highlightthickness=1)
        self.preview_frame.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas = tk.Canvas(self.preview_frame, bg=PREVIEW_BG, highlightthickness=0)
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.preview_canvas.bind("<Configure>", self._schedule_draw_preview)
        self.preview_canvas.bind("<MouseWheel>", self._on_preview_wheel)
        self.preview_canvas.bind("<Button-4>", self._on_preview_wheel)
        self.preview_canvas.bind("<Button-5>", self._on_preview_wheel)
        self.preview_frame.bind("<MouseWheel>", self._on_preview_wheel)
        self.preview_frame.bind("<Button-4>", self._on_preview_wheel)
        self.preview_frame.bind("<Button-5>", self._on_preview_wheel)
        self._style_topmost_button()

    def _section(self, text):
        ttk.Label(self.left, text=text, style="Section.TLabel").pack(anchor=tk.W, pady=(2, 8))

    def _gradient_strip(self, parent, width, height):
        canvas = tk.Canvas(parent, width=width, height=height, bg=PANEL_BG, highlightthickness=0)
        colors = ("#38BDF8", "#7C3AED", "#EC4899")
        for x in range(width):
            t = x / max(1, width - 1)
            if t < 0.5:
                local = t / 0.5
                start = self._hex_to_rgb(colors[0])
                end = self._hex_to_rgb(colors[1])
            else:
                local = (t - 0.5) / 0.5
                start = self._hex_to_rgb(colors[1])
                end = self._hex_to_rgb(colors[2])
            color = self._rgb_to_hex(tuple(int(start[i] * (1 - local) + end[i] * local) for i in range(3)))
            canvas.create_line(x, 0, x, height, fill=color)
        return canvas

    def _hex_to_rgb(self, value):
        value = value.lstrip("#")
        return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))

    def _rgb_to_hex(self, rgb):
        return "#{:02X}{:02X}{:02X}".format(*rgb)

    def _solid_button(
        self,
        parent,
        text,
        command,
        bg=PRIMARY,
        fg="#FFFFFF",
        hover=PRIMARY_HOVER,
        active_fg="#FFFFFF",
        padx=18,
        pady=9,
    ):
        width = max(86, len(text) * 18 + padx * 2)
        height = max(38, pady * 2 + 24)
        return RoundedButton(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            hover=hover,
            active_fg=active_fg,
            width=width,
            height=height,
            radius=10,
        )

    def _switch(self, parent, variable, command):
        canvas = tk.Canvas(parent, width=52, height=26, bg=PANEL_BG, highlightthickness=0, cursor="hand2")
        canvas.variable = variable
        canvas.command = command
        canvas.bind("<Button-1>", lambda event: self._toggle_switch(event.widget.variable, event.widget.command))
        self.switches[str(variable)] = canvas
        self._draw_switch(variable)
        return canvas

    def _toggle_switch(self, variable, command):
        variable.set(not variable.get())
        self._draw_switch(variable)
        command()
        return "break"

    def _refresh_switches(self):
        self._draw_switch(self.crop_lines)
        self._draw_switch(self.auto_save)

    def _draw_switch(self, variable):
        canvas = self.switches.get(str(variable))
        if not canvas:
            return
        canvas.delete("all")
        enabled = variable.get()
        track = PRIMARY if enabled else "#E2E8F0"
        outline = "#A78BFA" if enabled else "#CBD5E1"
        knob = "#FFFFFF"
        self._canvas_round_rect(canvas, 1, 2, 51, 24, 7, fill=track, outline=outline, width=1)
        x = 29 if enabled else 4
        self._canvas_round_rect(canvas, x, 5, x + 18, 21, 5, fill=knob, outline="")

    def _canvas_round_rect(self, canvas, x1, y1, x2, y2, radius, **kwargs):
        points = [
            x1 + radius,
            y1,
            x2 - radius,
            y1,
            x2,
            y1,
            x2,
            y1 + radius,
            x2,
            y2 - radius,
            x2,
            y2,
            x2 - radius,
            y2,
            x1 + radius,
            y2,
            x1,
            y2,
            x1,
            y2 - radius,
            x1,
            y1 + radius,
            x1,
            y1,
        ]
        return canvas.create_polygon(points, smooth=True, splinesteps=12, **kwargs)

    def _pill_button(self, parent, text, command):
        button = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Microsoft YaHei UI", 10),
            bd=0,
            relief=tk.FLAT,
            padx=18,
            pady=8,
            cursor="hand2",
        )
        button.pack(side=tk.LEFT, padx=(0, 8))
        return button

    def _setup_drag_drop(self):
        try:
            import windnd

            drop_targets = [
                self,
                self.bg_canvas,
                self.left_shell,
                self.right_shell,
                self.left_canvas,
                self.left,
                self.right,
            ]
            for name in ("upload_box", "preview_frame", "preview_canvas"):
                widget = getattr(self, name, None)
                if widget is not None:
                    drop_targets.append(widget)

            for widget in dict.fromkeys(drop_targets):
                try:
                    windnd.hook_dropfiles(widget, func=self._on_drop_files)
                except Exception:
                    pass
        except Exception:
            return

    def _all_widgets(self, widget):
        yield widget
        for child in widget.winfo_children():
            yield from self._all_widgets(child)

    def _on_drop_files(self, files):
        if not files:
            return
        paths = [self._decode_drop_path(file) for file in files]
        paths = [path for path in paths if Path(path).suffix.lower() in SUPPORTED_EXTS]
        if not paths:
            self.after(10, lambda: self._set_status("请拖入 JPG / PNG / BMP / TIFF 图片。"))
            return
        if self.drop_after is not None:
            try:
                self.after_cancel(self.drop_after)
            except tk.TclError:
                pass
        self.drop_after = self.after(80, lambda p=paths: self._run_dropped_files(p))

    def _run_dropped_files(self, paths):
        self.drop_after = None
        self.batch_layout_files(paths, append=True)

    def _decode_drop_path(self, file):
        return file.decode("gbk", errors="ignore") if isinstance(file, bytes) else str(file)

    def choose_file(self):
        path = filedialog.askopenfilename(
            title="选择证件照",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"),
                ("所有文件", "*.*"),
            ],
        )
        if path:
            self.open_image(path)

    def choose_batch_files(self):
        paths = filedialog.askopenfilenames(
            title="选择需要批量排版的证件照",
            filetypes=[
                ("图片文件", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff"),
                ("所有文件", "*.*"),
            ],
        )
        if paths:
            self.batch_layout_files(paths, append=False)

    def open_image(self, path):
        try:
            image = self._load_source_image(path)
        except Exception as exc:
            messagebox.showerror("无法打开图片", f"图片无法打开：{exc}")
            return

        self.batch_items = []
        self.preview_index = 0
        self.source_path = Path(path)
        self.source_image = image
        self.file_label.configure(text=f"{self.source_path.name}\n{image.width} x {image.height} px")
        self._set_status("单张模式：可保存当前预览或直接打印。")
        self._update_preview()

    def _load_source_image(self, path):
        path = Path(path)
        if path.suffix.lower() not in SUPPORTED_EXTS:
            raise ValueError("请选择 JPG、PNG、BMP 或 TIFF 图片。")
        try:
            with Image.open(path) as image:
                return ImageOps.exif_transpose(image).convert("RGB")
        except Exception as exc:
            raise ValueError(f"图片无法打开：{exc}") from exc

    def _select_id_size(self, name):
        self.id_size_name.set(name)
        self._refresh_toggle_buttons()
        self._update_preview()

    def _select_paper(self, name):
        self.paper_name.set(name)
        self._refresh_toggle_buttons()
        self._update_preview()

    def _refresh_toggle_buttons(self):
        for name, button in self.id_buttons.items():
            self._style_pill(button, selected=name == self.id_size_name.get())
        for name, button in self.paper_buttons.items():
            self._style_pill(button, selected=name == self.paper_name.get())
        state = tk.NORMAL if self.paper_name.get() == "自定义" else tk.DISABLED
        self.custom_w_entry.configure(state=state)
        self.custom_h_entry.configure(state=state)
        self._refresh_switches()

    def _style_pill(self, button, selected=False):
        if selected:
            button.configure(bg="#E0F2FE", fg="#075985", activebackground="#BAE6FD", activeforeground="#075985")
        else:
            button.configure(bg=NEUTRAL, fg="#334155", activebackground=NEUTRAL_HOVER, activeforeground="#0F172A")

    def _set_status(self, text):
        if hasattr(self, "status_label"):
            self.status_label.configure(text=text)

    def _update_auto_save_status(self):
        if self.auto_save.get():
            self._set_status("自动保存已开启：拖入或批量选择后会写入 JPEG。")
        else:
            self._set_status("自动保存已关闭：只排版预览和打印，不自动写入文件。")

    def _paper_size_mm(self):
        if self.paper_name.get() != "自定义":
            return PAPER_SIZES[self.paper_name.get()]
        try:
            width = float(self.custom_w.get())
            height = float(self.custom_h.get())
            if width < 10 or height < 10:
                raise ValueError
            return width, height
        except Exception:
            return DEFAULT_CUSTOM_PAPER_MM

    def _paper_size_px(self):
        if self.paper_name.get() in PAPER_PIXEL_SIZES:
            return PAPER_PIXEL_SIZES[self.paper_name.get()]
        return size_to_px(self._paper_size_mm())

    def _update_preview(self):
        if self.batch_items:
            self._show_batch_preview(self.preview_index)
            return

        if self.source_image is None:
            self.layout_image = None
            self.layout_stats = None
            if hasattr(self, "stats_label"):
                self.stats_label.configure(text="")
            if hasattr(self, "preview_canvas"):
                self._draw_preview()
            return
        try:
            self.layout_image, self.layout_stats = self.generate_layout()
            self._draw_preview()
        except Exception as exc:
            self.layout_image = None
            self.layout_stats = None
            self.stats_label.configure(text="")
            messagebox.showerror("排版失败", str(exc))

    def generate_layout(self):
        canvas, stats = self._generate_layout_for_image(self.source_image)
        self._update_stats_label(stats)
        return canvas, stats

    def _generate_layout_for_image(self, source_image):
        id_name = self.id_size_name.get()
        id_mm = ID_SIZES[id_name]
        paper_mm = self._paper_size_mm()
        photo_w, photo_h = ID_PIXEL_SIZES[id_name]
        paper_w, paper_h = self._paper_size_px()

        candidates = []
        for oriented_w, oriented_h, rotate in ((photo_w, photo_h, False), (photo_h, photo_w, True)):
            cols = max(0, (paper_w - MARGIN * 2 + GAP) // (oriented_w + GAP))
            rows = max(0, (paper_h - MARGIN * 2 + GAP) // (oriented_h + GAP))
            candidates.append((cols * rows, cols, rows, oriented_w, oriented_h, rotate))
        count, cols, rows, slot_w, slot_h, rotate = max(candidates, key=lambda item: item[0])

        if count <= 0:
            raise ValueError("当前相纸尺寸无法放下所选证件照。")

        canvas = Image.new("RGB", (paper_w, paper_h), BACKGROUND)
        photo = ImageOps.fit(source_image, (photo_w, photo_h), method=Image.Resampling.LANCZOS)
        if rotate:
            photo = photo.rotate(90, expand=True)

        layout_w = cols * slot_w + max(0, cols - 1) * GAP
        layout_h = rows * slot_h + max(0, rows - 1) * GAP
        start_x = int((paper_w - layout_w) / 2)
        start_y = int((paper_h - layout_h) / 2)

        for row in range(rows):
            for col in range(cols):
                x = start_x + col * (slot_w + GAP)
                y = start_y + row * (slot_h + GAP)
                canvas.paste(photo, (x, y))

        if self.crop_lines.get():
            self._draw_crop_lines(canvas, start_x, start_y, cols, rows, slot_w, slot_h)

        stats = {
            "cols": cols,
            "rows": rows,
            "count": count,
            "paper_mm": paper_mm,
            "id_mm": id_mm,
            "paper_px": (paper_w, paper_h),
            "photo_px": (slot_w, slot_h),
            "rotated": rotate,
        }
        return canvas, stats

    def _update_stats_label(self, stats, prefix=""):
        paper_mm = stats["paper_mm"]
        id_mm = stats["id_mm"]
        self.stats_label.configure(
            text=(
                f"{prefix}{stats['cols']} x {stats['rows']} = {stats['count']} 张 | "
                f"{paper_mm[0]:g}x{paper_mm[1]:g}mm  {id_mm[0]}x{id_mm[1]}mm"
            )
        )

    def _draw_crop_lines(self, canvas, start_x, start_y, cols, rows, slot_w, slot_h):
        draw = ImageDraw.Draw(canvas)
        width, height = canvas.size
        xs = [start_x + i * (slot_w + GAP) for i in range(cols)]
        xs.append(start_x + cols * slot_w + max(0, cols - 1) * GAP)
        ys = [start_y + i * (slot_h + GAP) for i in range(rows)]
        ys.append(start_y + rows * slot_h + max(0, rows - 1) * GAP)

        for x in xs:
            self._dashed_line(draw, (x, 0), (x, height), fill=CROP_LINE)
        for y in ys:
            self._dashed_line(draw, (0, y), (width, y), fill=CROP_LINE)

    def _dashed_line(self, draw, start, end, fill):
        x1, y1 = start
        x2, y2 = end
        length = math.hypot(x2 - x1, y2 - y1)
        if length == 0:
            return

        dx = (x2 - x1) / length
        dy = (y2 - y1) / length
        pos = 0
        while pos < length:
            seg_end = min(pos + 6, length)
            draw.line(
                (
                    x1 + dx * pos,
                    y1 + dy * pos,
                    x1 + dx * seg_end,
                    y1 + dy * seg_end,
                ),
                fill=fill,
                width=1,
            )
            pos += 9

    def _schedule_draw_preview(self, _event=None):
        if self.preview_draw_after is not None:
            try:
                self.after_cancel(self.preview_draw_after)
            except tk.TclError:
                pass
        self.preview_draw_after = self.after(70, self._draw_preview)

    def _draw_preview(self):
        self.preview_draw_after = None
        self.preview_canvas.delete("all")
        canvas_w = self.preview_canvas.winfo_width()
        canvas_h = self.preview_canvas.winfo_height()
        if canvas_w < 10 or canvas_h < 10:
            return

        if self.layout_image is None:
            self.preview_canvas.create_text(
                canvas_w / 2,
                canvas_h / 2,
                text="上传证件照后显示排版预览",
                fill="#94A3B8",
                font=("Microsoft YaHei UI", 14),
            )
            return

        scale = min((canvas_w * 0.9) / self.layout_image.width, (canvas_h * 0.9) / self.layout_image.height)
        preview_size = (max(1, int(self.layout_image.width * scale)), max(1, int(self.layout_image.height * scale)))
        preview = self.layout_image.resize(preview_size, Image.Resampling.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(preview)
        x = canvas_w // 2
        y = canvas_h // 2
        self.preview_canvas.create_rectangle(
            x - preview_size[0] / 2 - 1,
            y - preview_size[1] / 2 - 1,
            x + preview_size[0] / 2 + 1,
            y + preview_size[1] / 2 + 1,
            outline=BORDER,
            fill=PANEL_BG,
        )
        self.preview_canvas.create_image(x, y, image=self.preview_photo)

    def _refresh_printers(self):
        printers = load_printers()
        if printers:
            self.printer_combo.configure(values=printers)
            if not self.printer_name.get() or self.printer_name.get() == SYSTEM_DEFAULT_PRINTER:
                self.printer_name.set(printers[0])
            return

        self.printer_name.set(SYSTEM_DEFAULT_PRINTER)
        self.printer_combo.configure(values=[SYSTEM_DEFAULT_PRINTER])

    def _default_output_path(self):
        source_path = self.source_path if self.source_path else Path.cwd() / "photo.jpg"
        return self._output_path_for_source(source_path)

    def _output_path_for_source(self, source_path):
        source_path = Path(source_path)
        base_dir = source_path.parent
        stem = source_path.stem
        paper = self.paper_name.get()
        if paper == "自定义":
            paper_mm = self._paper_size_mm()
            paper = f"{paper_mm[0]:g}x{paper_mm[1]:g}mm"

        name = f"{stem}_{self.id_size_name.get()}_{paper}排版.jpg"
        path = base_dir / name
        index = 1
        while path.exists():
            path = base_dir / f"{Path(name).stem}_{index}.jpg"
            index += 1
        return path

    def batch_layout_files(self, paths, append=False):
        saved = []
        failures = []
        batch_items = list(self.batch_items) if append else []
        first_preview = None
        processed = 0
        auto_save = self.auto_save.get()

        for path in paths:
            source_path = Path(path)
            try:
                image = self._load_source_image(source_path)
                layout, stats = self._generate_layout_for_image(image)
                output_path = None
                if auto_save:
                    output_path = self._output_path_for_source(source_path)
                    layout.save(output_path, "JPEG", quality=95, dpi=(DPI, DPI), optimize=True)
                    saved.append(output_path)
                item = {
                    "source_path": source_path,
                    "output_path": output_path,
                    "layout_image": layout,
                    "stats": stats,
                    "image_size": (image.width, image.height),
                }
                batch_items.append(item)
                processed += 1
                if first_preview is None:
                    first_preview = item
            except Exception as exc:
                failures.append(f"{source_path.name}: {exc}")

        self.batch_items = batch_items
        if processed:
            self.preview_index = len(self.batch_items) - processed
            self._show_batch_preview(self.preview_index)

        self._show_batch_result(processed, saved, failures, auto_save)

    def _show_batch_preview(self, index):
        if not self.batch_items:
            return

        self.preview_index = index % len(self.batch_items)
        item = self.batch_items[self.preview_index]
        source_path = item["source_path"]
        image_w, image_h = item["image_size"]

        self.source_path = source_path
        self.source_image = None
        self.layout_image = item["layout_image"]
        self.layout_stats = item["stats"]
        self.file_label.configure(
            text=(
                f"批量 {self.preview_index + 1}/{len(self.batch_items)}，打印将全部发送\n"
                f"预览：{source_path.name}  {image_w} x {image_h} px"
            )
        )
        self._update_stats_label(item["stats"], prefix=f"{self.preview_index + 1}/{len(self.batch_items)} | ")
        self._draw_preview()

    def _on_preview_wheel(self, event):
        if len(self.batch_items) <= 1:
            return "break"

        if getattr(event, "num", None) == 4 or getattr(event, "delta", 0) > 0:
            self._show_batch_preview(self.preview_index - 1)
        else:
            self._show_batch_preview(self.preview_index + 1)
        return "break"

    def _show_batch_result(self, processed, saved, failures, auto_save):
        if not processed:
            detail = "\n".join(failures[:8]) if failures else "没有可处理的图片。"
            messagebox.showerror("批量排版失败", detail)
            return

        if auto_save:
            total_kb = sum(path.stat().st_size for path in saved) / 1024
            folders = {str(path.parent) for path in saved}
            folder_text = saved[0].parent if len(folders) == 1 else "原图所在文件夹"
            message = f"已排版 {processed} 张，自动保存 {len(saved)} 张到 {folder_text}，总大小 {total_kb:.1f} KB。"
        else:
            message = f"已排版 {processed} 张，自动保存已关闭；打印会直接使用当前批量队列。"

        self._set_status(f"{message} 点击“开始打印”会打印全部。")

        if failures:
            detail = "\n".join(failures[:8])
            if len(failures) > 8:
                detail += f"\n... 还有 {len(failures) - 8} 个文件失败"
            messagebox.showwarning("批量排版完成", f"{message}\n\n失败文件：\n{detail}")

    def clear_all(self):
        self.source_path = None
        self.source_image = None
        self.layout_image = None
        self.preview_photo = None
        self.layout_stats = None
        self.batch_items = []
        self.preview_index = 0
        self.file_label.configure(text="尚未选择图片")
        self.stats_label.configure(text="")
        self._set_status("")
        self._draw_preview()

    def save_layout(self):
        if self.layout_image is None:
            messagebox.showwarning("提示", "请先选择证件照。")
            return

        path = self._default_output_path()
        try:
            self.layout_image.save(path, "JPEG", quality=95, dpi=(DPI, DPI), optimize=True)
            size_kb = os.path.getsize(path) / 1024
            self._set_status(f"已保存：{path}（{size_kb:.1f} KB）")
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))

    def print_layout(self):
        if self.batch_items:
            self.print_batch_layouts()
            return

        if self.layout_image is None:
            messagebox.showwarning("提示", "请先选择证件照。")
            return

        temp_path = Path(os.environ.get("TEMP", str(Path.cwd()))) / "photo_layout_tool_print.jpg"
        try:
            self.layout_image.save(temp_path, "JPEG", quality=95, dpi=(DPI, DPI))
        except Exception as exc:
            messagebox.showerror("打印失败", f"创建临时打印文件失败：{exc}")
            return

        try:
            self._print_image_file(temp_path)
            self._set_status("打印任务已发送。")
        except Exception as exc:
            messagebox.showerror("打印失败", str(exc))

    def print_batch_layouts(self):
        if not self.batch_items:
            messagebox.showwarning("提示", "请先选择证件照。")
            return

        failures = []
        sent = 0
        for index, item in enumerate(self.batch_items, 1):
            try:
                self._print_batch_item(item, index)
                sent += 1
            except Exception as exc:
                failures.append(f"{item['source_path'].name}: {exc}")

        if failures:
            detail = "\n".join(failures[:8])
            if len(failures) > 8:
                detail += f"\n... 还有 {len(failures) - 8} 个文件失败"
            self._set_status(f"已发送 {sent} / {len(self.batch_items)} 张排版图。")
            messagebox.showwarning(
                "批量打印完成",
                f"已发送 {sent} / {len(self.batch_items)} 张排版图。\n\n失败文件：\n{detail}",
            )
            return

        self._set_status(f"已发送 {sent} 张排版图到打印机。")

    def _print_batch_item(self, item, index):
        output_path = item.get("output_path")
        if output_path and output_path.exists():
            self._print_image_file(output_path)
            return

        temp_path = Path(os.environ.get("TEMP", str(Path.cwd()))) / f"photo_layout_tool_batch_{index}.jpg"
        item["layout_image"].save(temp_path, "JPEG", quality=95, dpi=(DPI, DPI))
        self._print_image_file(temp_path)

    def _print_image_file(self, image_path):
        if not sys.platform.startswith("win"):
            raise RuntimeError("当前系统不支持应用内打印。")

        try:
            self._print_with_win32(image_path)
        except Exception as exc:
            try:
                os.startfile(str(image_path), "print")
            except Exception as fallback_exc:
                raise RuntimeError(f"{exc}\n\n系统默认打印也失败：{fallback_exc}") from fallback_exc

    def _print_with_win32(self, image_path):
        import win32print
        import win32ui
        from PIL import ImageWin

        printer = self.printer_name.get()
        if not printer or printer == SYSTEM_DEFAULT_PRINTER:
            printer = win32print.GetDefaultPrinter()

        hdc = win32ui.CreateDC()
        hdc.CreatePrinterDC(printer)
        try:
            printable_w = hdc.GetDeviceCaps(8)  # HORZRES
            printable_h = hdc.GetDeviceCaps(10)  # VERTRES
            printer_dpi_x = hdc.GetDeviceCaps(88)  # LOGPIXELSX
            printer_dpi_y = hdc.GetDeviceCaps(90)  # LOGPIXELSY
            paper_mm = self._paper_size_mm()
            target_w = int(round(paper_mm[0] / 25.4 * printer_dpi_x))
            target_h = int(round(paper_mm[1] / 25.4 * printer_dpi_y))
            target_w = min(target_w, printable_w)
            target_h = min(target_h, printable_h)
            left = max(0, int((printable_w - target_w) / 2))
            top = max(0, int((printable_h - target_h) / 2))

            image = Image.open(image_path).convert("RGB")
            dib = ImageWin.Dib(image)
            hdc.StartDoc(APP_NAME)
            hdc.StartPage()
            dib.draw(hdc.GetHandleOutput(), (left, top, left + target_w, top + target_h))
            hdc.EndPage()
            hdc.EndDoc()
        finally:
            hdc.DeleteDC()

    def open_printer_settings(self):
        if not sys.platform.startswith("win"):
            messagebox.showinfo("提示", "打印机属性仅支持 Windows。")
            return

        printer = self.printer_name.get()
        if not printer or printer == SYSTEM_DEFAULT_PRINTER:
            try:
                import win32print

                printer = win32print.GetDefaultPrinter()
            except Exception:
                printer = ""

        try:
            if printer:
                subprocess.Popen(
                    ["rundll32.exe", "printui.dll,PrintUIEntry", "/p", "/n", printer],
                    shell=False,
                )
                return
            subprocess.Popen(["control.exe", "printers"], shell=False)
        except Exception as exc:
            messagebox.showerror("打开失败", str(exc))

    def open_project_home(self):
        try:
            webbrowser.open(REPO_URL)
        except Exception as exc:
            messagebox.showerror("打开失败", str(exc))

    def toggle_topmost(self):
        self.is_topmost.set(not self.is_topmost.get())
        self.attributes("-topmost", self.is_topmost.get())
        self._style_topmost_button()

    def _style_topmost_button(self):
        if self.is_topmost.get():
            self.topmost_button.set_colors("#EF4444", "#FFFFFF", "#DC2626", "#FFFFFF")
        else:
            self.topmost_button.set_colors(NEUTRAL, "#334155", NEUTRAL_HOVER, "#0F172A")


if __name__ == "__main__":
    enable_dpi_awareness()
    app = PhotoLayoutTool()
    app.mainloop()
