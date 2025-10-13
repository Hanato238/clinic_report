from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Set, Tuple

DEFAULT_ALLOWED_SIZES = {(525, 525), (525, 526), (526, 525), (526, 526)}
DEFAULT_RENAME_MAP = {
    "0-0": "frontal_1_left",
    "0-1": "mid",
    "0-2": "vertex_center",
    "1-0": "occipital",
}

@dataclass(frozen=True)
class ExtractorConfig:
    allowed_sizes: Set[Tuple[int, int]] = field(default_factory=lambda: set(DEFAULT_ALLOWED_SIZES))
    rename_map: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_RENAME_MAP))

@dataclass(frozen=True)
class PipelineConfig:
    # 出力: None なら PDF と同じディレクトリに temp_YYYYMMDD 作成
    out_root: str | None = None
    # 画像の一時生ファイルは消す
    remove_raw_images: bool = True
