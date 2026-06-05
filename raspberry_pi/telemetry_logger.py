import csv
import json
import re
import time
from datetime import datetime
from pathlib import Path


PAPER_CSV_FIELDS = [
    "group",
    "repeat",
    "run_id",
    "time_s",
    "device_ms",
    "pH",
    "TDS_mg_L",
    "conductivity_uS_cm",
    "water_temp_C",
    "spectral_intensity",
    "absorbance",
    "estimated_concentration_mg_L",
    "tof_distance_mm",
    "pump_duty_pct",
    "reagent_volume_mL",
    "control_mode",
    "event",
    "micro_dosing_active",
    "safety_active",
    "target_ph_low",
    "target_ph_high",
    "target_tds_mg_L",
    "target_concentration_mg_L",
    "ph_voltage_V",
    "tds_voltage_V",
    "thermal_gradient_C",
    "ambient_temp_C",
    "humidity_pct",
    "pressure_hPa",
    "ambient_lux",
    "tof_confidence",
    "flow_coeff",
    "slider_pos_steps",
    "host_time_s",
]


def first_value(data, *keys, default=None):
    if not isinstance(data, dict):
        return default
    for key in keys:
        value = data.get(key)
        if value is not None:
            return value
    return default


def number_or_blank(value):
    return "" if value is None else value


def infer_group_repeat(run_id: str | None):
    if not run_id:
        return None, None
    match = re.match(r"run_([a-zA-Z]\d+)_(\d+)$", run_id)
    if not match:
        return None, None
    return match.group(1).upper(), int(match.group(2))


