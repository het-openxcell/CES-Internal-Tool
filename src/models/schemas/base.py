import pydantic
from pydantic import ConfigDict


class BaseSchemaModel(pydantic.BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        validate_assignment=True,
    )
