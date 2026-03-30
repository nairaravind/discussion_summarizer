# Pydantic model 
from pydantic import BaseModel, Field
from typing import List

class Summarizer(BaseModel):
    summary: str = Field(description="Based on the discussion on the page, what is the summary of the story.")
    key_themes: List[str] = Field(description="Main topics the community is discussing or debating about in the post")
    notable_insights: List[str] = Field(description="Specific, well-supported claims or perspectives surfaced in the comments")
    community_sentiment: str = Field(description="Overall tone of the discussion, ensure to capture the sentiment")
    controversy_signal: str = Field(description="How heated or divided is the discussion?")
    reasoning_trace: str = Field(description="The model's chain of thought before arriving at conclusions")