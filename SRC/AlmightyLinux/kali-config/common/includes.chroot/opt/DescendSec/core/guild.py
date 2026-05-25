from utils.constants import (
    VERIFICATION_LEVELS, EXPLICIT_CONTENT_FILTER, NSFW_LEVELS,
    PREMIUM_TIER, GUILD_FEATURES, CHANNEL_TYPES, ACTIVITY_TYPES,
    STATUS_TYPES, DISCORD_CDN_BASE,
)
from core.snowflake import decode_snowflake


def fetch_guild_widget(api_client, guild_id):
    response = api_client.get(f"/guilds/{guild_id}/widget.json")

    if response is None:
        return {"error": "Connection failed", "guild_id": str(guild_id)}

    if response.status_code == 403:
        return {"error": "Widget disabled for this guild", "guild_id": str(guild_id)}

    if response.status_code == 404:
        return {"error": "Guild not found", "guild_id": str(guild_id)}

    if response.status_code != 200:
        return {"error": f"API returned status {response.status_code}", "guild_id": str(guild_id)}

    return parse_widget_data(response.json(), guild_id)


def parse_widget_data(data, guild_id):
    snowflake_data = decode_snowflake(guild_id)

    channels = []
    for ch in data.get("channels", []):
        channels.append({
            "id": ch.get("id"),
            "name": ch.get("name"),
            "position": ch.get("position"),
        })

    members = []
    for member in data.get("members", []):
        member_info = {
            "id": member.get("id"),
            "username": member.get("username"),
            "discriminator": member.get("discriminator"),
            "avatar_url": member.get("avatar_url"),
            "status": member.get("status"),
            "status_name": STATUS_TYPES.get(member.get("status"), "Unknown"),
        }

        if member.get("game"):
            member_info["activity"] = {
                "name": member["game"].get("name"),
            }

        if member.get("channel_id"):
            member_info["voice_channel_id"] = member.get("channel_id")

        if member.get("deaf"):
            member_info["deaf"] = True
        if member.get("mute"):
            member_info["mute"] = True
        if member.get("self_deaf"):
            member_info["self_deaf"] = True
        if member.get("self_mute"):
            member_info["self_mute"] = True
        if member.get("suppress"):
            member_info["suppressed"] = True

        members.append(member_info)

    voice_members = [m for m in members if m.get("voice_channel_id")]

    online_count = len(members)
    voice_count = len(voice_members)
    status_dist = {}
    for m in members:
        status = m.get("status", "unknown")
        status_dist[status] = status_dist.get(status, 0) + 1

    return {
        "guild_id": str(guild_id),
        "name": data.get("name"),
        "instant_invite": data.get("instant_invite"),
        "presence_count": data.get("presence_count", online_count),
        "created_at": snowflake_data["created_at_utc"],
        "created_at_iso": snowflake_data["created_at_iso"],
        "guild_age": snowflake_data["age"],
        "guild_age_days": snowflake_data["age_days"],
        "channels": channels,
        "channel_count": len(channels),
        "members_online": members,
        "online_count": online_count,
        "voice_members": voice_members,
        "voice_count": voice_count,
        "status_distribution": status_dist,
    }


def fetch_guild_preview(api_client, guild_id):
    response = api_client.get(f"/guilds/{guild_id}/preview")

    if response is None:
        return None

    if response.status_code != 200:
        return None

    return parse_guild_preview(response.json())


def parse_guild_preview(data):
    guild_id = data.get("id", "")
    snowflake_data = decode_snowflake(guild_id)

    features = data.get("features", [])
    feature_names = [GUILD_FEATURES.get(f, f) for f in features]

    icon_hash = data.get("icon")
    splash_hash = data.get("splash")
    discovery_splash = data.get("discovery_splash")
    banner_hash = data.get("banner")

    icon_url = None
    if icon_hash:
        ext = "gif" if icon_hash.startswith("a_") else "png"
        icon_url = f"{DISCORD_CDN_BASE}/icons/{guild_id}/{icon_hash}.{ext}?size=4096"

    splash_url = None
    if splash_hash:
        splash_url = f"{DISCORD_CDN_BASE}/splashes/{guild_id}/{splash_hash}.png?size=4096"

    banner_url = None
    if banner_hash:
        ext = "gif" if banner_hash.startswith("a_") else "png"
        banner_url = f"{DISCORD_CDN_BASE}/banners/{guild_id}/{banner_hash}.{ext}?size=4096"

    emojis = []
    for emoji in data.get("emojis", []):
        emojis.append({
            "id": emoji.get("id"),
            "name": emoji.get("name"),
            "animated": emoji.get("animated", False),
            "available": emoji.get("available", True),
        })

    stickers = []
    for sticker in data.get("stickers", []):
        stickers.append({
            "id": sticker.get("id"),
            "name": sticker.get("name"),
            "format_type": sticker.get("format_type"),
        })

    return {
        "guild_id": guild_id,
        "name": data.get("name"),
        "description": data.get("description"),
        "icon_hash": icon_hash,
        "icon_url": icon_url,
        "icon_animated": icon_hash and icon_hash.startswith("a_") if icon_hash else False,
        "splash_hash": splash_hash,
        "splash_url": splash_url,
        "discovery_splash": discovery_splash,
        "banner_hash": banner_hash,
        "banner_url": banner_url,
        "features": features,
        "feature_names": feature_names,
        "approximate_member_count": data.get("approximate_member_count"),
        "approximate_presence_count": data.get("approximate_presence_count"),
        "emojis": emojis,
        "emoji_count": len(emojis),
        "stickers": stickers,
        "sticker_count": len(stickers),
        "created_at": snowflake_data["created_at_utc"],
        "guild_age": snowflake_data["age"],
        "guild_age_days": snowflake_data["age_days"],
    }


def build_guild_icon_url(guild_id, icon_hash):
    if not icon_hash:
        return None
    ext = "gif" if icon_hash.startswith("a_") else "png"
    return f"{DISCORD_CDN_BASE}/icons/{guild_id}/{icon_hash}.{ext}?size=4096"
