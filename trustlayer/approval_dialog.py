"""Native approval dialog, launched by the executor for one action."""
import json
import sys
import tkinter as tk
from tkinter import ttk


def ask(review, timeout_ms=None):
    result = "denied"
    root = tk.Tk()
    root.title("TrustLayer AI | Review action")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)
    details = (
        f"Action: {review['action']}\nResource: {review['resource']}\n"
        f"Target: {review['target']}\nRisk: {review['risk']}\n\n"
        f"{review['reason']}\n{review['consequence']}"
    )
    ttk.Label(frame, text=details, wraplength=560, justify="left").pack(anchor="w")
    buttons = ttk.Frame(frame)
    buttons.pack(anchor="e", pady=(18, 0))

    def close(choice="denied"):
        nonlocal result
        result = choice
        root.destroy()

    deny = ttk.Button(buttons, text="Block", command=close)
    deny.pack(side="left", padx=(0, 8))
    ttk.Button(
        buttons, text="Approve & Proceed", command=lambda: close("approved")
    ).pack(side="left")
    root.protocol("WM_DELETE_WINDOW", close)
    root.bind("<Escape>", lambda event: close())
    if timeout_ms is not None:
        root.after(timeout_ms, close)
    deny.focus_set()
    root.mainloop()
    return result


if __name__ == "__main__":
    print(ask(json.load(sys.stdin)))
