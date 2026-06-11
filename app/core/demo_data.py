from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from app.core.channel_inference import summarize_channels
from app.models.sample import SampleRecord


def build_demo_samples(directory: Path, events_per_sample: int = 12_000) -> list[SampleRecord]:
    """Create a deterministic local synthetic flow-style demo batch.

    The generated samples are only for UI and workflow demonstration. They are
    not biological reference data and are not instrument output.
    """
    directory.mkdir(parents=True, exist_ok=True)
    specs = [
        ("demo_control_1", "control", "1", 1.0),
        ("demo_control_2", "control", "2", 1.08),
        ("demo_treated_1", "treated", "1", 1.75),
        ("demo_treated_2", "treated", "2", 1.92),
    ]
    samples: list[SampleRecord] = []
    for index, (sample_id, condition, replicate, fluorescence_shift) in enumerate(specs, start=1):
        frame = _demo_frame(events_per_sample, fluorescence_shift, seed=400 + index)
        path = directory / f"{sample_id}.csv"
        frame.to_csv(path, index=False)
        sample = SampleRecord(sample_id, path.name, path=path, file_type="csv", events=frame)
        sample.condition = condition
        sample.replicate = replicate
        sample.control_type = "untreated" if condition == "control" else "treated"
        sample.notes = "Synthetic local demo data; not biological reference material."
        sample.channels = summarize_channels(frame)
        _annotate_demo_channels(sample)
        samples.append(sample)
    return samples


def _demo_frame(event_count: int, fluorescence_shift: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    main_count = int(event_count * 0.82)
    debris_count = event_count - main_count
    main = rng.multivariate_normal(
        [72_000, 36_000],
        [[8_500**2, 2_700**2], [2_700**2, 5_200**2]],
        size=main_count,
    )
    debris = rng.multivariate_normal(
        [24_000, 11_000],
        [[4_500**2, 1_200**2], [1_200**2, 2_800**2]],
        size=debris_count,
    )
    scatter = np.clip(np.vstack([main, debris]), 1, None)
    fitc = rng.lognormal(mean=7.15, sigma=0.5, size=event_count) * fluorescence_shift
    pe = rng.lognormal(mean=6.75, sigma=0.58, size=event_count) * (1.0 + (fluorescence_shift - 1.0) * 0.35)
    time = np.linspace(0, 240, event_count)
    return pd.DataFrame(
        {
            "FSC-A": scatter[:, 0],
            "SSC-A": scatter[:, 1],
            "FITC-A": fitc,
            "PE-A": pe,
            "Time": time,
        }
    )


def _annotate_demo_channels(sample: SampleRecord) -> None:
    for channel in sample.channels:
        if channel.raw_name == "FITC-A":
            channel.marker = "Demo Marker A"
            channel.antibody = "Synthetic clone A"
            channel.fluorochrome = "FITC"
        elif channel.raw_name == "PE-A":
            channel.marker = "Demo Marker B"
            channel.antibody = "Synthetic clone B"
            channel.fluorochrome = "PE"
