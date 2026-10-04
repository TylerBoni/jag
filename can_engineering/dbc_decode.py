"""Decode hs_bus.dbc signals into friendly readings (via cantools)."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import cantools
from cantools.database import Message

_SKIP_RE = re.compile(
    r"(Counter|Checksum|Complement|Mux_|VIN_SEGMENT|Field\d|DerivedNibble|"
    r"FrameCounter|Status_01|Alive|Byte\d|Reserved|b7$|Alt$)",
    re.I,
)

_FRIENDLY_MSG = {
    "ECM_RPM": "Engine speed",
    "ChargingSystemFault": "Charging system",
    "ThrottlePosition": "Throttle",
    "AirTemperature": "Outside air temp",
    "IPC_EngineTemperatureWarnings": "Engine temp warnings",
    "ECM_Faults": "Engine warnings",
    "ASL_Faults": "Check-engine / ASL",
    "ECM_ETM_Status": "Engine module status",
    "ABS_WheelSpeed": "Vehicle speed",
    "ABS_DSCStatus": "Stability control",
    "ABS_EBDStatus": "Brake system",
    "TSM_GearPosition": "Gear position",
    "IPC_DoorStatus": "Doors",
    "IPC_RTCClock": "Battery / clock",
    "IPC_BatteryCurrentRelay": "Battery charge current",
    "TransmissionOilTemp": "Gearbox oil temp",
    "SteeringAngle": "Steering",
    "WheelSpeeds_Front": "Front wheels",
    "WheelSpeeds_Rear": "Rear wheels",
    "EPB_ParkBrakeWarnings": "Park brake",
    "RCM_AirbagSeatbelt": "Airbag / seatbelt",
    "GSM_KnobStatus": "Gear selector",
    "BatteryNotCharging_WarningGate": "Battery charging",
    "ADCM_ETM_Status": "Suspension module",
    "CoolantTemp": "Coolant",
}

_FRIENDLY_SIG = {
    "c_RPM_Raw": "RPM",
    "i_VehicleSpeed": "Speed",
    "i_BrakePressure": "Brake pressure",
    "i_ThrottlePosition": "Throttle",
    "i_AirTemperature": "Air temperature",
    "i_OilTemperature": "Engine / coolant temp",
    "i_TransmissionOilTemp": "Gearbox oil temp",
    "c_BatteryVoltage_Relay": "Battery voltage",
    "c_BatteryChargingCurrent_Relay": "Charge current",
    "i_ChargingFault_Byte0": "Charging fault bit",
    "c_CheckEngineLight_Indicator": "Check engine light",
    "c_EngineSystemFault": "Engine fault",
    "c_EngineOilLevelStatus": "Oil level",
    "c_EngineOilLevelMonitorSystemFault_Msg": "Oil level monitor",
    "c_RestrictedPerformanceRed": "Power limited (red)",
    "c_RestrictedPerformanceYellow": "Power limited (yellow)",
    "c_ParkBrakeIndicator": "Park brake light",
    "c_EBD_Fault": "Brake balance fault",
    "i_ABS_Fault": "ABS fault",
    "i_ESP_Off": "Traction control off",
    "i_ESP_Active": "Traction active",
    "c_Door_Front_Left_Closed": "Driver door closed",
    "Door_Front_Right_Closed": "Passenger door closed",
    "Door_Rear_Left_Closed": "Rear left closed",
    "Door_Rear_Right_Closed": "Rear right closed",
    "Trunk_Closed": "Trunk closed",
    "Hood_Closed": "Hood closed",
    "i_Airbag_Warning": "Airbag warning",
    "i_Seatbelt_Warning": "Seatbelt warning",
    "i_IgnitionIsOn": "Ignition on",
    "i_SteeringAngle": "Steering angle",
    "i_WheelSpeed_FL": "Front left",
    "i_WheelSpeed_FR": "Front right",
    "i_WheelSpeed_RL": "Rear left",
    "i_WheelSpeed_RR": "Rear right",
    "Mode": "Gear mode",
    "ManualGear": "Manual gear",
    "c_WaterInFuelSeeHandbook_Msg": "Water in fuel",
    "c_PleaseWaitColdStartInProgress_Msg": "Cold start wait",
    "c_ASL_Indicator": "Speed limiter",
    "c_EngineOverheat_Red": "Engine overheat",
    "c_EngineTemperatureHigh_Yellow": "Engine temp high",
    "c_ParkBrakeApplied_Red": "Park brake on",
    "c_ParkBrakeFault_Yellow": "Park brake fault",
    "c_DSC_State": "Stability mode",
}


def short_name(dbc_name: str) -> str:
    name = dbc_name
    for prefix in ("c_HS_", "i_HS_", "u_HS_", "c_", "i_", "u_"):
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break
    return re.sub(r"_0x[0-9A-Fa-f]+$", "", name)


def message_title(dbc_name: str) -> str:
    short = short_name(dbc_name)
    return _FRIENDLY_MSG.get(short, short.replace("_", " "))


def signal_label(name: str) -> str:
    if name in _FRIENDLY_SIG:
        return _FRIENDLY_SIG[name]
    bare = re.sub(r"^[ciu]_", "", name)
    if bare in _FRIENDLY_SIG:
        return _FRIENDLY_SIG[bare]
    bare = re.sub(r"([a-z])([A-Z])", r"\1 \2", bare).replace("_", " ")
    return bare.strip().capitalize()


def _to_imperial(phys: float, unit: str) -> tuple[float, str]:
    """Convert DBC metric units to F / mph / psi for display."""
    u = (unit or "").strip()
    if u in ("°C", "degC", "C"):
        return phys * 9.0 / 5.0 + 32.0, "°F"
    if u in ("km/h", "kmh", "kph"):
        return phys * 0.621371, "mph"
    if u in ("bar",):
        return phys * 14.5038, "psi"
    if u in ("kPa", "kpa"):
        return phys * 0.145038, "psi"
    return phys, u


def _format_value(name: str, value, unit: str, choices: dict | None) -> tuple[str, str, float, float, bool]:
    """Returns text, kind, bar_pct, phys_float (display units), alert."""
    unit = (unit or "").replace("degC", "°C").replace("deg/s", "°/s")
    if unit == "deg":
        unit = "°"

    # cantools NamedSignalValue (enum choice)
    if type(value).__name__ == "NamedSignalValue":
        label = str(value)
        try:
            phys = float(value.value)
        except Exception:
            phys = 0.0
        return label, "enum", 0.0, phys, False

    if isinstance(value, str):
        return value, "enum", 0.0, 0.0, False

    if choices and isinstance(value, (int, float)) and int(value) in choices:
        return str(choices[int(value)]), "enum", float(value), float(value), False

    phys = float(value)
    if isinstance(value, (int, float)) and value in (0, 1) and not unit:
        if any(w in name.lower() for w in ("fault", "warning", "closed", "on", "off", "active", "indicator", "msg", "light")):
            yes = bool(int(value))
            alert = yes and any(
                w in signal_label(name).lower()
                for w in ("fault", "warning", "check engine", "limited", "overheat")
            )
            return ("Yes" if yes else "No"), "bool", (100.0 if yes else 0.0), phys, alert

    phys, unit = _to_imperial(phys, unit)

    if abs(phys - round(phys)) < 1e-6:
        num = str(int(round(phys)))
    elif abs(phys) >= 10:
        num = f"{phys:.1f}"
    else:
        num = f"{phys:.2f}"
    text = f"{num} {unit}".strip()

    label = signal_label(name).lower()
    if "rpm" in label or unit == "rpm":
        pct = max(0.0, min(100.0, phys / 80.0))
    elif unit in ("%",):
        pct = max(0.0, min(100.0, phys))
    elif unit in ("V",):
        pct = max(0.0, min(100.0, (phys - 10) / 6 * 100))
    elif unit in ("°F",):
        pct = max(0.0, min(100.0, (phys - (-40)) / 320 * 100))  # -40–280°F-ish
    elif unit in ("mph",):
        pct = max(0.0, min(100.0, phys / 160 * 100))
    elif unit in ("psi",):
        pct = max(0.0, min(100.0, phys / 3000 * 100))
    else:
        pct = max(0.0, min(100.0, abs(phys) if abs(phys) <= 100 else 50.0))

    return text, "value", pct, phys, False


class DbcIndex:
    def __init__(self, path: str | Path):
        path = Path(path)
        raw = path.read_text(encoding="utf-8", errors="replace")
        cleaned = "\n".join(
            line for line in raw.splitlines() if not line.strip().startswith("//")
        )
        with tempfile.NamedTemporaryFile("w", suffix=".dbc", delete=False) as tmp:
            tmp.write(cleaned)
            tmp_path = tmp.name
        self._db = cantools.database.load_file(tmp_path, strict=False)
        self._titles: dict[int, str] = {}
        for msg in self._db.messages:
            self._titles[msg.frame_id] = message_title(msg.name)

    def titles(self) -> dict[int, str]:
        return dict(self._titles)

    def decode(self, arb_id: int, data: bytes) -> list[dict]:
        try:
            msg: Message = self._db.get_message_by_frame_id(arb_id)
        except KeyError:
            return []
        try:
            decoded = msg.decode(data, decode_choices=True, scaling=True)
        except Exception:
            return []

        out = []
        for name, value in decoded.items():
            if name == "i_OilTemperature":
                # XK guess (byte 6, °C+60). On this F-Type the byte is 0x00 and
                # does not move with the coolant sensor.
                continue
            if _SKIP_RE.search(name) and "RPM" not in name:
                continue
            sig = msg.get_signal_by_name(name)
            unit = getattr(sig, "unit", None) or ""
            choices = getattr(sig, "choices", None) or {}
            # cantools may already stringify choices
            text, kind, pct, phys, alert = _format_value(name, value, unit, choices)
            label = signal_label(name)
            if kind == "bool":
                alert = text == "Yes" and any(
                    w in label.lower()
                    for w in ("fault", "warning", "check engine", "limited", "overheat")
                )
            out.append(
                {
                    "key": name,
                    "label": label,
                    "text": text,
                    "kind": kind,
                    "bar_pct": pct,
                    "alert": alert,
                    "phys": phys if kind == "value" else (phys if kind == "enum" else phys),
                }
            )
        return out


def load_dbc(path: str | Path) -> DbcIndex:
    return DbcIndex(path)


def default_dbc_path() -> Path:
    return Path(__file__).resolve().parent / "hs_bus.dbc"


def load_dbc_names(path: str | Path) -> dict[int, str]:
    return load_dbc(path).titles()
