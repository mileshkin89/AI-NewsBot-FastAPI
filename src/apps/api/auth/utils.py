from fastapi import Response


def set_refresh_token_cookie(
        response: Response,
        refresh_token: str
) -> None:
    """Sets a refresh token in the cookie."""
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,
    )


