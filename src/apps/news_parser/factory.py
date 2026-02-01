from .sites import SiteParser
from .telegram import TelegramParser


def get_parser(source, limit):
    if source.type == "tg" and source.enabled:
        return TelegramParser(
            source_name=source.name,
            channel=source.url,
            limit=limit,
        )

    if source.type == "site" and source.enabled:
        return SiteParser(
            source_name=source.name,
            url=source.url,
            title_selector=source.title_selector,
            limit=limit,
        )

    raise ValueError(f"Unsupported source type: {source.type}")
