"""Interactive script to create a Telethon session file for the Telegram parser."""
import asyncio
import shutil
from pathlib import Path

from telethon import TelegramClient
from settings import settings


async def main():
    """Create Telethon session via interactive login and move it to TG_SESSION_DIR."""
    session_dir = Path(settings.TG_SESSION_DIR)
    session_file = f"{settings.TG_SESSION_NAME}.session"

    # 1. Ensure the session directory exists
    session_dir.mkdir(parents=True, exist_ok=True)

    # 2. Create Telegram client (session will be created in current directory)
    client = TelegramClient(
        settings.TG_SESSION_NAME,
        settings.TG_API_ID,
        settings.TG_API_HASH,
    )

    # 3. Perform authorization
    await client.start()
    print("Session created successfully")
    await client.disconnect()

    # 4. Move session file to TG_SESSION_DIR
    src = Path(session_file)
    dst = session_dir / session_file

    if src.exists() and not dst.exists():
        shutil.move(src, dst)
        print(f"Session file moved to: {dst}\n"
              f"Now you can use the telegram parser")
    else:
        print("Session file already exists in sessions directory")


asyncio.run(main())
