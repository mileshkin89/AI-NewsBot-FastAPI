# AI-NewsBot-FastAPI
An application for automating a news channel using AI to process and generate posts.

## Installation

### Create _.env_
Create a `.env` file based on `.env.sample`:
```bash
cp .env.sample .env
```

### Telethon Client Registration

1. Register a Telethon client using a phone number.
It is recommended not to use your personal Telegram number.

Official page:
https://my.telegram.org
 → Development tools

You need to obtain _api_id_ and _api_hash_.

2. Add _api_id_ and _api_hash_ values in _.env_ file

3. On the first application run, execute _telethon_login.py_ and complete the authorization process:
- enter your phone number
- enter the verification code sent via Telegram
After successful authorization, a file named _<TG_SESSION_NAME>.session_ will be created and moved in sessions/ directory.
