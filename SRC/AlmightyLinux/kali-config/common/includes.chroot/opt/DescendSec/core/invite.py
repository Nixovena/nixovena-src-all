import re
from utils.constants import (
    VERIFICATION_LEVELS, NSFW_LEVELS, GUILD_FEATURES,
    DISCORD_CDN_BASE,
)
from core.snowflake import decode_snowflake


INVITE_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(?:discord\.gg|discord(?:app)?\.com/invite)/([a-zA-Z0-9\-]+)"
)


def extract_invite_code(input_str):
    match = INVITE_PATTERN.search(input_str)
    if match:
        return match.group(1)
    return input_str.strip()


def fetch_invite(api_client, invite_input, with_counts=True, with_expiration=True):
    code = extract_invite_code(invite_input)

    params = {}
    if with_counts:
        params["with_counts"] = "true"
    if with_expiration:
        params["with_expiration"] = "true"

    response = api_client.get(f"/invites/{code}", params=params)

    if response is None:
        return {"error": "Connection failed", "invite_code": code}

    if response.status_code == 404:
        return {"error": "Invite not found or expired", "invite_code": code}

    if response.status_code != 200:
        return {"error": f"API returned status {response.status_code}", "invite_code": code}

    return parse_invite_data(response.json())


def parse_invite_data(data):
    code = data.get("code", "")
    invite_type = data.get("type", 0)
    expires_at = data.get("expires_at")

    guild_data = data.get("guild", {})
    guild_id = guild_data.get("id", "")
    guild_snowflake = decode_snowflake(guild_id) if guild_id else {}

    guild_icon = guild_data.get("icon")
    guild_icon_url = None
    if guild_icon and guild_id:
        ext = "gif" if guild_icon.startswith("a_") else "png"
        guild_icon_url = f"{DISCORD_CDN_BASE}/icons/{guild_id}/{guild_icon}.{ext}?size=4096"

    guild_splash = guild_data.get("splash")
    guild_splash_url = None
    if guild_splash and guild_id:
        guild_splash_url = f"{DISCORD_CDN_BASE}/splashes/{guild_id}/{guild_splash}.png?size=4096"

    guild_banner = guild_data.get("banner")
    guild_banner_url = None
    if guild_banner and guild_id:
        ext = "gif" if guild_banner.startswith("a_") else "png"
        guild_banner_url = f"{DISCORD_CDN_BASE}/banners/{guild_id}/{guild_banner}.{ext}?size=4096"

    features = guild_data.get("features", [])
    feature_names = [GUILD_FEATURES.get(f, f) for f in features]

    verification = guild_data.get("verification_level", 0)
    nsfw_level = guild_data.get("nsfw_level", 0)
    vanity_url = guild_data.get("vanity_url_code")

    channel_data = data.get("channel", {})
    channel_id = channel_data.get("id", "")
    channel_name = channel_data.get("name", "")
    channel_type = channel_data.get("type", 0)

    inviter_data = data.get("inviter")
    inviter_info = None
    if inviter_data:
        inviter_id = inviter_data.get("id", "")
        inviter_snowflake = decode_snowflake(inviter_id) if inviter_id else {}
        inviter_avatar = inviter_data.get("avatar")
        inviter_avatar_url = None
        if inviter_avatar and inviter_id:
            ext = "gif" if inviter_avatar.startswith("a_") else "png"
            inviter_avatar_url = f"{DISCORD_CDN_BASE}/avatars/{inviter_id}/{inviter_avatar}.{ext}?size=4096"

        inviter_info = {
            "id": inviter_id,
            "username": inviter_data.get("username"),
            "global_name": inviter_data.get("global_name"),
            "discriminator": inviter_data.get("discriminator"),
            "avatar_hash": inviter_avatar,
            "avatar_url": inviter_avatar_url,
            "avatar_animated": inviter_avatar and inviter_avatar.startswith("a_"),
            "bot": inviter_data.get("bot", False),
            "public_flags": inviter_data.get("public_flags", 0),
            "created_at": inviter_snowflake.get("created_at_utc"),
            "account_age": inviter_snowflake.get("age"),
        }

    result = {
        "invite_code": code,
        "invite_url": f"https://discord.gg/{code}",
        "invite_type": invite_type,
        "expires_at": expires_at,
        "guild": {
            "id": guild_id,
            "name": guild_data.get("name"),
            "description": guild_data.get("description"),
            "icon_hash": guild_icon,
            "icon_url": guild_icon_url,
            "splash_hash": guild_splash,
            "splash_url": guild_splash_url,
            "banner_hash": guild_banner,
            "banner_url": guild_banner_url,
            "features": features,
            "feature_names": feature_names,
            "verification_level": verification,
            "verification_name": VERIFICATION_LEVELS.get(verification, "Unknown"),
            "nsfw_level": nsfw_level,
            "nsfw_name": NSFW_LEVELS.get(nsfw_level, "Unknown"),
            "vanity_url_code": vanity_url,
            "premium_subscription_count": guild_data.get("premium_subscription_count"),
            "created_at": guild_snowflake.get("created_at_utc"),
            "guild_age": guild_snowflake.get("age"),
        },
        "channel": {
            "id": channel_id,
            "name": channel_name,
            "type": channel_type,
        },
        "inviter": inviter_info,
        "approximate_member_count": data.get("approximate_member_count"),
        "approximate_presence_count": data.get("approximate_presence_count"),
    }

    member_count = data.get("approximate_member_count", 0)
    presence_count = data.get("approximate_presence_count", 0)
    if member_count and presence_count:
        result["online_ratio"] = round(presence_count / member_count * 100, 2) if member_count > 0 else 0

    return result
