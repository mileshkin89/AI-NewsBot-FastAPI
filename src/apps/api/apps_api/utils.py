"""Shared utilities for API layer."""


def paginate(total: int, skip: int, limit: int, items_count: int) -> dict:
    """
    Build pagination metadata dict for list responses.

    Args:
        total: Total number of items matching the query.
        skip: Number of items skipped (offset).
        limit: Maximum number of items per page.
        items_count: Number of items in current response.

    Returns:
        Dict with total, skip, limit, and has_more keys.
    """
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + items_count) < total,
    }
