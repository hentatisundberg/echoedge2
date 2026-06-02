"""Minimal Echopype probe for Svea 2026 raw files.

Usage:
    python inspect_raw.py /path/to/file.raw

This script opens a single raw file, prints key metadata, and tries a
lowercase-second MVBS bin so it works with pandas 3.x.
"""

from __future__ import annotations

import sys
from pathlib import Path

import echopype as ep
import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PARAMS = REPO_ROOT / "postprocessing" / "svea2026" / "params.yaml"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python inspect_raw.py /path/to/file.raw")
        return 1

    raw_file = Path(sys.argv[1]).expanduser().resolve()
    if not raw_file.exists():
        print(f"File not found: {raw_file}")
        return 1

    params_path = DEFAULT_PARAMS
    with params_path.open("r", encoding="utf-8") as params_file:
        params = list(yaml.safe_load_all(params_file))[0]

    raw_echodata = ep.open_raw(raw_file, sonar_model="EK80")

    print("platform.channel:", raw_echodata.platform.channel.to_numpy())
    print("beam.transmit_type:", raw_echodata.beam.transmit_type.to_numpy())
    print("platform.longitude sample:", raw_echodata.platform.longitude.to_numpy()[:5])
    print("platform.latitude sample:", raw_echodata.platform.latitude.to_numpy()[:5])

    if hasattr(raw_echodata, "sonar_model"):
        print("sonar_model:", raw_echodata.sonar_model)

    ds_sv_raw = ep.calibrate.compute_Sv(
        raw_echodata,
        env_params=params["env_params"],
        cal_params=params["cal_params"],
        waveform_mode="CW",
        encode_mode="complex",
    )
    print("Sv dims:", ds_sv_raw.Sv.dims)

    try:
        ds_mvbs = ep.commongrid.compute_MVBS(
            ds_sv_raw,
            range_bin="1m",
            ping_time_bin="2s",
        )
        print("MVBS dims:", ds_mvbs.Sv.dims)
        print("ping_time sample:", ds_mvbs.Sv.ping_time.values[:5])
    except Exception as exc:
        print("MVBS failed:", type(exc).__name__, exc)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
