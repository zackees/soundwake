#!/usr/bin/env python3
"""Deterministic front-end contract check for FastLED/soundwave#92."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "simulation" / "front-end-contract.json"


def gain(rg: float, rf: float) -> float:
    return 1.0 + rf / rg


def corner(value: float, tolerance: float, high: bool) -> float:
    return value * (1.0 + tolerance if high else 1.0 - tolerance)


def main() -> int:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    f = data["front_end"]
    rail = data["mic_rail"]
    corners = data["corners"]
    failures: list[str] = []
    sources = data.get("sources", {})
    for name in ("microphone", "mic_ldo", "op_amp", "passives"):
        if not sources.get(name) or ("datasheet" not in sources[name].lower() and "TODO(#" not in sources[name]):
            failures.append(f"missing source/TODO for {name}")
    for node in ("MIC_2V0", "MIC_OUT", "PREAMP_BIAS", "PREAMP_OUT", "LEVEL"):
        if node not in data.get("nodes", {}):
            failures.append(f"missing required netlist node {node}")
    tolerance = corners["passive_tolerance"]
    nominal_gain = gain(f["preamp_rg_ohm"], f["preamp_rf_ohm"])
    gain_low = gain(corner(f["preamp_rg_ohm"], tolerance, True), corner(f["preamp_rf_ohm"], tolerance, False))
    gain_high = gain(corner(f["preamp_rg_ohm"], tolerance, False), corner(f["preamp_rf_ohm"], tolerance, True))
    lp_low = 1.0 / (2.0 * math.pi * corner(f["preamp_rf_ohm"], tolerance, True) * corner(f["preamp_cf_f"], tolerance, True))
    lp_high = 1.0 / (2.0 * math.pi * corner(f["preamp_rf_ohm"], tolerance, False) * corner(f["preamp_cf_f"], tolerance, False))
    hp_low = 1.0 / (2.0 * math.pi * corner(f["coupling_r_ohm"], tolerance, True) * corner(f["coupling_c_f"], tolerance, True))
    hp_high = 1.0 / (2.0 * math.pi * corner(f["coupling_r_ohm"], tolerance, False) * corner(f["coupling_c_f"], tolerance, False))
    if not 7.7 <= nominal_gain <= 8.1 or gain_low < 7.6 or gain_high > 8.3:
        failures.append(f"preamp gain out of contract: {gain_low:.3f}-{gain_high:.3f}")
    if not 3800.0 <= lp_low <= 4300.0 or not 3800.0 <= lp_high <= 4300.0:
        failures.append(f"low-pass corner out of contract: {lp_low:.1f}-{lp_high:.1f} Hz")
    if not 45.0 <= hp_low <= 55.0 or not 45.0 <= hp_high <= 55.0:
        failures.append(f"high-pass corner out of contract: {hp_low:.1f}-{hp_high:.1f} Hz")
    mic_pin = rail["target_v"] - rail["post_ldo_r_ohm"] * rail["load_max_a"]
    for host_rail in corners["host_rail_v"]:
        if host_rail - rail["target_v"] < rail["dropout_max_v"]:
            failures.append(f"{host_rail:.3f} V host rail does not meet mic-LDO dropout contract")
        if mic_pin < rail["minimum_pin_v"]:
            failures.append(f"mic pin {mic_pin:.3f} V is below its minimum contract")
        bias = host_rail * f["preamp_bias_fraction"]
        for sensitivity in corners["mic_sensitivity_dbv"]:
            mic_peak = f["microphone_peak_v_at_full_scale"] * 10.0 ** ((sensitivity + 42.0) / 20.0)
            swing = mic_peak * gain_high
            if bias - swing < f["preamp_required_rail_margin_v"] or host_rail - (bias + swing) < f["preamp_required_rail_margin_v"]:
                failures.append(f"{host_rail:.3f} V / {sensitivity:.1f} dBV corner clips preamp: swing={swing:.3f} V")
    if failures:
        print("front-end validation failed:")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1
    print(
        "front-end validation passed: "
        f"gain={nominal_gain:.3f} ({gain_low:.3f}-{gain_high:.3f}), "
        f"band={hp_low:.1f}-{lp_high:.1f} Hz, mic_pin={mic_pin:.3f} V"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
