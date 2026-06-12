from __future__ import annotations

from dataclasses import dataclass, field

from app.models.gate import GateDefinition
from app.models.qc_flag import QCFlag
from app.models.sample import SampleRecord


@dataclass
class WorkbenchSession:
    """Server-side in-memory session for local Dash use."""

    samples: dict[str, SampleRecord] = field(default_factory=dict)
    file_hashes: dict[str, str] = field(default_factory=dict)
    gates: list[GateDefinition] = field(default_factory=list)
    qc_flags: dict[str, list[QCFlag]] = field(default_factory=dict)
    comparison_rows: list[dict[str, object]] = field(default_factory=list)

    def sample_list(self) -> list[SampleRecord]:
        return list(self.samples.values())

    def selected_sample(self, sample_id: str | None) -> SampleRecord | None:
        if sample_id and sample_id in self.samples:
            return self.samples[sample_id]
        return next(iter(self.samples.values()), None)

    def all_qc_flags(self) -> list[QCFlag]:
        return [flag for flags in self.qc_flags.values() for flag in flags]

    def duplicate_sample_id(self, digest: str) -> str | None:
        """Return the loaded sample id for a file hash, if still present."""
        sample_id = self.file_hashes.get(digest)
        if sample_id in self.samples:
            return sample_id
        if sample_id is not None:
            self.file_hashes.pop(digest, None)
        return None

    def remember_file_hash(self, digest: str, sample: SampleRecord) -> None:
        """Index an uploaded file hash to the current sample id."""
        self.file_hashes[digest] = sample.sample_id
