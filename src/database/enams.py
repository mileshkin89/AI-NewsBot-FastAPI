from enum import Enum


class SourceType(str, Enum):
    SITE = "site"
    TG = "tg"


class NewsItemStatus(str, Enum):
    NEW = "new"
    DEDUPLICATED = "deduplicated"
    PROCESSED = "processed"
    FAILED = "failed"


class PostStatus(str, Enum):
    NEW = "new"
    GENERATED = "generated"
    FAILED = "failed"

