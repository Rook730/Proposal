"""Base model for everything saved to the data folder.

Forward compatibility (1.10.1): a newer version of the app may add fields to the files in the shared data
folder. Data read from a file keeps those unknown fields and writes them back unchanged on save, so an older
version never drops or rejects what a newer one wrote.

Code keeps the strictness `extra="forbid"` gave before: a keyword argument or attribute that is not a field
is still an error when it comes from our own code (constructor or assignment). Only dict / JSON validation
(model_validate, model_validate_json, nested models) accepts and keeps unknown fields.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from pydantic import BaseModel, ConfigDict

# True while data from a file or a dict is being validated (pydantic runs __init__ for nested models too)
_VALIDATING: ContextVar[bool] = ContextVar("validating_saved_data", default=False)


@contextmanager
def _validating():
    token = _VALIDATING.set(True)
    try:
        yield
    finally:
        _VALIDATING.reset(token)


class SavedModel(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="allow")

    def __init__(self, /, **data: Any) -> None:
        if not _VALIDATING.get():
            cls = type(self)
            unknown = [k for k in data if k not in cls.model_fields]
            if unknown:
                raise TypeError(f"{cls.__name__} has no field(s): {', '.join(sorted(unknown))}")
        super().__init__(**data)

    @classmethod
    def model_validate(cls, obj: Any, **kwargs: Any):
        with _validating():
            return super().model_validate(obj, **kwargs)

    @classmethod
    def model_validate_json(cls, json_data: Any, **kwargs: Any):
        with _validating():
            return super().model_validate_json(json_data, **kwargs)

    @classmethod
    def model_validate_strings(cls, obj: Any, **kwargs: Any):
        with _validating():
            return super().model_validate_strings(obj, **kwargs)

    def __setattr__(self, name: str, value: Any) -> None:
        if (not name.startswith("_") and name not in type(self).model_fields
                and name not in (self.__pydantic_extra__ or {})):
            raise ValueError(f'"{type(self).__name__}" object has no field "{name}"')
        super().__setattr__(name, value)

    @property
    def unknown_fields(self) -> dict[str, Any]:
        """Fields written by a newer version (kept and saved back, never shown or used)."""
        return dict(self.__pydantic_extra__ or {})
