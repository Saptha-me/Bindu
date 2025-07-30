import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional, Union

from pydantic import AnyUrl, BaseModel, ConfigDict, Field
from pydantic.json_schema import SkipJsonSchema

class SecurityConfig(BaseModel):
    """Security configuration for an agent."""
    did_required: bool = False
    private_key_pem_location: str | None = None
    public_key_pem_location: str | None = None
    recreate_keys: bool = False
    create_csr: bool = False
    ca: str = "sheldon"
    csr_location: str | None = None
