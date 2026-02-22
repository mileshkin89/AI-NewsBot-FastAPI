"""Enums for source type, news item status, post status, and user-post status."""
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
    PROCESSED = "processed"
    FAILED = "failed"


class UsersPostStatus(str, Enum):
    NEW = "new"
    PUBLISHED = "published"
    FAILED = "failed"