from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    artifacts_dir: Path = Field(default=Path("artifacts"))
    watches_dir: Path = Field(default=Path(".dra") / "watches")
    app_name: str = Field(default="DeepResearch Agent")
