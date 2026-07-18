from pydantic import BaseModel, Field


class AnalysisCreate(BaseModel):
    dataset_id: str
    prompt: str = Field(min_length=3, max_length=4000)