class TelemetryLogger:
    def __init__(
        self,
        project_dir: Path,
        log_dir: Path | None = None,
        run_id: str | None = None,
        group: str | None = None,
        repeat: int | None = None,
        control_mode: str = "normal_dosing",
        target_ph_low: float | None = 6.8,
        target_ph_high: float | None = 7.2,
        target_tds_mg_l: float | None = 350.0,
        target_concentration_mg_l: float | None = 8.0,
        duration_s: int | None = None,
        sample_interval_s: int = 1,
    ):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = run_id or f"run_{stamp}"
        inferred_group, inferred_repeat = infer_group_repeat(self.run_id)
        self.group = group or inferred_group or "runtime"
        self.repeat = repeat or inferred_repeat or 1
        self.control_mode = control_mode
        self.target_ph_low = target_ph_low
        self.target_ph_high = target_ph_high
        self.target_tds_mg_l = target_tds_mg_l
        self.target_concentration_mg_l = target_concentration_mg_l
        self.duration_s = duration_s
        self.sample_interval_s = sample_interval_s
        self.start_host_time = time.time()
        self._boot_written = False
        self._last_tds_mg_l = None
        self._last_tds_ms = None

        if log_dir:
            requested_log_dir = Path(log_dir)
            self.log_dir = (
                requested_log_dir / "paper_dataset"
                if requested_log_dir.name.lower() == "data"
                else requested_log_dir
            )
        else:
            self.log_dir = Path(project_dir) / "data_logs" / "paper_dataset"
        self.closed_loop_dir = self.log_dir / "closed_loop"
        self.jsonl_dir = self.log_dir / "serial_jsonl"
        self.closed_loop_dir.mkdir(parents=True, exist_ok=True)
        self.jsonl_dir.mkdir(parents=True, exist_ok=True)

        self.csv_path = self.closed_loop_dir / f"{self.run_id}.csv"
        self.jsonl_path = self.jsonl_dir / f"{self.run_id}.jsonl"
        self._csv_file = self.csv_path.open("w", newline="", encoding="utf-8")
        self._jsonl_file = self.jsonl_path.open("w", encoding="utf-8")
        self._writer = csv.DictWriter(self._csv_file, fieldnames=PAPER_CSV_FIELDS)
        self._writer.writeheader()
        self._write_manifest()

    def write_boot(self, msg: dict | None = None):
        self._ensure_boot(msg)

    def write(self, msg: dict):
        if not isinstance(msg, dict):
            return
        self._ensure_boot()
        packet = self._to_jsonl_packet(msg)
        self._jsonl_file.write(json.dumps(packet, ensure_ascii=False, separators=(",", ":")) + "\n")
        self._jsonl_file.flush()
        self._writer.writerow(self._to_csv_row(packet))
        self._csv_file.flush()

    def close(self):
        self._csv_file.close()
        self._jsonl_file.close()

    def _ensure_boot(self, msg: dict | None = None):
        if self._boot_written:
            return
        source = msg if isinstance(msg, dict) else {}
        boot = {
            "type": "boot",
            "ok": first_value(source, "ok", default=True),
            "version": "code_v2_paper_dataset",
            "ads": first_value(source, "ads", default=True),
            "ds18b20": first_value(source, "ds18b20", "ds18b20_ok"),
            "mlx90640": first_value(source, "mlx90640", "mlx90640_ok"),
            "as7341": first_value(source, "as7341", "as7341_ok"),
            "bme280": first_value(source, "bme280", "bme280_ok"),
            "tof": first_value(source, "tof", "tof_ok"),
            "wifi_configured": first_value(source, "wifi_configured", "wifi_connected"),
            "run_id": self.run_id,
            "group": self.group,
            "repeat": self.repeat,
        }
        self._jsonl_file.write(json.dumps(boot, ensure_ascii=False, separators=(",", ":")) + "\n")
        self._jsonl_file.flush()
        self._boot_written = True

    def _write_manifest(self):
        manifest_path = self.log_dir / "closed_loop_manifest.csv"
        new_file = not manifest_path.exists()
        with manifest_path.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "group",
                    "group_name",
                    "purpose",
                    "repeat",
                    "run_id",
                    "csv_path",
                    "jsonl_path",
                    "duration_s",
                    "sample_interval_s",
                ],
            )
            if new_file:
                writer.writeheader()
            writer.writerow(
                {
                    "group": self.group,
                    "group_name": "runtime_acquisition",
                    "purpose": "live SH800 acquisition",
                    "repeat": self.repeat,
                    "run_id": self.run_id,
                    "csv_path": f"closed_loop/{self.run_id}.csv",
                    "jsonl_path": f"serial_jsonl/{self.run_id}.jsonl",
                    "duration_s": "" if self.duration_s is None else self.duration_s,
                    "sample_interval_s": self.sample_interval_s,
                }
            )

    def _to_jsonl_packet(self, msg: dict):
        packet = dict(msg)
        sensor = dict(msg.get("sensor") or {})

        sensor.update(
            {
                "ms": first_value(msg, "ms", default=first_value(sensor, "ms")),
                "tds_voltage": first_value(msg, "tds_voltage", default=first_value(sensor, "tds_voltage")),
                "ph_voltage": first_value(msg, "voltage", "ph_voltage", default=first_value(sensor, "ph_voltage")),
                "tds_mg_l": first_value(msg, "tds_ppm", "tds_mg_l", default=first_value(sensor, "tds_mg_l")),
                "tds_slope_mg_l_min": first_value(
                    msg,
                    "tds_slope_mg_l_min",
                    default=first_value(sensor, "tds_slope_mg_l_min"),
                ),
                "ph": first_value(msg, "ph", "pH", default=first_value(sensor, "ph")),
                "ds18b20_c": first_value(msg, "temperature_c", default=first_value(sensor, "ds18b20_c")),
                "thermal_avg_c": first_value(
                    msg,
                    "thermal_avg_c",
                    "mlx90640_avg_temp_c",
                    default=first_value(sensor, "thermal_avg_c"),
                ),
                "thermal_max_c": first_value(
                    msg,
                    "thermal_max_c",
                    default=first_value(sensor, "thermal_max_c"),
                ),
                "thermal_min_c": first_value(
                    msg,
                    "thermal_min_c",
                    default=first_value(sensor, "thermal_min_c"),
                ),
                "thermal_gradient_c": first_value(
                    msg,
                    "thermal_gradient_c",
                    default=first_value(sensor, "thermal_gradient_c"),
                ),
                "spectral_intensity": first_value(
                    msg,
                    "as7341_intensity",
                    default=first_value(sensor, "spectral_intensity"),
                ),
                "absorbance": first_value(
                    msg,
                    "absorbance_au",
                    "absorbance",
                    default=first_value(sensor, "absorbance"),
                ),
                "concentration_mg_l": first_value(
                    msg,
                    "concentration_mg_l",
                    "concentration",
                    default=first_value(sensor, "concentration_mg_l"),
                ),
                "color_rate_per_s": first_value(
                    msg,
                    "as7341_rate",
                    default=first_value(sensor, "color_rate_per_s"),
                ),
                "tof_distance_mm": first_value(
                    msg,
                    "tof_distance_mm",
                    default=first_value(sensor, "tof_distance_mm"),
                ),
                "tof_confidence": first_value(
                    msg,
                    "tof_confidence",
                    default=first_value(sensor, "tof_confidence"),
                ),
                "ambient_temp_c": first_value(
                    msg,
                    "bme280_temperature_c",
                    default=first_value(sensor, "ambient_temp_c"),
                ),
                "humidity_pct": first_value(
                    msg,
                    "bme280_humidity_percent",
                    default=first_value(sensor, "humidity_pct"),
                ),
                "pressure_hpa": first_value(
                    msg,
                    "bme280_pressure_hpa",
                    default=first_value(sensor, "pressure_hpa"),
                ),
                "reagent_volume_ml": first_value(
                    msg,
                    "dosing_volume_ml",
                    default=first_value(sensor, "reagent_volume_ml"),
                ),
            }
        )
        tds = first_value(sensor, "tds_mg_l")
        device_ms = first_value(msg, "ms", default=first_value(sensor, "ms"))
        if first_value(sensor, "tds_slope_mg_l_min") is None and tds is not None and device_ms is not None:
            if self._last_tds_mg_l is not None and self._last_tds_ms is not None and device_ms > self._last_tds_ms:
                sensor["tds_slope_mg_l_min"] = (
                    (tds - self._last_tds_mg_l) * 60000.0 / (device_ms - self._last_tds_ms)
                )
            self._last_tds_mg_l = tds
            self._last_tds_ms = device_ms
        sensor["conductivity_uS_cm"] = first_value(
            msg,
            "conductivity_uS_cm",
            default=first_value(sensor, "conductivity_uS_cm", default=(tds * 2.0 if tds is not None else None)),
        )
        sensor["ambient_lux"] = first_value(msg, "ambient_lux", default=first_value(sensor, "ambient_lux"))
        sensor["flow_coeff"] = first_value(msg, "flow_coeff", default=first_value(sensor, "flow_coeff", default=1.0))

        packet["version"] = first_value(packet, "version", default="code_v2_paper_dataset")
        packet["local_time"] = datetime.now().isoformat(timespec="milliseconds")
        packet["host_time_s"] = time.time()
        packet["run_id"] = self.run_id
        packet["group"] = self.group
        packet["repeat"] = self.repeat
        packet["mode"] = first_value(packet, "mode", "control_mode", default=self.control_mode)
        packet["reason"] = first_value(packet, "reason", "event", default=packet["mode"])
        packet["auto_enabled"] = first_value(packet, "auto_enabled", default=True)
        packet["target_ph_low"] = first_value(packet, "target_ph_low", default=self.target_ph_low)
        packet["target_ph_high"] = first_value(packet, "target_ph_high", default=self.target_ph_high)
        packet["target_tds_mg_l"] = first_value(packet, "target_tds_mg_l", "target_tds_mg_L", default=self.target_tds_mg_l)
        packet["target_tds_mg_L"] = packet["target_tds_mg_l"]
        packet["target_concentration_mg_l"] = first_value(
            packet,
            "target_concentration_mg_l",
            "target_concentration_mg_L",
            default=self.target_concentration_mg_l,
        )
        packet["target_concentration_mg_L"] = packet["target_concentration_mg_l"]
        packet["atomizer_percent"] = first_value(
            packet,
            "atomizer_percent",
            default=first_value(packet, "pwm1_percent"),
        )
        packet["sensor"] = sensor
        packet["ph"] = first_value(packet, "ph", default=first_value(sensor, "ph"))
        packet["temperature_c"] = first_value(packet, "temperature_c", default=first_value(sensor, "ds18b20_c"))
        packet["voltage"] = first_value(packet, "voltage", default=first_value(sensor, "ph_voltage"))
        return packet

    def _to_csv_row(self, packet: dict):
        sensor = packet.get("sensor") if isinstance(packet.get("sensor"), dict) else {}
        slider = packet.get("slider") if isinstance(packet.get("slider"), dict) else {}
        device_ms = first_value(packet, "ms", default=first_value(sensor, "ms"))
        elapsed_s = (
            round(float(device_ms) / 1000.0, 3)
            if device_ms is not None
            else round(time.time() - self.start_host_time, 3)
        )
        tds = first_value(sensor, "tds_mg_l")

        return {
            "group": self.group,
            "repeat": self.repeat,
            "run_id": self.run_id,
            "time_s": elapsed_s,
            "device_ms": number_or_blank(device_ms),
            "pH": number_or_blank(first_value(sensor, "ph")),
            "TDS_mg_L": number_or_blank(tds),
            "conductivity_uS_cm": number_or_blank(first_value(sensor, "conductivity_uS_cm")),
            "water_temp_C": number_or_blank(first_value(sensor, "ds18b20_c")),
            "spectral_intensity": number_or_blank(first_value(sensor, "spectral_intensity")),
            "absorbance": number_or_blank(first_value(sensor, "absorbance")),
            "estimated_concentration_mg_L": number_or_blank(first_value(sensor, "concentration_mg_l")),
            "tof_distance_mm": number_or_blank(first_value(sensor, "tof_distance_mm")),
            "pump_duty_pct": number_or_blank(first_value(packet, "pump_percent")),
            "reagent_volume_mL": number_or_blank(first_value(sensor, "reagent_volume_ml")),
            "control_mode": first_value(packet, "mode", "control_mode", default="manual"),
            "event": first_value(packet, "event", default=""),
            "micro_dosing_active": first_value(packet, "micro_dosing_active", default=False),
            "safety_active": first_value(packet, "safety_active", default=False),
            "target_ph_low": number_or_blank(first_value(packet, "target_ph_low")),
            "target_ph_high": number_or_blank(first_value(packet, "target_ph_high")),
            "target_tds_mg_L": number_or_blank(first_value(packet, "target_tds_mg_l")),
            "target_concentration_mg_L": number_or_blank(first_value(packet, "target_concentration_mg_l")),
            "ph_voltage_V": number_or_blank(first_value(sensor, "ph_voltage")),
            "tds_voltage_V": number_or_blank(first_value(sensor, "tds_voltage")),
            "thermal_gradient_C": number_or_blank(first_value(sensor, "thermal_gradient_c")),
            "ambient_temp_C": number_or_blank(first_value(sensor, "ambient_temp_c")),
            "humidity_pct": number_or_blank(first_value(sensor, "humidity_pct")),
            "pressure_hPa": number_or_blank(first_value(sensor, "pressure_hpa")),
            "ambient_lux": number_or_blank(first_value(sensor, "ambient_lux")),
            "tof_confidence": number_or_blank(first_value(sensor, "tof_confidence")),
            "flow_coeff": number_or_blank(first_value(sensor, "flow_coeff")),
            "slider_pos_steps": number_or_blank(first_value(slider, "pos")),
            "host_time_s": round(first_value(packet, "host_time_s", default=time.time()), 3),
        }
