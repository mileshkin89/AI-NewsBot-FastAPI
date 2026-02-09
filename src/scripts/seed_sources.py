import asyncio
import csv
import logging
from pathlib import Path
from sqlalchemy.exc import IntegrityError

from database.db import get_db
from database.enams import SourceType
from database.models import Source
from settings import settings

logger = logging.getLogger(__name__)


def load_sources_from_csv(csv_path: Path | None = None) -> list[Source]:
    """
    Load news sources from a CSV file.

    Expects columns: type, name, url; optional: title_selector, enabled.
    Type must be 'tg' (Telegram) or 'site'. Skips invalid rows and logs warnings.

    Args:
        csv_path: Path to the CSV file. If None, uses settings.SOURCES_CSV_PATH
                  (default: data/sources.csv in project root, or Docker volume).

    Returns:
        List of Source model instances. Empty list if file is missing or invalid.
    """
    path = csv_path or settings.SOURCES_CSV_PATH
    if not path.exists():
        logger.warning(
            "Sources file not found: %s. Add data/sources.csv or mount a volume.",
            path,
        )
        return []

    sources: list[Source] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames and "type" not in (reader.fieldnames or []):
            logger.warning(
                "CSV must have columns: type, name, url [, title_selector] [, enabled]",
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
                title_selector = (row.get("title_selector") or "").strip() or None
                enabled_str = (row.get("enabled") or "true").strip().lower()
                enabled = enabled_str in ("true", "1", "yes", "да")
                sources.append(
                    Source(
                        type=SourceType(type_val),
                        name=name,
                        url=url,
                        title_selector=title_selector,
                        enabled=enabled,
                    )
                )
            except Exception as e:
                logger.warning("Skipping CSV row: %s — %s", row, e)
                continue
    return sources


async def populate_db() -> None:
    """
    Insert sources from CSV into the database.

    Loads sources via load_sources_from_csv(), adds them in a single transaction.
    On IntegrityError (e.g. duplicate URL) rolls back and exits without raising.
    """
    sources = load_sources_from_csv()
    if not sources:
        return

    async with get_db() as db:
        db.add_all(sources)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            return


asyncio.run(populate_db())