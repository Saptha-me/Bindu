from __future__ import annotations

from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class pebbleSettings(BaseSettings):
    env: str = "dev"
    title: str = "pebble"
    cors_origin_list: Optional[List[str]] = Field(None, validate_default=True)
