"""Interactive echogram cutoff viewer for a single Svea 2026 raw file.

Examples:
    python3 testing/svea2026_echopype_probe/cut_off_visualization.py /../../../../../../Volumes/JHS-SSD2/RUTSPRAS_2026/raw//D20260214-T172041.raw --channel-index 1 --lower -115 --upper -25 --show --save-out testing/svea2026_echopype_probe/preview.png

The script prints Sv distribution stats and shows/saves a viridis echogram using
fixed or auto-derived color limits.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "lib") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "lib"))

from processing import extract_meta_data, process_data  # noqa: E402


DEFAULT_PARAMS = REPO_ROOT / "postprocessing" / "svea2026" / "params.yaml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Preview one raw file with tunable echogram cutoffs.")
    parser.add_argument("raw_file", type=Path, help="Path to a single .raw file")
    parser.add_argument("--channel-index", type=int, default=0, help="Index of the processed channel to preview")
    parser.add_argument("--lower", type=float, default=None, help="Lower dB bound for the color scale")
    parser.add_argument("--upper", type=float, default=None, help="Upper dB bound for the color scale")
    parser.add_argument("--save-out", type=Path, default=None, help="Optional output path for the preview PNG")
    parser.add_argument("--show", action="store_true", help="Open an interactive matplotlib window")
    return parser.parse_args()


def load_params() -> dict:
    with DEFAULT_PARAMS.open("r", encoding="utf-8") as params_file:
        return list(yaml.safe_load_all(params_file))[0]


def summarize_values(values: np.ndarray) -> None:
    finite = values[np.isfinite(values)]
    nonzero = finite[finite != 0]
    source = nonzero if nonzero.size else finite

    print(f"count_finite: {finite.size}")
    print(f"count_nonzero: {nonzero.size}")
    print(f"min: {float(np.min(source)):.3f}")
    print(f"p01: {float(np.percentile(source, 1)):.3f}")
    print(f"p02: {float(np.percentile(source, 2)):.3f}")
    print(f"p05: {float(np.percentile(source, 5)):.3f}")
    print(f"p10: {float(np.percentile(source, 10)):.3f}")
    print(f"median: {float(np.median(source)):.3f}")
    print(f"p90: {float(np.percentile(source, 90)):.3f}")
    print(f"p95: {float(np.percentile(source, 95)):.3f}")
    print(f"p98: {float(np.percentile(source, 98)):.3f}")
    print(f"p99: {float(np.percentile(source, 99)):.3f}")
    print(f"max: {float(np.max(source)):.3f}")
    print(f"mean: {float(np.mean(source)):.3f}")
    print(f"std: {float(np.std(source)):.3f}")


def prepare_echogram(raw_file: Path, channel_index: int) -> tuple[np.ndarray, dict]:
    params = load_params()
    raw_echodata, channels, _longitude, _latitude, transmit_types = extract_meta_data(str(raw_file))

    if channel_index < 0 or channel_index >= len(channels):
        raise IndexError(f"channel-index {channel_index} is out of range for {len(channels)} channels")

    transmit_type = transmit_types[channel_index][0] if hasattr(transmit_types[channel_index], "__len__") else transmit_types[channel_index]
    ds_mvbs, _ping_times = process_data(
        str(raw_file),
        params["env_params"],
        params["cal_params"],
        params["bin_size"],
        transmit_type,
    )

    echogram = ds_mvbs.Sv.to_numpy()[channel_index]
    echogram = np.swapaxes(echogram, 0, 1)
    metadata = {
        "channels": channels,
        "transmit_types": transmit_types,
        "selected_channel": channels[channel_index],
        "selected_transmit": transmit_type,
    }
    return echogram, metadata


def plot_echogram(data: np.ndarray, lower: float, upper: float, title: str, save_out: Path | None, show: bool) -> None:
    fig, ax = plt.subplots(figsize=(14, 7), constrained_layout=True)
    image = ax.imshow(data, aspect="auto", cmap="viridis", vmin=lower, vmax=upper, origin="upper")
    ax.set_title(title)
    ax.set_xlabel("Ping")
    ax.set_ylabel("Range bin")
    fig.colorbar(image, ax=ax, label="Sv (dB)")

    if save_out is not None:
        save_out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_out, dpi=180)
        print(f"saved: {save_out}")

    if show:
        plt.show()
    else:
        plt.close(fig)


def main() -> int:
    args = parse_args()
    raw_file = args.raw_file.expanduser().resolve()
    if not raw_file.exists():
        print(f"File not found: {raw_file}")
        return 1

    echogram, metadata = prepare_echogram(raw_file, args.channel_index)
    print(f"raw_file: {raw_file.name}")
    print(f"selected_channel: {metadata['selected_channel']}")
    print(f"selected_transmit: {metadata['selected_transmit']}")
    print(f"echogram_shape: {echogram.shape}")
    summarize_values(echogram)

    lower = args.lower
    upper = args.upper
    if lower is None or upper is None:
        valid = echogram[np.isfinite(echogram)]
        valid = valid[valid != 0]
        if valid.size == 0:
            valid = echogram[np.isfinite(echogram)]
        lower = float(np.percentile(valid, 2)) if lower is None else lower
        upper = float(np.percentile(valid, 98)) if upper is None else upper
        print(f"auto_bounds: lower={lower:.3f}, upper={upper:.3f}")
    else:
        print(f"fixed_bounds: lower={lower:.3f}, upper={upper:.3f}")

    title = f"{raw_file.name} | {metadata['selected_channel']} | {lower:.1f} to {upper:.1f} dB"
    plot_echogram(echogram, lower, upper, title, args.save_out, args.show)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
