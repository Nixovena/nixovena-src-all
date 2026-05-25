import re
from utils.constants import WEBHOOK_TYPES, DISCORD_CDN_BASE
from core.snowflake import decode_snowflake


WEBHOOK_PATTERN = re.compile(
    r"(?:https?://)?(?:(?:canary|ptb)\.)?discord(?:app)?\.com/api/webhooks/(\d+)/([a-zA-Z0-9_\-]+)"
)


def parse_webhook_url(url):
    match = WEBHOOK_PATTERN.search(url)
    if not match:
        return None

    return {
        "webhook_id": match.group(1),
        "webhook_token": match.group(2),
        "full_url": f"https://discord.com/api/webhooks/{match.group(1)}/{match.group(2)}",
    }


def fetch_webhook(api_client, webhook_url):
    parsed = parse_webhook_url(webhook_url)
    if not parsed:
        return {"error": "Invalid webhook URL format"}

    url = f"https://discord.com/api/v10/webhooks/{parsed['webhook_id']}/{parsed['webhook_token']}"
    response = api_client.get(url)

    if response is None:
        return {"error": "Connection failed", **parsed}

    if response.status_code == 404:
        return {"error": "Webhook not found or deleted", **parsed}

    if response.status_code == 401:
        return {"error": "Unauthorized - invalid webhook token", **parsed}

    if response.status_code != 200:
        return {"error": f"API returned status {response.status_code}", **parsed}

    return parse_webhook_data(response.json(), parsed)


def parse_webhook_data(data, parsed_url):
    webhook_id = data.get("id", "")
    webhook_type = data.get("type", 0)
    guild_id = data.get("guild_id")
    channel_id = data.get("channel_id")
    name = data.get("name")
    avatar_hash = data.get("avatar")

    snowflake_data = decode_snowflake(webhook_id)

    avatar_url = None
    if avatar_hash:
        ext = "gif" if avatar_hash.startswith("a_") else "png"
        avatar_url = f"{DISCORD_CDN_BASE}/avatars/{webhook_id}/{avatar_hash}.{ext}?size=4096"

    guild_snowflake = decode_snowflake(guild_id) if guild_id else {}
    channel_snowflake = decode_snowflake(channel_id) if channel_id else {}

    user_data = data.get("user")
    creator_info = None
    if user_data:
        creator_id = user_data.get("id", "")
        creator_snowflake = decode_snowflake(creator_id) if creator_id else {}
        creator_info = {
            "id": creator_id,
            "username": user_data.get("username"),
            "global_name": user_data.get("global_name"),
            "discriminator": user_data.get("discriminator"),
            "avatar_hash": user_data.get("avatar"),
            "bot": user_data.get("bot", False),
            "created_at": creator_snowflake.get("created_at_utc"),
        }

    source_guild = data.get("source_guild")
    source_channel = data.get("source_channel")

    source_info = None
    if source_guild or source_channel:
        source_info = {}
        if source_guild:
            source_info["guild_id"] = source_guild.get("id")
            source_info["guild_name"] = source_guild.get("name")
            source_info["guild_icon"] = source_guild.get("icon")
        if source_channel:
            source_info["channel_id"] = source_channel.get("id")
            source_info["channel_name"] = source_channel.get("name")

    application_id = data.get("application_id")

    return {
        "webhook_id": webhook_id,
        "webhook_token": parsed_url.get("webhook_token"),
        "webhook_url": parsed_url.get("full_url"),
        "name": name,
        "type": webhook_type,
        "type_name": WEBHOOK_TYPES.get(webhook_type, "Unknown"),
        "avatar_hash": avatar_hash,
        "avatar_url": avatar_url,
        "guild_id": guild_id,
        "guild_created_at": guild_snowflake.get("created_at_utc"),
        "channel_id": channel_id,
        "channel_created_at": channel_snowflake.get("created_at_utc"),
        "creator": creator_info,
        "source": source_info,
        "application_id": application_id,
        "created_at": snowflake_data["created_at_utc"],
        "webhook_age": snowflake_data["age"],
        "token_prefix": parsed_url.get("webhook_token", "")[:12] + "..." if parsed_url.get("webhook_token") else None,
        "raw_data": data,
    }
