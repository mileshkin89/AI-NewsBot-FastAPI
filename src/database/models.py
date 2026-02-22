"""SQLAlchemy models for sources, categories, news items, posts, users, and admins."""
from datetime import datetime

from sqlalchemy import DateTime, String, Boolean, BigInteger, ForeignKey, func, UniqueConstraint, Table, Column, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Enum as SAEnum

from database.enams import SourceType, PostStatus, NewsItemStatus, UsersPostStatus


class Base(DeclarativeBase):
    pass


source_category = Table(
    "source_category",
    Base.metadata,
    Column(
        "source_id",
        ForeignKey("sources.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

user_category = Table(
    "user_category",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    sources: Mapped[list["Source"]] = relationship(
        secondary=source_category,
        back_populates="categories",
        lazy="selectin",
    )

    users: Mapped[list["User"]] = relationship(
        secondary=user_category,
        back_populates="categories",
        lazy="selectin",
    )


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

    categories: Mapped[list["Category"]] = relationship(
        secondary=source_category,
        back_populates="sources",
        lazy="selectin",
    )


class NewsItem(Base):
    __tablename__ = 'news_items'

    __table_args__ = (
        UniqueConstraint("title", "source_id", name="uq_news_title_source"),
        Index("ix_news_items_simhash", "simhash"),
        Index("ix_news_items_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(250))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    raw_text: Mapped[str] = mapped_column(String(4100))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    simhash: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duplicate_of_id: Mapped[int | None] = mapped_column(
        ForeignKey("news_items.id"),
        nullable=True,
    )
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
    duplicate_of: Mapped["NewsItem | None"] = relationship(
        "NewsItem",
        remote_side="NewsItem.id",
        foreign_keys=[duplicate_of_id],
    )

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

    users_posts: Mapped[list["UsersPost"]] = relationship(
        "UsersPost",
        back_populates="post",
        cascade="all, delete-orphan",
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    chat_id: Mapped[int] = mapped_column(unique=True)
    name: Mapped[str | None] = mapped_column(String(250), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    users_posts: Mapped[list["UsersPost"]] = relationship(
        "UsersPost",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    categories: Mapped[list["Category"]] = relationship(
        secondary=user_category,
        back_populates="users",
        lazy="selectin",
    )


class UsersPost(Base):
    __tablename__ = "user_post"

    __table_args__ = (
        UniqueConstraint("user_id", "post_id", name="uq_user_post"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[UsersPostStatus] = mapped_column(
        SAEnum(UsersPostStatus, native_enum=False),
        default=UsersPostStatus.NEW,
        nullable=False,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE")
    )

    user: Mapped["User"] = relationship(
        back_populates="users_posts"
    )
    post: Mapped["Post"] = relationship(
        back_populates="users_posts"
    )


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(150), default=None)

    hashed_password: Mapped[str] = mapped_column(String(255))
    refresh_token: Mapped[str | None] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True)
    is_super_admin: Mapped[bool] = mapped_column(default=False)

    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )
