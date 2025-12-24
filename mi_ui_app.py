# =============================================================================
#  MI Generator & Flasher UI
# =============================================================================
#  Author      : Devan Antony
#  Created     : 2025-12-01
#  Description : Python GUI to generate MI BIN files, view HEX content,
#                and flash to target devices via COM port.
#                Features:
#                  - INI/CSV file selection
#                  - Interactive MI_bin_generator input
#                  - Hex viewer for generated BIN
#                  - COM port selection & test connection
#                  - Flashing via S32FlashTool
#  Notes       : It shall be taken into account while creating one file that
#                the python script will trigger another python script.
#                So creation of exe directly will have unexpected results.
#
#  Recommended to trigger script using a bat file with no arguments.
# =============================================================================

import os
import sys
import tkinter as tk
from tkinter import filedialog, scrolledtext
from tkinter import ttk
import subprocess
import threading
import serial.tools.list_ports
import ttkbootstrap as tb
import signal
import tempfile
import shutil

# ----------------------------- Resource Path -----------------------------
def resource_path(relative_path):
    """Correct path inside PyInstaller or normal run."""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# =========================================================================
#                                MAIN UI
# =========================================================================
class MI_UI:
    def __init__(self, root):
        self.root = root
        self.root.title("MI Generator & Flasher UI")
        self.ini_path = tk.StringVar()
        self.csv_path = tk.StringVar()
        self.selected_com = tk.StringVar()
        self.proc = None
        self.output_bin = None
        tb.Style(theme="flatly")

        # ----------------------------- Main Layout -----------------------------
        main = tb.Frame(root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        # Left panel
        left = tb.Frame(main)
        left.grid(row=1, column=0, sticky="n", padx=(0, 12))
        main.columnconfigure(0, weight=0)

        # Right panel - Console
        console_frame = tb.Frame(main)
        console_frame.grid(row=1, column=1, sticky="nsew")
        main.columnconfigure(1, weight=1)
        main.rowconfigure(1, weight=1)

        tb.Label(console_frame, text="Console Output:").grid(row=0, column=0, sticky="w")
        self.console = scrolledtext.ScrolledText(console_frame, width=90, height=35)
        self.console.grid(row=1, column=0, sticky="nsew")
        console_frame.columnconfigure(0, weight=1)
        console_frame.rowconfigure(1, weight=1)

        # ----------------------------- COM Port Row -----------------------------
        com_frame = tb.Frame(main)
        com_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        tb.Label(com_frame, text="Select COM Port:").grid(row=0, column=0, sticky="w")
        self.combobox = ttk.Combobox(com_frame, textvariable=self.selected_com, width=15, state="readonly")
        self.combobox.grid(row=0, column=1, padx=5)

        tb.Button(com_frame, text="Refresh", bootstyle="info", command=self.refresh_com_ports).grid(row=0, column=2, padx=5)
        tb.Button(com_frame, text="Test Connection", bootstyle="warning", command=self.test_connection).grid(row=0, column=3)

        self.refresh_com_ports()

        # ----------------------------- INI File -----------------------------
        tb.Label(left, text="Select mcu_mi.ini:").grid(row=0, column=0, sticky="w")
        tb.Entry(left, textvariable=self.ini_path, width=45).grid(row=1, column=0, sticky="w")
        tb.Button(left, text="Browse", bootstyle="secondary", command=self.browse_ini).grid(row=1, column=1, padx=5)

        # ----------------------------- CSV File -----------------------------
        tb.Label(left, text="Select mi_config.csv:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        tb.Entry(left, textvariable=self.csv_path, width=45).grid(row=3, column=0, sticky="w")
        tb.Button(left, text="Browse", bootstyle="secondary", command=self.browse_csv).grid(row=3, column=1, padx=5)

        # ----------------------------- Control Buttons -----------------------------
        self.start_btn = tb.Button(left, text="Start MI", bootstyle="success", command=self.run_script)
        self.start_btn.grid(row=4, column=0, pady=12, sticky="w")

        self.hex_btn = tb.Button(left, text="View Hex File", bootstyle="info", state="disabled", command=self.show_hex)
        self.hex_btn.grid(row=5, column=0, sticky="w")

        self.flash_btn = tb.Button(left, text="Flash MI", bootstyle="danger", state="disabled", command=self.flash_mi)
        self.flash_btn.grid(row=6, column=0, pady=(6, 0), sticky="w")

        self.output_label = tb.Label(left, text="Output File: -")
        self.output_label.grid(row=7, column=0, pady=10, sticky="w")

        # ----------------------------- Interactive Input Box -----------------------------
        tb.Label(left, text="Send Input to MI_bin_generator:").grid(row=8, column=0, sticky="w", pady=(5, 0))
        input_frame = tb.Frame(left)
        input_frame.grid(row=9, column=0, sticky="w")

        self.input_entry = tb.Entry(input_frame, width=35)
        self.input_entry.grid(row=0, column=0, padx=(0, 6))
        tb.Button(input_frame, text="Send", bootstyle="secondary", command=self.send_input).grid(row=0, column=1)

        # ----------------------------- Logo -----------------------------
        #logo_path = resource_path("images.png")
        logo_path = os.path.join(
            os.path.dirname(sys.executable if getattr(sys, "frozen", False) else __file__),
            "images.png"
        )

        if os.path.isfile(logo_path):
            try:
                self.logo_img = tk.PhotoImage(file=logo_path)
                tb.Label(left, image=self.logo_img).grid(row=10, column=0, pady=18, sticky="sw")
            except Exception as e:
                self.log(f"Logo load error: {e}")
        else:
            self.log(f"Logo missing: {logo_path}")

        if os.path.isfile(logo_path):
            try:
                self.logo_img = tk.PhotoImage(file=logo_path)
                tb.Label(left, image=self.logo_img).grid(row=10, column=0, pady=18, sticky="sw")
            except Exception as e:
                self.log(f"Logo load error: {e}")
        else:
            self.log("Logo missing.")

        root.minsize(1000, 600)

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # =========================================================================
    #                               LOGGING
    # =========================================================================
    def log(self, msg):
        try:
            self.console.insert(tk.END, msg + "\n")
            self.console.see(tk.END)
        except Exception:
            pass

    # =========================================================================
    #                               FILE BROWSERS
    # =========================================================================
    def browse_ini(self):
        f = filedialog.askopenfilename(filetypes=[("INI files", "*.ini")])
        if f:
            self.ini_path.set(f)

    def browse_csv(self):
        f = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
        if f:
            self.csv_path.set(f)

    # =========================================================================
    #                               COM PORTS
    # =========================================================================
    def refresh_com_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.combobox["values"] = ports
        self.selected_com.set(ports[0] if ports else "")
        self.log("COM ports refreshed.")

    # =========================================================================
    #                           TEST CONNECTION
    # =========================================================================
    def test_connection(self):
        com = self.selected_com.get()
        if not com:
            self.log("Select a COM port.")
            return

        s32 = resource_path(r"C:\NXP\S32FlashTool_2.1.2RTM\bin\S32FlashTool.exe")
        target = resource_path(r"C:\NXP\S32FlashTool_2.1.2RTM\targets\S32G3xxx.bin")
        algorithm = resource_path(r"C:\NXP\S32FlashTool_2.1.2RTM\flash\MX66U2G45G.bin")
        cmd = [s32, "-t", target, "-a", algorithm, "-i", "uart", "-p", com]

        self.log(f"Testing connection on {com}...")

        def reader(pipe):
            for line in iter(pipe.readline, ''):   # read full lines until EOF
                if not line:
                    break
                # Strip only the final newline, keep other formatting
                clean = line.rstrip()
                self.root.after(0, lambda t=clean: self.log(t))
            pipe.close()

        def worker():
            try:
                p = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
                )
                threading.Thread(target=reader, args=(p.stdout,), daemon=True).start()
                p.wait()
                self.root.after(0, lambda: self.log("Algorithm download complete."))
            except Exception as e:
                self.root.after(0, lambda e=e: self.log(f"Error: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    #                          RUN MI GENERATOR (FULL UI)
    # =========================================================================
    def run_script(self):
        self.console.delete("1.0", tk.END)

        ini = self.ini_path.get()
        csv = self.csv_path.get()
        if not os.path.isfile(ini) or not os.path.isfile(csv):
            self.log("Select valid INI + CSV files.")
            return

        # -------------------- FIXED for PyInstaller onefile --------------------
        if getattr(sys, "frozen", False):
            # Extract MI_bin_generator.py to a temp folder
            temp_dir = tempfile.mkdtemp()
            script = os.path.join(temp_dir, "MI_bin_generator.py")
            shutil.copy(resource_path("MI_bin_generator.py"), script)
            python_exec = sys.executable
        else:
            script = os.path.abspath("MI_bin_generator.py")
            python_exec = sys.executable

        cmd = [python_exec, "-u", script, f"--i={ini}", f"-c={csv}"]
        self.log(f"Running: {' '.join(cmd)}")
        self.log("=== Start sending MI inputs below ===")

        # ---------------------------------------------------------
        # Prompt-aware READER
        # ---------------------------------------------------------
        def reader(pipe):
            buffer = ""
            while True:
                ch = pipe.read(1)
                if not ch:
                    break
                buffer += ch

                if ch == "\n" or buffer.endswith(":") or buffer.endswith(": ") or buffer.endswith(") "):
                    out = buffer
                    buffer = ""
                    self.root.after(0, lambda t=out: self.log(t.rstrip()))
            pipe.close()

        # ---------------------------------------------------------
        def worker():
            try:
                self.proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                threading.Thread(target=reader, args=(self.proc.stdout,), daemon=True).start()
            except Exception as e:
                self.root.after(0, lambda e=e: self.log(f"Exception: {e}"))

        # ---------------------------------------------------------
        # FIXED BIN WATCHER (works with or without quotes)
        # ---------------------------------------------------------
        def bin_watcher():
            capturing = False
            buffer_path = ""
            last_line_index = 1  # start from first line

            while True:
                if not self.proc:
                    break

                try:
                    # Read new lines since last_line_index
                    total_lines = int(self.console.index(tk.END).split('.')[0])
                    if total_lines < last_line_index:
                        last_line_index = total_lines  # console was cleared
                    new_lines = [self.console.get(f"{i}.0", f"{i}.end").strip() for i in range(last_line_index, total_lines)]
                    last_line_index = total_lines
                except Exception:
                    threading.Event().wait(0.2)
                    continue

                for line in new_lines:
                    line = line.strip()

                    # Detect start of MI bin path
                    if "MI bin file generated:" in line:
                        capturing = True
                        parts = line.split(":", 1)
                        buffer_path = parts[1].strip().strip("'").strip('"') if len(parts) > 1 else ""
                        continue

                    # Capture continuation lines if needed
                    if capturing:
                        if line:  # skip empty
                            buffer_path += line.strip("'").strip('"')
                        # Check if file exists
                        if buffer_path and os.path.isfile(buffer_path):
                            self.output_bin = buffer_path
                            size = os.path.getsize(self.output_bin)
                            kb = size / 1024
                            self.root.after(0, lambda: self.output_label.config(
                                text=f"Output File: {self.output_bin} ({kb:.2f} KB)"
                            ))
                            self.root.after(0, lambda: self.hex_btn.config(state="normal"))
                            self.root.after(0, lambda: self.flash_btn.config(state="normal"))
                            return

                threading.Event().wait(0.2)  # small delay to avoid CPU hog

        # -------------------- Start Process --------------------
        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
        except Exception as e:
            self.log(f"Exception: {e}")
            return

        # Start threads
        threading.Thread(target=reader, args=(self.proc.stdout,), daemon=True).start()
        threading.Thread(target=bin_watcher, daemon=True).start()

    # =========================================================================
    #                           SEND INTERACTIVE INPUT
    # =========================================================================
    def send_input(self):
        if not (self.proc and self.proc.poll() is None):
            self.log("Process not running.")
            return

        try:
            msg = self.input_entry.get()
            if not msg:
                return
            self.proc.stdin.write(msg + "\n")
            self.proc.stdin.flush()
            self.input_entry.delete(0, tk.END)
            self.log(f"> {msg}")
        except Exception as e:
            self.log(f"Send error: {e}")

    # =========================================================================
    #                               HEX VIEWER
    # =========================================================================
    def show_hex(self):
        if not self.output_bin or not os.path.isfile(self.output_bin):
            self.log("BIN file missing.")
            return

        win = tk.Toplevel(self.root)
        win.title("Hex Viewer")
        text = scrolledtext.ScrolledText(win, width=120, height=40)
        text.pack(fill="both", expand=True)

        with open(self.output_bin, "rb") as f:
            data = f.read()

        out = []
        for offset in range(0, len(data), 16):
            chunk = data[offset:offset+16]
            hexstr = " ".join(f"{b:02X}" for b in chunk)
            ascii_text = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
            out.append(f"{offset:08X}  {hexstr:<48}  {ascii_text}")

        text.insert("1.0", "\n".join(out))

    # =========================================================================
    #                               FLASHING
    # =========================================================================
    def flash_mi(self):
        if not self.output_bin or not os.path.isfile(self.output_bin):
            self.log("Generated BIN missing.")
            return

        com = self.selected_com.get()
        if not com:
            self.log("Select COM port.")
            return

        s32 = resource_path(r"C:\NXP\S32FlashTool_2.1.2RTM\bin\S32FlashTool.exe")
        target = resource_path(r"C:\NXP\S32FlashTool_2.1.2RTM\targetsS32G3xxx.bin")
        addr = "0x0FFE0000"

        cmd = [s32, "-t", target, "-fprogram", "-f", self.output_bin, "-addr", addr, "-i", "uart", "-p", com]
        self.log(f"Flashing: {' '.join(cmd)}")

        def reader(pipe):
            buffer = ""
            while True:
                ch = pipe.read(1)
                if not ch:
                    break
                buffer += ch
                if ch == "\n" or buffer.endswith(":") or buffer.endswith(": ") or buffer.endswith(") "):
                    out = buffer
                    buffer = ""
                    self.root.after(0, lambda t=out: self.log(t.rstrip()))
            pipe.close()

        def worker():
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                threading.Thread(target=reader, args=(p.stdout,), daemon=True).start()
            except Exception as e:
                self.root.after(0, lambda e=e: self.log(f"Flash error: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    # =========================================================================
    #                               CLEANUP
    # =========================================================================
    def on_close(self):
        try:
            if self.proc and self.proc.poll() is None:
                try:
                    if os.name != "nt":
                        os.kill(self.proc.pid, signal.SIGINT)
                    else:
                        self.proc.terminate()
                except Exception:
                    try:
                        self.proc.terminate()
                    except Exception:
                        pass

                try:
                    self.proc.wait(timeout=1)
                except Exception:
                    try:
                        self.proc.kill()
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            self.root.destroy()
        except Exception:
            pass

# =========================================================================
#                              RUN PROGRAM
# =========================================================================
if __name__ == "__main__":
    root = tb.Window()
    app = MI_UI(root)
    root.mainloop()
