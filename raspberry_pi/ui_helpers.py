import tkinter as tk
from tkinter import ttk


def configure_style(root):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("TFrame", background="#f3f6fb")
    style.configure("Card.TFrame", background="#ffffff", relief="flat")
    style.configure("TLabel", background="#f3f6fb", font=("Arial", 11))
    style.configure("Card.TLabel", background="#ffffff", font=("Arial", 11))
    style.configure("Value.TLabel", background="#ffffff", foreground="#1f2937", font=("Arial", 18, "bold"))
    style.configure("Title.TLabel", background="#f3f6fb", foreground="#0f172a", font=("Arial", 18, "bold"))
    style.configure("Subtle.TLabel", background="#ffffff", foreground="#64748b", font=("Arial", 10))
    style.configure("TButton", font=("Arial", 11), padding=(12, 8))
    style.configure("Primary.TButton", font=("Arial", 11, "bold"), padding=(14, 9))
    style.configure("Danger.TButton", font=("Arial", 11, "bold"), padding=(14, 9), foreground="#b91c1c")
    style.configure("TEntry", padding=5)
    style.configure("TNotebook", background="#f3f6fb", borderwidth=0)
    style.configure("TNotebook.Tab", font=("Arial", 12, "bold"), padding=(18, 10))
    style.configure("TLabelframe", background="#f3f6fb", padding=12)
    style.configure("TLabelframe.Label", background="#f3f6fb", foreground="#0f172a", font=("Arial", 12, "bold"))


def status_card(parent, row, col, title, var):
    card = ttk.Frame(parent, style="Card.TFrame", padding=12)
    card.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)
    ttk.Label(card, text=title, style="Subtle.TLabel").pack(anchor="w")
    ttk.Label(card, textvariable=var, style="Value.TLabel", wraplength=140).pack(anchor="w", pady=(5, 0))


def value_cell(parent, row, col, title, var):
    cell = ttk.Frame(parent, padding=8)
    cell.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
    ttk.Label(cell, text=title).pack(anchor="w")
    ttk.Label(cell, textvariable=var, font=("Arial", 13, "bold")).pack(anchor="w", pady=(3, 0))
