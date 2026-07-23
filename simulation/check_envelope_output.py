#!/usr/bin/env python3
"""Deterministic envelope, wake, and raw-mux contract check for issue #93."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "simulation" / "envelope-output-contract.json"

def main() -> int:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    failures: list[str] = []
    for key in ("rectifier", "comparator", "mux"):
        value = data.get("sources", {}).get(key, "")
        if "datasheet" not in value.lower() and "TODO(#" not in value:
            failures.append(f"missing source/TODO for {key}")
    required_nodes = {"LEVEL_ENVELOPE", "WAKE_N", "RAW_N", "LEVEL"}
    missing_nodes = required_nodes - set(data.get("nodes", {}))
    if missing_nodes:
        failures.append("missing nodes: " + ", ".join(sorted(missing_nodes)))
    envelope = data["envelope"]
    output = envelope["gain"] * envelope["full_scale_input_peak_v"]
    attack_90 = -math.log(0.1) * envelope["attack_tau_s"]
    release_tau = envelope["release_tau_s"]
    if output > envelope["maximum_output_v"]:
        failures.append(f"full-scale envelope {output:.3f} V exceeds {envelope['maximum_output_v']:.3f} V")
    if not 0.001 <= attack_90 <= 0.005:
        failures.append(f"attack 90% time {attack_90 * 1000:.2f} ms outside 1-5 ms")
    if not 0.1 <= release_tau <= 0.3:
        failures.append(f"release time constant {release_tau * 1000:.0f} ms outside 100-300 ms")
    wake = data["wake"]
    worst_trip = wake["nominal_trip_v"] + wake["offset_max_v"] + wake["hysteresis_v"] / 2
    for rail in data["corners"]["host_rail_v"]:
        high_level = rail - wake["pullup_ohm"] * wake["off_leakage_max_a"]
        if high_level < 0.7 * rail:
            failures.append(f"{rail:.1f} V open-drain high level {high_level:.3f} V is not valid")
    if worst_trip >= wake["firmware_68db_min_v"]:
        failures.append(f"worst coarse trip {worst_trip:.4f} V reaches 68 dB firmware floor")
    mux = data["mux"]
    mux_tau = (mux["on_resistance_max_ohm"] + mux["source_impedance_max_ohm"]) * mux["load_cap_f"]
    if 5 * mux_tau > mux["settle_max_s"]:
        failures.append("mux RC settling exceeds mux settle contract")
    if mux["host_discard_s"] < mux["settle_max_s"]:
        failures.append("host raw-mode discard is shorter than mux settling contract")
    if failures:
        print("envelope/output validation failed:")
        print("\n".join(f"- {failure}" for failure in failures))
        return 1
    print(f"envelope/output validation passed: output={output:.3f} V attack90={attack_90 * 1000:.2f} ms worst_trip={worst_trip * 1000:.2f} mV")
    return 0

if __name__ == "__main__":
    sys.exit(main())
