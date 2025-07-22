# |--------------------------------------------------|
# |                                                  |
# |           Give Feedback / Get Help               |
# | https://github.com/Pebbling-ai/pebble/issues/new |
# |                                                  |
# |--------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

from pydantic import BaseModel, ConfigDict


class PebblingProtocolBaseModel(BaseModel):
    """Pebbling Protocol data models.

    Provides a common configuration (e.g., alias-based population) and
    serves as the foundation for future extensions or shared utilities.
    """

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)
