import tkinter as tk
from tkinter import ttk

from ui_helpers import status_card, value_cell


def build_control_tab(app, root):
    ttk.Label(root, text="滴定控制", style="Title.TLabel").pack(anchor="w", pady=(0, 10))

    telemetry = ttk.Frame(root, style="TFrame")
    telemetry.pack(fill=tk.X)
    for col in range(6):
        telemetry.columnconfigure(col, weight=1)
    status_card(telemetry, 0, 0, "pH", app.ph_var)
    status_card(telemetry, 0, 1, "温度 ℃", app.temp_var)
    status_card(telemetry, 0, 2, "电压 V", app.voltage_var)
    status_card(telemetry, 0, 3, "PWM1 %", app.pwm_display_var)
    status_card(telemetry, 0, 4, "蠕动泵 %", app.pump_display_var)
    status_card(telemetry, 0, 5, "连接", app.status_var)

    slider = ttk.LabelFrame(root, text="丝杆滑台", padding=12)
    slider.pack(fill=tk.X, pady=12)
    for col in range(6):
        slider.columnconfigure(col, weight=1)
    value_cell(slider, 0, 0, "当前位置", app.slider_pos_var)
    value_cell(slider, 0, 1, "目标位置", app.slider_target_var)
    value_cell(slider, 0, 2, "剩余步数", app.slider_distance_var)
    value_cell(slider, 0, 3, "已使能", app.slider_enabled_var)
    value_cell(slider, 0, 4, "运动中", app.slider_moving_var)
    value_cell(slider, 0, 5, "当前速度", app.slider_speed_display_var)

    controls = ttk.Frame(slider)
    controls.grid(row=1, column=0, columnspan=6, sticky="ew", pady=(12, 4))
    for col in range(10):
        controls.columnconfigure(col, weight=1)
    ttk.Label(controls, text="速度 steps/s").grid(row=0, column=0, padx=4, sticky="e")
    ttk.Entry(controls, textvariable=app.slider_speed_set_var, width=10).grid(row=0, column=1, padx=4, sticky="ew")
    ttk.Button(controls, text="设置速度", style="Primary.TButton", command=app.set_slider_speed).grid(row=0, column=2, padx=4)
    ttk.Label(controls, text="加速度").grid(row=0, column=3, padx=4, sticky="e")
    ttk.Entry(controls, textvariable=app.slider_accel_var, width=10).grid(row=0, column=4, padx=4, sticky="ew")
    ttk.Button(controls, text="设置加速度", command=app.set_slider_accel).grid(row=0, column=5, padx=4)
    ttk.Label(controls, text="距离 mm").grid(row=1, column=0, padx=4, pady=8, sticky="e")
    ttk.Entry(controls, textvariable=app.move_mm_var, width=10).grid(row=1, column=1, padx=4, pady=8, sticky="ew")
    ttk.Button(controls, text="移动距离", style="Primary.TButton", command=app.move_slider_mm).grid(row=1, column=2, padx=4, pady=8)
    ttk.Label(controls, text="时间 s").grid(row=1, column=3, padx=4, pady=8, sticky="e")
    ttk.Entry(controls, textvariable=app.move_sec_var, width=10).grid(row=1, column=4, padx=4, pady=8, sticky="ew")
    ttk.Button(controls, text="按时间移动", command=app.move_slider_time).grid(row=1, column=5, padx=4, pady=8)

    actions = ttk.Frame(slider)
    actions.grid(row=2, column=0, columnspan=6, sticky="ew", pady=8)
    for idx, (text, cmd, style_name) in enumerate([
        ("使能", app.slider_enable, "Primary.TButton"),
        ("关闭使能", app.slider_disable, "TButton"),
        ("停止", app.slider_stop, "TButton"),
        ("立即停止", app.slider_halt, "TButton"),
        ("清零", app.slider_zero, "TButton"),
        ("急停", app.emergency_stop, "Danger.TButton"),
    ]):
        actions.columnconfigure(idx, weight=1)
        ttk.Button(actions, text=text, style=style_name, command=cmd).grid(row=0, column=idx, padx=5, sticky="ew")

    optical = ttk.LabelFrame(root, text="AS7341 / MLX90640", padding=12)
    optical.pack(fill=tk.X, pady=(0, 12))
    for col in range(4):
        optical.columnconfigure(col, weight=1)
    value_cell(optical, 0, 0, "MLX90640 平均温度 ℃", app.mlx_temp_var)
    value_cell(optical, 0, 1, "AS7341 强度", app.as7341_intensity_var)
    value_cell(optical, 0, 2, "AS7341 变化率", app.as7341_rate_var)
    value_cell(optical, 0, 3, "传感器状态", app.sensor_status_var)

    pump_frame = ttk.LabelFrame(root, text="PWM / 蠕动泵", padding=12)
    pump_frame.pack(fill=tk.X, pady=(0, 12))
    for col in range(7):
        pump_frame.columnconfigure(col, weight=1)
    ttk.Label(pump_frame, text="PWM1 %").grid(row=0, column=0, padx=4, sticky="e")
    ttk.Entry(pump_frame, textvariable=app.pwm_set_var, width=10).grid(row=0, column=1, padx=4, sticky="ew")
    ttk.Button(pump_frame, text="设置 PWM1", style="Primary.TButton", command=app.set_pwm1).grid(row=0, column=2, padx=4)
    ttk.Label(pump_frame, text="蠕动泵 %").grid(row=0, column=3, padx=4, sticky="e")
    ttk.Entry(pump_frame, textvariable=app.pump_set_var, width=10).grid(row=0, column=4, padx=4, sticky="ew")
    ttk.Button(pump_frame, text="设置蠕动泵", style="Primary.TButton", command=app.set_pump).grid(row=0, column=5, padx=4)
    ttk.Button(pump_frame, text="停止蠕动泵", command=app.pump_stop).grid(row=0, column=6, padx=4)

    log_frame = ttk.LabelFrame(root, text="通信日志", padding=10)
    log_frame.pack(fill=tk.BOTH, expand=True)
    app.log = tk.Text(log_frame, height=8, bg="#0f172a", fg="#e5e7eb", insertbackground="#e5e7eb", relief=tk.FLAT)
    app.log.pack(fill=tk.BOTH, expand=True)
