"""Native, local approval dialog for one pending action."""
import json
import os
import subprocess
import sys
import tkinter as tk
from tkinter import ttk


def copy_prompt(prompt):
    """Copy only the selected refinement, with no file or shell intermediary."""
    if sys.platform == "win32":
        command = [os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                                "System32", "clip.exe")]
        content = prompt.encode("utf-16")
    elif sys.platform == "darwin":
        command = ["/usr/bin/pbcopy"]
        content = prompt.encode("utf-8")
    else:
        return False
    try:
        completed = subprocess.run(command, input=content, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, timeout=3, check=False)
        return completed.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def ask(review, timeout_ms=None, refinement=None):
    result = "denied"
    root = tk.Tk()
    root.title("TrustLayer AI")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.configure(background="#eef2f7")

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("Review.TButton", padding=(14, 8), font="TkDefaultFont",
                    background="#e8edf5", foreground="#17253c", borderwidth=0)
    style.map("Review.TButton", background=[("active", "#d8e3f2")])
    style.configure("Primary.Review.TButton", background="#244fc0", foreground="white")
    style.map("Primary.Review.TButton", background=[("active", "#173d9e")])

    frame = tk.Frame(root, background="white", padx=24, pady=22)
    frame.pack(fill="both", expand=True, padx=12, pady=12)
    frame.grid_columnconfigure(0, weight=1)

    def label(text, row, *, color="#17253c", font="TkDefaultFont", gap=0):
        tk.Label(frame, text=text, foreground=color, background="white", wraplength=500,
                 justify="left", font=font).grid(row=row, column=0, sticky="w", pady=(gap, 0))

    label("TrustLayer AI", 0, color="#244fc0", font=("TkDefaultFont", 10, "bold"))
    label("Review this prompt" if refinement else "Review this action", 1,
          font=("TkDefaultFont", 19, "bold"), gap=5)
    label(review["reason"], 2, color="#455772", gap=5)

    target = review["target"]
    if review["resource"] != target:
        target = review["resource"] + "\n" + target
    details = tk.Text(frame, width=64, height=3 if refinement else 6, wrap="word",
                      borderwidth=0, highlightthickness=0, padx=10, pady=8,
                      background="#f3f6fa", foreground="#17253c", exportselection=False)
    details.insert("1.0", f"{review['action']}\n{target}\n{review['consequence']}")
    details.configure(state="disabled")
    details.grid(row=3, column=0, sticky="ew", pady=(12, 0))

    if refinement:
        label("Suggested prompt", 4, font=("TkDefaultFont", 10, "bold"), gap=14)
        suggestion = tk.Text(frame, height=4, width=64, wrap="word", borderwidth=0,
                             highlightthickness=0, padx=10, pady=8,
                             background="#edf3ff", foreground="#17253c", exportselection=False)
        suggestion.insert("1.0", refinement)
        suggestion.configure(state="disabled")
        suggestion.grid(row=5, column=0, sticky="ew", pady=(5, 0))
        copy_row = tk.Frame(frame, background="white")
        copy_row.grid(row=6, column=0, sticky="ew", pady=(5, 0))
        status = tk.Label(copy_row, background="white", foreground="#455772")
        status.pack(side="left")

        def copy():
            status.configure(text="Copied. Paste it in this chat." if copy_prompt(refinement)
                             else "Select the suggestion and copy it manually.")

        ttk.Button(copy_row, text="Copy prompt", style="Review.TButton",
                   command=copy).pack(side="right")

    buttons = tk.Frame(frame, background="white")
    buttons.grid(row=7, column=0, sticky="e", pady=(17, 0))

    def close(choice="denied"):
        nonlocal result
        result = choice
        root.destroy()

    deny = ttk.Button(buttons, text="Block and refine prompt" if refinement else "Block",
                      style="Review.TButton",
                      command=lambda: close("refine" if refinement else "denied"))
    deny.pack(side="left", padx=(0, 8))
    ttk.Button(buttons, text="Approve & Proceed", style="Primary.Review.TButton",
               command=lambda: close("approved")).pack(side="left")
    root.protocol("WM_DELETE_WINDOW", close)
    root.bind("<Escape>", lambda event: close())
    if timeout_ms is not None:
        root.after(timeout_ms, close)
    deny.focus_set()
    root.mainloop()
    return result


if __name__ == "__main__":
    print(ask(json.load(sys.stdin)))
