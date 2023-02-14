from pydantic.main import BaseModel as PydanticBaseModel
from pydantic.main import ModelMetaclass as PydanticModelMetaclass


class ModelMetaclass(PydanticModelMetaclass):
    def __call__(cls, *args, **kwargs):
        if getattr(cls, "__validate__", False):
            obj = super().__call__(*args, **kwargs)
        else:
            obj = cls.construct(*args, **kwargs)

        cls.__post_init__(obj)

        return obj


class BaseModel(PydanticBaseModel, metaclass=ModelMetaclass):
    class Config:
        arbitrary_types_allowed = True
        extra = "allow"

    def __post_init__(self):
        """
        Things to do immediately after initialization.

        This method does nothing here but can be overriden in subclasses.
        """

    def __init_subclass__(cls, validate: bool = False, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.__validate__ = validate
