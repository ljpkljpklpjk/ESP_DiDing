from tkinter import ttk


def build_network_tab(app, root):
    ttk.Label(root, text="网络设置", style="Title.TLabel").pack(anchor="w", pady=(0, 10))
    frame = ttk.LabelFrame(root, text="树莓派 WiFi", padding=14)
    frame.pack(fill="x")
    frame.columnconfigure(1, weight=1)
    frame.columnconfigure(3, weight=1)
    ttk.Label(frame, text="状态").grid(row=0, column=0, sticky="w", padx=4, pady=6)
    ttk.Label(frame, textvariable=app.pi_wifi_status_var, wraplength=760).grid(row=0, column=1, columnspan=4, sticky="ew", padx=4, pady=6)
    ttk.Button(frame, text="刷新状态", style="Primary.TButton", command=app.refresh_wifi_status).grid(row=1, column=0, padx=4, pady=8, sticky="ew")
    ttk.Button(frame, text="打开 WiFi", command=app.wifi_on).grid(row=1, column=1, padx=4, pady=8, sticky="ew")
    ttk.Button(frame, text="关闭 WiFi", command=app.wifi_off).grid(row=1, column=2, padx=4, pady=8, sticky="ew")
    ttk.Label(frame, text="WiFi 名称").grid(row=2, column=0, sticky="w", padx=4, pady=8)
    ttk.Entry(frame, textvariable=app.wifi_ssid_var, width=28).grid(row=2, column=1, sticky="ew", padx=4, pady=8)
    ttk.Label(frame, text="密码").grid(row=2, column=2, sticky="w", padx=4, pady=8)
    ttk.Entry(frame, textvariable=app.wifi_password_var, width=28, show="*").grid(row=2, column=3, sticky="ew", padx=4, pady=8)
    ttk.Button(frame, text="连接 WiFi", style="Primary.TButton", command=app.connect_wifi).grid(row=2, column=4, padx=4, pady=8, sticky="ew")
