import tkinter as tk
from tkinter import ttk


def build_update_tab(app, root):
    ttk.Label(root, text="系统更新", style="Title.TLabel").pack(anchor="w", pady=(0, 10))
    frame = ttk.LabelFrame(root, text="Gitee / OTA", padding=14)
    frame.pack(fill=tk.X)
    frame.columnconfigure(1, weight=1)
    frame.columnconfigure(3, weight=1)
    ttk.Label(frame, text="项目路径").grid(row=0, column=0, sticky="w", padx=4, pady=8)
    ttk.Entry(frame, textvariable=app.project_dir_var, width=70).grid(row=0, column=1, columnspan=3, sticky="ew", padx=4, pady=8)
    ttk.Label(frame, text="ESP32 IP").grid(row=1, column=0, sticky="w", padx=4, pady=8)
    ttk.Entry(frame, textvariable=app.esp32_ip_var, width=24).grid(row=1, column=1, sticky="ew", padx=4, pady=8)
    ttk.Label(frame, text="OTA 密码").grid(row=1, column=2, sticky="w", padx=4, pady=8)
    ttk.Entry(frame, textvariable=app.ota_password_var, width=24, show="*").grid(row=1, column=3, sticky="ew", padx=4, pady=8)
    ttk.Button(frame, text="检查 Gitee 更新", command=app.check_project_update).grid(row=2, column=0, padx=4, pady=10, sticky="ew")
    ttk.Button(frame, text="从 Gitee 更新代码", style="Primary.TButton", command=app.update_project).grid(row=2, column=1, padx=4, pady=10, sticky="ew")
    app.ota_button = ttk.Button(frame, text="更新 ESP32 固件 OTA", style="Primary.TButton", command=app.update_esp32_ota)
    app.ota_button.grid(row=2, column=2, padx=4, pady=10, sticky="ew")
    ttk.Label(frame, text="OTA 进度").grid(row=3, column=0, sticky="w", padx=4, pady=8)
    ttk.Label(frame, textvariable=app.ota_progress_var, wraplength=800).grid(row=3, column=1, columnspan=3, sticky="ew", padx=4, pady=8)
    app.ota_progress_bar = ttk.Progressbar(frame, mode="indeterminate")
    app.ota_progress_bar.grid(row=4, column=1, columnspan=3, sticky="ew", padx=4, pady=8)
    ttk.Label(frame, text="状态").grid(row=5, column=0, sticky="w", padx=4, pady=8)
    ttk.Label(frame, textvariable=app.update_status_var, wraplength=800).grid(row=5, column=1, columnspan=3, sticky="ew", padx=4, pady=8)

    log_frame = ttk.LabelFrame(root, text="OTA 实时输出", padding=10)
    log_frame.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
    app.ota_log = tk.Text(log_frame, height=12, bg="#111827", fg="#d1d5db", insertbackground="#d1d5db", relief=tk.FLAT)
    app.ota_log.pack(fill=tk.BOTH, expand=True)
