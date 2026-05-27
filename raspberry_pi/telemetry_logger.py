import csv
import json
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


class TelemetryLogger:
    def __init__(
        self,
        project_dir: Path,
        log_dir: Path | None = None,
        run_id: str | None = None,
        group: str = "runtime",
        repeat: int = 1,
    ):
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = run_id or f"run_{stamp}"
        self.group = group
        self.repeat = repeat
        self.start_host_time = time.time()

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

    def write(self, msg: dict):
        if not isinstance(msg, dict):
            return
        packet = self._to_jsonl_packet(msg)
        self._jsonl_file.write(json.dumps(packet, ensure_ascii=False, separators=(",", ":")) + "\n")
        self._jsonl_file.flush()
        self._writer.writerow(self._to_csv_row(packet))
        self._csv_file.flush()

    def close(self):
        self._csv_file.close()
        self._jsonl_file.close()

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
                    "duration_s": "",
                    "sample_interval_s": 1,
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
                "ph": first_value(msg, "ph", "pH", default=first_value(sensor, "ph")),
                "ds18b20_c": first_value(msg, "temperature_c", default=first_value(sensor, "ds18b20_c")),
                "thermal_avg_c": first_value(
                    msg,
                    "mlx90640_avg_temp_c",
                    default=first_value(sensor, "thermal_avg_c"),
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
        sensor["conductivity_uS_cm"] = first_value(
            msg,
            "conductivity_uS_cm",
            default=first_value(sensor, "conductivity_uS_cm", default=(tds * 2.0 if tds is not None else None)),
        )
        sensor["flow_coeff"] = first_value(msg, "flow_coeff", default=first_value(sensor, "flow_coeff"))

        packet["version"] = first_value(packet, "version", default="sh800_live_logger")
        packet["local_time"] = datetime.now().isoformat(timespec="milliseconds")
        packet["host_time_s"] = time.time()
        packet["run_id"] = self.run_id
        packet["group"] = self.group
        packet["repeat"] = self.repeat
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
            "event": first_value(packet, "event", "reason", default=""),
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
