"""bindu utilities and helper functions."""

from .capabilities import (
    add_extension_to_capabilities,
    get_x402_extension_from_capabilities,
)
from .did_utils import check_did_match, validate_did_extension
from .request_utils import handle_endpoint_errors
from .skill_loader import load_skills
from .skill_utils import find_skill_by_id

# Note: worker_utils is NOT imported here to avoid circular dependency with DID extension
# Import directly from bindu.utils.worker_utils where needed

__all__ = [
    "load_skills",
    "add_extension_to_capabilities",
    "get_x402_extension_from_capabilities",
    "find_skill_by_id",
    "handle_endpoint_errors",
    "validate_did_extension",
    "check_did_match",
]
