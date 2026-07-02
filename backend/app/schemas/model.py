from pydantic import BaseModel


class ModelInfo(BaseModel):
    id: str
    object: str
    created: int
    owned_by: str


class ModelsResponse(BaseModel):
    object: str
    data: list[ModelInfo]
