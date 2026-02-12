import asyncio
import csv
import logging
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database.db import get_db
from database.enams import SourceType
from database.models import Category, Source
from settings import settings

logger = logging.getLogger(__name__)


def load_categories_from_csv(csv_path: Path | None = None) -> list[Category]:
    """
    Load categories from a CSV file.

    Expects columns: name; optional: enabled.
    Skips invalid rows and logs warnings.

    Args:
        csv_path: Path to the CSV file. If None, uses settings.CATEGORIES_CSV_PATH
                  (default: data/categories.csv in project root, or Docker volume).

    Returns:
        List of Category model instances. Empty list if file is missing or invalid.
    """
    path = csv_path or settings.CATEGORIES_CSV_PATH
    if not path.exists():
        logger.warning(
            "Categories file not found: %s. Add data/categories.csv or mount a volume.",
            path,
        )
        return []

    categories: list[Category] = []
    seen_names: set[str] = set()  # skip duplicate names within CSV (first wins)
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and "name" not in (reader.fieldnames or []):
            logger.warning(
                "Categories CSV must have column: name [, enabled]",
            )
            return []
        for row in reader:
            try:
                name = (row.get("name") or "").strip()
                if not name:
                    logger.warning("Skipping row: empty category name")
                    continue
                if name in seen_names:
                    logger.warning(
                        "Skipping duplicate category name in CSV: %r, keeping first occurrence",
                        name,
                    )
                    continue
                seen_names.add(name)
                enabled_str = (row.get("enabled") or "true").strip().lower()
                enabled = enabled_str in ("true", "1", "yes", "да")
                categories.append(Category(name=name, enabled=enabled))
            except Exception as e:
                logger.warning("Skipping categories CSV row: %s — %s", row, e)
                continue
    return categories


def load_sources_from_csv(
    csv_path: Path | None = None,
) -> list[tuple[Source, list[str]]]:
    """
    Load news sources from a CSV file.

    Expects columns: type, name, url; optional: title_selector, enabled, categories.
    Type must be 'tg' (Telegram) or 'site'. Categories: comma-separated category
    names (e.g. cinema,sports). Skips invalid rows and logs warnings.

    Args:
        csv_path: Path to the CSV file. If None, uses settings.SOURCES_CSV_PATH
                  (default: data/sources.csv in project root, or Docker volume).

    Returns:
        List of (Source, category_names). category_names are resolved when seeding.
    """
    path = csv_path or settings.SOURCES_CSV_PATH
    if not path.exists():
        logger.warning(
            "Sources file not found: %s. Add data/sources.csv or mount a volume.",
            path,
        )
        return []

    result: list[tuple[Source, list[str]]] = []
    seen_urls: set[str] = set()  # skip duplicate URLs within CSV (first wins)
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and "type" not in (reader.fieldnames or []):
            logger.warning(
                "CSV must have columns: type, name, url [, title_selector] [, enabled] [, categories]",
            )
            return []
        for row in reader:
            try:
                type_val = (row.get("type") or "").strip().lower()
                if type_val not in ("tg", "site"):
                    logger.warning(
                        "Skipping row: invalid type '%s' (expected tg or site)",
                        type_val,
                    )
                    continue
                name = (row.get("name") or "").strip()
                url = (row.get("url") or "").strip()
                if not name or not url:
                    logger.warning("Skipping row: empty name or url")
                    continue
                if url in seen_urls:
                    logger.warning(
                        "Skipping duplicate URL in CSV: %r (source %r), keeping first occurrence",
                        url,
                        name,
                    )
                    continue
                seen_urls.add(url)
                title_selector = (row.get("title_selector") or "").strip() or None
                enabled_str = (row.get("enabled") or "true").strip().lower()
                enabled = enabled_str in ("true", "1", "yes", "да")
                raw_categories = (row.get("categories") or "").strip()
                category_names = [
                    s.strip() for s in raw_categories.split(",") if s.strip()
                ]
                source = Source(
                    type=SourceType(type_val),
                    name=name,
                    url=url,
                    title_selector=title_selector,
                    enabled=enabled,
                )
                result.append((source, category_names))
            except Exception as e:
                logger.warning("Skipping CSV row: %s — %s", row, e)
                continue
    return result


async def populate_db() -> None:
    """
    Insert categories and sources from CSV files into the database (idempotent).

    Only inserts categories/sources that are not already in the DB (by name/URL).
    Safe to run repeatedly (e.g. after container restart).
    """
    async with get_db() as db:
        # Categories: insert only those that don't exist yet
        existing_categories_result = await db.execute(select(Category.name))
        existing_category_names = {row[0] for row in existing_categories_result.all()}
        categories = load_categories_from_csv()
        new_categories = [c for c in categories if c.name not in existing_category_names]
        if new_categories:
            db.add_all(new_categories)
            try:
                await db.commit()
                logger.info("Seeded %d new categories (%d already existed)", len(new_categories), len(categories) - len(new_categories))
            except IntegrityError:
                await db.rollback()
                logger.warning("Categories commit failed (e.g. duplicate names)")
        elif categories:
            logger.info("All %d categories already exist, skipping", len(categories))

        # Sources: insert only those whose URL is not in DB yet
        existing_sources_result = await db.execute(select(Source.url))
        existing_urls = {row[0] for row in existing_sources_result.all()}
        sources_with_categories = load_sources_from_csv()
        # Filter to only new sources (by URL)
        new_sources_with_categories = [
            (source, names) for source, names in sources_with_categories if source.url not in existing_urls
        ]
        if new_sources_with_categories:
            categories_result = await db.execute(select(Category))
            name_to_category = {c.name: c for c in categories_result.scalars().all()}
            sources: list[Source] = []
            for source, category_names in new_sources_with_categories:
                for name in category_names:
                    if name not in name_to_category:
                        logger.warning(
                            "Unknown category %r for source %s — skipping",
                            name,
                            source.name,
                        )
                source.categories = [
                    name_to_category[n] for n in category_names if n in name_to_category
                ]
                sources.append(source)
            db.add_all(sources)
            try:
                await db.commit()
                logger.info("Seeded %d new sources (%d already existed)", len(sources), len(sources_with_categories) - len(sources))
            except IntegrityError:
                await db.rollback()
                logger.warning("Sources commit failed (e.g. duplicate URLs)")
        elif sources_with_categories:
            logger.info("All %d sources already exist, skipping", len(sources_with_categories))


asyncio.run(populate_db())