from datetime import datetime
from pydantic import BaseModel


class RawNews(BaseModel):
    title: str | None
    text: str | None
    url: str
    source: str
    published_at: datetime | None
    source_message_id: int | None = None 


class NewsItem(BaseModel):
    title: str | None
    url: str
    source: str
    published_at: datetime | None
    raw_text: str | None
    source_message_id: int | None = None 
