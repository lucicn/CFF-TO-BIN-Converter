"""
CFF TO BIN Converter
Simple GUI tool to convert Mercedes-Benz CFF (Caesar Flash File) containers to binary files.
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

from cff_parser import CFFParser


class CFFToBinApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CFF TO BIN Converter")
        self.root.geometry("540x380")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.loaded_file = None
        self.parser = None

        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure("Main.TFrame", background="#1e1e2e")
        self.style.configure("Card.TFrame", background="#2a2a3c", relief="flat")

        self.style.configure(
            "Title.TLabel",
            background="#1e1e2e",
            foreground="#cdd6f4",
            font=("Segoe UI", 18, "bold"),
        )
        self.style.configure(
            "Subtitle.TLabel",
            background="#1e1e2e",
            foreground="#6c7086",
            font=("Segoe UI", 9),
        )
        self.style.configure(
            "Info.TLabel",
            background="#2a2a3c",
            foreground="#bac2de",
            font=("Segoe UI", 10),
        )
        self.style.configure(
            "InfoValue.TLabel",
            background="#2a2a3c",
            foreground="#cdd6f4",
            font=("Segoe UI", 10, "bold"),
        )
        self.style.configure(
            "Status.TLabel",
            background="#1e1e2e",
            foreground="#6c7086",
            font=("Segoe UI", 9),
        )
        self.style.configure(
            "Load.TButton",
            font=("Segoe UI", 11, "bold"),
            padding=(20, 10),
        )
        self.style.configure(
            "Convert.TButton",
            font=("Segoe UI", 11, "bold"),
            padding=(20, 10),
        )

        # Button color maps
        self.style.map(
            "Load.TButton",
            background=[("active", "#45475a"), ("!disabled", "#363649")],
            foreground=[("!disabled", "#cdd6f4")],
        )
        self.style.map(
            "Convert.TButton",
            background=[
                ("active", "#40a02b"),
                ("!disabled", "#a6e3a1"),
                ("disabled", "#45475a"),
            ],
            foreground=[("!disabled", "#1e1e2e"), ("disabled", "#6c7086")],
        )

    def _build_ui(self):
        main = ttk.Frame(self.root, style="Main.TFrame")
        main.pack(fill="both", expand=True, padx=24, pady=20)

        # Title
        ttk.Label(main, text="CFF TO BIN Converter", style="Title.TLabel").pack(
            anchor="w"
        )
        ttk.Label(
            main,
            text="Convert Mercedes-Benz CFF flash containers to binary files",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(0, 16))

        # File info card
        card = ttk.Frame(main, style="Card.TFrame")
        card.pack(fill="x", ipady=12, ipadx=16)

        inner = ttk.Frame(card, style="Card.TFrame")
        inner.pack(fill="x", padx=16, pady=8)

        # Row: File
        row0 = ttk.Frame(inner, style="Card.TFrame")
        row0.pack(fill="x", pady=2)
        ttk.Label(row0, text="File:", style="Info.TLabel", width=12).pack(
            side="left"
        )
        self.lbl_file = ttk.Label(
            row0, text="No file loaded", style="InfoValue.TLabel"
        )
        self.lbl_file.pack(side="left", fill="x")

        # Row: Flash Name
        row1 = ttk.Frame(inner, style="Card.TFrame")
        row1.pack(fill="x", pady=2)
        ttk.Label(row1, text="Flash Name:", style="Info.TLabel", width=12).pack(
            side="left"
        )
        self.lbl_flash_name = ttk.Label(row1, text="-", style="InfoValue.TLabel")
        self.lbl_flash_name.pack(side="left")

        # Row: Author
        row2 = ttk.Frame(inner, style="Card.TFrame")
        row2.pack(fill="x", pady=2)
        ttk.Label(row2, text="Author:", style="Info.TLabel", width=12).pack(
            side="left"
        )
        self.lbl_author = ttk.Label(row2, text="-", style="InfoValue.TLabel")
        self.lbl_author.pack(side="left")

        # Row: Checksum
        row3 = ttk.Frame(inner, style="Card.TFrame")
        row3.pack(fill="x", pady=2)
        ttk.Label(row3, text="Checksum:", style="Info.TLabel", width=12).pack(
            side="left"
        )
        self.lbl_checksum = ttk.Label(row3, text="-", style="InfoValue.TLabel")
        self.lbl_checksum.pack(side="left")

        # Row: Segments
        row4 = ttk.Frame(inner, style="Card.TFrame")
        row4.pack(fill="x", pady=2)
        ttk.Label(row4, text="Segments:", style="Info.TLabel", width=12).pack(
            side="left"
        )
        self.lbl_segments = ttk.Label(row4, text="-", style="InfoValue.TLabel")
        self.lbl_segments.pack(side="left")

        # Buttons row
        btn_frame = ttk.Frame(main, style="Main.TFrame")
        btn_frame.pack(fill="x", pady=(20, 0))

        self.btn_load = ttk.Button(
            btn_frame,
            text="Load CFF File",
            style="Load.TButton",
            command=self._load_file,
        )
        self.btn_load.pack(side="left", expand=True, fill="x", padx=(0, 8))

        self.btn_convert = ttk.Button(
            btn_frame,
            text="Convert to BIN",
            style="Convert.TButton",
            command=self._convert_file,
            state="disabled",
        )
        self.btn_convert.pack(side="right", expand=True, fill="x", padx=(8, 0))

        # Status bar
        self.lbl_status = ttk.Label(main, text="Ready", style="Status.TLabel")
        self.lbl_status.pack(anchor="w", pady=(12, 0))

    def _set_status(self, text):
        self.lbl_status.configure(text=text)
        self.root.update_idletasks()

    def _load_file(self):
        filepath = filedialog.askopenfilename(
            title="Select CFF File",
            filetypes=[("CFF Files", "*.cff"), ("All Files", "*.*")],
        )
        if not filepath:
            return

        self._set_status("Loading file...")
        self.btn_load.configure(state="disabled")
        self.btn_convert.configure(state="disabled")

        def do_parse():
            try:
                parser = CFFParser.from_file(filepath)
                self.root.after(0, lambda: self._on_parse_done(filepath, parser))
            except Exception as e:
                self.root.after(0, lambda: self._on_parse_error(str(e)))

        threading.Thread(target=do_parse, daemon=True).start()

    def _on_parse_done(self, filepath, parser):
        self.loaded_file = filepath
        self.parser = parser

        filename = os.path.basename(filepath)
        self.lbl_file.configure(text=filename)
        self.lbl_flash_name.configure(text=parser.flash_name or "(unknown)")
        self.lbl_author.configure(text=parser.file_author or "(unknown)")

        chk_status = "Valid" if parser.checksum_valid() else "MISMATCH"
        self.lbl_checksum.configure(
            text=f"0x{parser.stored_checksum:08X} ({chk_status})",
            foreground="#a6e3a1" if parser.checksum_valid() else "#f38ba8",
        )

        all_segs = parser.get_all_segments()
        total_size = sum(len(seg.data) for _, seg in all_segs)
        self.lbl_segments.configure(
            text=f"{len(all_segs)} segment(s), {total_size:,} bytes total"
        )

        self.btn_load.configure(state="normal")
        self.btn_convert.configure(state="normal")
        self._set_status(f"Loaded: {filename}")

    def _on_parse_error(self, error_msg):
        self.btn_load.configure(state="normal")
        self._set_status("Error loading file")
        messagebox.showerror("Parse Error", f"Failed to parse CFF file:\n\n{error_msg}")

    def _convert_file(self):
        if not self.parser:
            return

        base_name = os.path.splitext(os.path.basename(self.loaded_file))[0]
        save_path = filedialog.asksaveasfilename(
            title="Save BIN File",
            defaultextension=".bin",
            initialfile=f"{base_name}.bin",
            filetypes=[("Binary Files", "*.bin"), ("All Files", "*.*")],
        )
        if not save_path:
            return

        self._set_status("Converting...")
        self.btn_convert.configure(state="disabled")

        def do_convert():
            try:
                binary_data = self.parser.get_combined_binary()
                with open(save_path, 'wb') as f:
                    f.write(binary_data)
                self.root.after(
                    0,
                    lambda: self._on_convert_done(save_path, len(binary_data)),
                )
            except Exception as e:
                self.root.after(0, lambda: self._on_convert_error(str(e)))

        threading.Thread(target=do_convert, daemon=True).start()

    def _on_convert_done(self, save_path, size):
        self.btn_convert.configure(state="normal")
        self._set_status(f"Saved: {os.path.basename(save_path)} ({size:,} bytes)")
        messagebox.showinfo(
            "Conversion Complete",
            f"Binary file saved successfully!\n\n"
            f"Path: {save_path}\n"
            f"Size: {size:,} bytes",
        )

    def _on_convert_error(self, error_msg):
        self.btn_convert.configure(state="normal")
        self._set_status("Conversion failed")
        messagebox.showerror(
            "Conversion Error", f"Failed to convert file:\n\n{error_msg}"
        )


def main():
    root = tk.Tk()
    CFFToBinApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()