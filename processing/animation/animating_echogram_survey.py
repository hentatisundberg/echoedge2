"""Create a survey-specific echogram animation.

The input YAML document must contain at least:

    db_path: metadatabase/sailbuoy_metadatabase.db
    survey_id: SAILOR1_2018_001
    img_dir: /path/to/images
    filename_pattern: "*clean.png"
    save_path: /path/to/animation/
    img_height: 1000
    target_width: 3000
    max_images: 0
    x_shrink_factor: 1.0
    fps: 1


RUN EXAMPLE: 

python processing/animation/animating_echogram_survey.py processing/animation/config/params_animation_survey.yaml

Image timestamps are read from names containing ``DYYYYMMDD-THHMMSS`` or
``YYYYMMDDTHHMMSS``. If no timestamp is present, the script matches the image
to ``file_processing_metadata.file_name`` and uses its first timestamp.
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import re
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import cv2
try:
    import moviepy.editor as mpy
except ImportError:
    import moviepy as mpy
import yaml
from yaml.loader import SafeLoader


TIMESTAMP_PATTERNS = (
    re.compile(r"D(?P<date>\d{8})[-_]?T(?P<time>\d{6})", re.IGNORECASE),
    re.compile(r"(?P<date>\d{8})T(?P<time>\d{6})", re.IGNORECASE),
)


@dataclass(frozen=True)
class ImageRecord:
    path: Path
    timestamp: dt.datetime
    width: int


def parse_timestamp(value: str) -> dt.datetime:
    """Parse a database timestamp and return a timezone-aware UTC datetime."""

    normalized = value.strip().replace("Z", "+00:00")
    timestamp = dt.datetime.fromisoformat(normalized)
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=dt.timezone.utc)
    return timestamp.astimezone(dt.timezone.utc)


def timestamp_from_name(name: str) -> Optional[dt.datetime]:
    for pattern in TIMESTAMP_PATTERNS:
        match = pattern.search(name)
        if match:
            return dt.datetime.strptime(
                f"{match.group('date')}{match.group('time')}", "%Y%m%d%H%M%S"
            ).replace(tzinfo=dt.timezone.utc)
    return None


def load_config(config_path: Path) -> dict:
    with config_path.open(encoding="utf-8") as config_file:
        config = yaml.load(config_file, Loader=SafeLoader)
    if not isinstance(config, dict):
        raise ValueError("The YAML configuration must contain one mapping.")
    required = ("db_path", "survey_id", "img_dir", "filename_pattern")
    missing = [key for key in required if key not in config]
    if missing:
        raise ValueError(f"Missing configuration keys: {', '.join(missing)}")
    return config


def load_survey(
    connection: sqlite3.Connection, survey_id: str
) -> tuple[str, dt.datetime, dt.datetime]:
    row = connection.execute(
        """
        SELECT platform, start_time, end_time
        FROM survey_summary
        WHERE survey_id = ?
        """,
        (survey_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Survey {survey_id!r} was not found in survey_summary.")
    if not row[1] or not row[2]:
        raise ValueError(f"Survey {survey_id!r} has no complete start/end interval.")
    return row[0], parse_timestamp(row[1]), parse_timestamp(row[2])


def load_file_metadata(
    connection: sqlite3.Connection, platform: str
) -> list[tuple[str, dt.datetime]]:
    rows = connection.execute(
        """
        SELECT file_name, first_timestamp_utc
        FROM file_processing_metadata
        WHERE platform = ? AND first_timestamp_utc IS NOT NULL
        """,
        (platform,),
    ).fetchall()
    return [(row[0], parse_timestamp(row[1])) for row in rows]


def metadata_timestamp(
    image_path: Path, metadata: Iterable[tuple[str, dt.datetime]]
) -> Optional[dt.datetime]:
    """Find the most specific raw-file name contained in an image name."""

    image_name = image_path.name.lower()
    image_stem = image_path.stem.lower()
    matches = []
    for file_name, timestamp in metadata:
        raw_name = Path(file_name).name.lower()
        raw_stem = Path(raw_name).stem
        if raw_name in image_name or raw_stem in image_stem:
            matches.append((len(raw_stem), timestamp))
    return max(matches, default=(0, None))[1]


def find_images(
    config: dict,
    platform: str,
    survey_start: dt.datetime,
    survey_end: dt.datetime,
    metadata: list[tuple[str, dt.datetime]],
) -> list[ImageRecord]:
    image_dir = Path(config["img_dir"]).expanduser()
    pattern = config["filename_pattern"]
    paths = sorted(Path(path) for path in glob.glob(str(image_dir / pattern)))
    if not paths:
        raise ValueError(f"No images matched {image_dir / pattern}.")

    image_height = int(config.get("img_height", 1000))
    records = []
    unmatched = 0
    for path in paths:
        timestamp = timestamp_from_name(path.name)
        if timestamp is None:
            timestamp = metadata_timestamp(path, metadata)
        if timestamp is None:
            unmatched += 1
            continue
        if not survey_start <= timestamp <= survey_end:
            continue
        image = cv2.imread(str(path))
        if image is None:
            print(f"Warning: unable to read {path}; skipping")
            continue
        height, width = image.shape[:2]
        if width <= 10 or height != image_height:
            continue
        records.append(ImageRecord(path, timestamp, width))

    if unmatched:
        print(f"Warning: {unmatched} matching images had no usable timestamp; skipped")
    records.sort(key=lambda record: (record.timestamp, record.path.name))
    if not records:
        raise ValueError("No valid images fall within the selected survey interval.")

    max_images = int(config.get("max_images", 0))
    if max_images < 0:
        raise ValueError("max_images must be zero (unlimited) or a positive integer.")
    if max_images and len(records) > max_images:
        if max_images == 1:
            records = [records[0]]
        else:
            indexes = [
                round(index * (len(records) - 1) / (max_images - 1))
                for index in range(max_images)
            ]
            records = [records[index] for index in indexes]
    return records


def add_timestamp(image, first: dt.datetime, last: dt.datetime):
    label = (
        f"{first.strftime('%d %B %Y, %H:%M')} - "
        f"{last.strftime('%d %B %Y, %H:%M')}"
    )
    height, width = image.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1
    thickness = 1
    (text_width, text_height), baseline = cv2.getTextSize(
        label, font, font_scale, thickness
    )
    bottom_margin = 20
    origin = (
        max(0, (width - text_width) // 2),
        max(text_height, height - bottom_margin - baseline),
    )
    return cv2.putText(
        image,
        label,
        origin,
        font,
        font_scale,
        (0, 0, 255),
        thickness,
        cv2.LINE_AA,
    )


def write_batch(
    records: list[ImageRecord],
    output_dir: Path,
    survey_id: str,
    index: int,
    x_shrink_factor: float,
) -> Optional[Path]:
    images = [cv2.imread(str(record.path)) for record in records]
    images = [image for image in images if image is not None]
    if not images:
        print("Warning: all images in a batch failed to load; skipping batch")
        return None
    if x_shrink_factor != 1.0:
        images = [
            cv2.resize(
                image,
                (max(1, round(image.shape[1] * x_shrink_factor)), image.shape[0]),
                interpolation=cv2.INTER_AREA,
            )
            for image in images
        ]
    combined = cv2.hconcat(images)
    combined = add_timestamp(combined, records[0].timestamp, records[-1].timestamp)
    filename = (
        f"{survey_id}_{records[0].timestamp.strftime('%Y%m%dT%H%M%S')}_"
        f"{index:04d}.png"
    )
    output_path = output_dir / filename
    if not cv2.imwrite(str(output_path), combined):
        raise OSError(f"Could not write {output_path}")
    return output_path


def create_animation(records: list[ImageRecord], config: dict, work_dir: Path) -> list[Path]:
    target_width = int(config.get("target_width", 3000))
    survey_id = str(config["survey_id"])
    x_shrink_factor = float(config.get("x_shrink_factor", 1.0))
    if not 0 < x_shrink_factor <= 1:
        raise ValueError("x_shrink_factor must be greater than 0 and at most 1.")
    def output_width(record: ImageRecord) -> int:
        return max(1, round(record.width * x_shrink_factor))

    batches: list[Path] = []
    current: list[ImageRecord] = []
    current_width = 0
    for record in records:
        record_width = output_width(record)
        if current and current_width + record_width > target_width:
            output = write_batch(
                current,
                work_dir / "added",
                survey_id,
                len(batches),
                x_shrink_factor,
            )
            if output:
                batches.append(output)
            current = []
            current_width = 0
        current.append(record)
        current_width += record_width

    minimum_fraction = float(config.get("minimum_final_batch_fraction", 0.5))
    if current and (
        not batches or current_width >= target_width * minimum_fraction
    ):
        output = write_batch(
            current,
            work_dir / "added",
            survey_id,
            len(batches),
            x_shrink_factor,
        )
        if output:
            batches.append(output)
    elif current:
        print(f"Skipped final batch with width {current_width} (less than {minimum_fraction:.0%})")

    if not batches:
        raise ValueError("No concatenated image batches were produced.")

    crop_width = min(cv2.imread(str(path)).shape[1] for path in batches)
    cropped = []
    for index, path in enumerate(batches):
        image = cv2.imread(str(path))
        output = work_dir / "added_cropped" / f"{index:04d}.png"
        if not cv2.imwrite(str(output), image[:, :crop_width]):
            raise OSError(f"Could not write {output}")
        cropped.append(output)
    return cropped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="YAML animation configuration")
    args = parser.parse_args()
    config = load_config(args.config)

    db_path = Path(config["db_path"]).expanduser()
    with sqlite3.connect(db_path) as connection:
        platform, survey_start, survey_end = load_survey(
            connection, str(config["survey_id"])
        )
        metadata = load_file_metadata(connection, platform)

    records = find_images(config, platform, survey_start, survey_end, metadata)
    print(
        f"Selected {len(records)} images for {config['survey_id']} "
        f"({platform}, {survey_start.isoformat()} to {survey_end.isoformat()})"
    )

    survey_id = str(config["survey_id"])
    work_dir = Path(config.get("work_dir", "dump/animation")) / survey_id
    if work_dir.exists():
        shutil.rmtree(work_dir)
    (work_dir / "added").mkdir(parents=True)
    (work_dir / "added_cropped").mkdir()
    cropped = create_animation(records, config, work_dir)

    output_stem = f"{survey_id}_animated"
    dump_dir = Path(config.get("dump_path", "dump"))
    dump_dir.mkdir(parents=True, exist_ok=True)
    gif_path = dump_dir / f"{output_stem}.gif"
    clip = mpy.ImageSequenceClip([str(path) for path in cropped], fps=int(config["fps"]))
    clip.write_gif(str(gif_path))

    save_path = Path(config.get("save_path", dump_dir)).expanduser()
    save_path.mkdir(parents=True, exist_ok=True)
    clip.write_videofile(str(save_path / f"{output_stem}.mp4"))
    print(f"GIF written to {gif_path}")
    print(f"MP4 written to {save_path / f'{output_stem}.mp4'}")


if __name__ == "__main__":
    main()
