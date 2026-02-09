from datetime import datetime

from sqlalchemy import DateTime, String, Boolean, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Enum as SAEnum

from database.enams import SourceType, PostStatus, NewsItemStatus


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(250))
    type: Mapped[SourceType] = mapped_column(SAEnum(SourceType, native_enum=False), nullable=False)
    url: Mapped[str] = mapped_column(String(500), unique=True)
    title_selector: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    news_items: Mapped[list["NewsItem"]] = relationship(
        "NewsItem",
        back_populates="source",
        cascade="all, delete-orphan"
    )


class NewsItem(Base):
    __tablename__ = 'news_items'

    __table_args__ = (
        UniqueConstraint("title", "source_id", name="uq_news_title_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(250))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    raw_text: Mapped[str] = mapped_column(String(2000))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[NewsItemStatus] = mapped_column(
        SAEnum(NewsItemStatus, native_enum=False),
        default=NewsItemStatus.NEW,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))

    source: Mapped["Source"] = relationship("Source", back_populates="news_items")

    posts: Mapped["Post"] = relationship(
        "Post",
        back_populates="news",
        uselist=False,
        cascade="all, delete-orphan"
    )


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    generated_text: Mapped[str | None] = mapped_column(String(2000), default=None)

    status: Mapped[PostStatus] = mapped_column(
        SAEnum(PostStatus, native_enum=False),
        default=PostStatus.NEW,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    news_id: Mapped[int] = mapped_column(ForeignKey("news_items.id"), index=True, unique=True)

    news: Mapped["NewsItem"] = relationship("NewsItem", back_populates="posts")
