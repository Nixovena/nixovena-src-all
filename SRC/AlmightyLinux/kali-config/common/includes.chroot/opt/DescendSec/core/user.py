from datetime import datetime, timezone
from utils.constants import (
    DISCORD_CDN_BASE, USER_FLAGS, NITRO_TYPES,
    ACCOUNT_AGE_THRESHOLDS, DISCORD_API_BASE,
)
from core.snowflake import decode_snowflake


def fetch_user(api_client, user_id):
    response = api_client.get(f"/users/{user_id}")

    if response is None:
        return {"error": "Connection failed", "user_id": str(user_id)}

    if response.status_code == 401:
        return {"error": "Invalid or missing token", "user_id": str(user_id)}

    if response.status_code == 404:
        return {"error": "User not found", "user_id": str(user_id)}

    if response.status_code != 200:
        return {
            "error": f"API returned status {response.status_code}",
            "user_id": str(user_id),
        }

    return parse_user_data(response.json())


def parse_user_data(data):
    user_id = data.get("id", "")
    username = data.get("username", "")
    global_name = data.get("global_name")
    discriminator = data.get("discriminator", "0")
    avatar_hash = data.get("avatar")
    banner_hash = data.get("banner")
    accent_color = data.get("accent_color")
    public_flags = data.get("public_flags", 0)
    bot = data.get("bot", False)
    system = data.get("system", False)
    banner_color = data.get("banner_color")
    avatar_decoration = data.get("avatar_decoration_data")

    snowflake_data = decode_snowflake(user_id)

    badges = parse_flags(public_flags)

    avatar_url = build_avatar_url(user_id, avatar_hash)
    banner_url = build_banner_url(user_id, banner_hash)

    has_animated_avatar = avatar_hash and avatar_hash.startswith("a_")
    has_animated_banner = banner_hash and banner_hash.startswith("a_")

    nitro_indicators = []
    if has_animated_avatar:
        nitro_indicators.append("Animated Avatar (Nitro)")
    if has_animated_banner:
        nitro_indicators.append("Animated Banner (Nitro)")
    if banner_hash:
        nitro_indicators.append("Custom Banner (Nitro)")
    if avatar_decoration:
        nitro_indicators.append("Avatar Decoration (Nitro)")

    legacy_username = discriminator != "0"
    display_name = global_name or username

    age_classification = classify_account_age(snowflake_data["age_days"])

    risk_score = calculate_risk_score(snowflake_data["age_days"], bot, badges, nitro_indicators)

    result = {
        "user_id": user_id,
        "username": username,
        "global_name": global_name,
        "display_name": display_name,
        "discriminator": discriminator,
        "legacy_username_system": legacy_username,
        "full_tag": f"{username}#{discriminator}" if legacy_username else username,
        "bot": bot,
        "system": system,
        "avatar_hash": avatar_hash,
        "avatar_url": avatar_url,
        "avatar_animated": has_animated_avatar,
        "banner_hash": banner_hash,
        "banner_url": banner_url,
        "banner_animated": has_animated_banner,
        "banner_color": banner_color,
        "accent_color": accent_color,
        "accent_color_hex": f"#{accent_color:06x}" if accent_color else None,
        "avatar_decoration": bool(avatar_decoration),
        "public_flags": public_flags,
        "public_flags_binary": format(public_flags, "032b") if public_flags else None,
        "badges": badges,
        "nitro_indicators": nitro_indicators,
        "has_nitro_evidence": len(nitro_indicators) > 0,
        "created_at": snowflake_data["created_at_utc"],
        "created_at_iso": snowflake_data["created_at_iso"],
        "created_at_unix": snowflake_data["created_at_unix"],
        "account_age": snowflake_data["age"],
        "account_age_days": snowflake_data["age_days"],
        "account_age_class": age_classification,
        "snowflake_worker_id": snowflake_data["worker_id"],
        "snowflake_process_id": snowflake_data["process_id"],
        "snowflake_increment": snowflake_data["increment"],
        "risk_score": risk_score,
        "raw_data": data,
    }

    return result


def parse_flags(flags_value):
    flags = []
    if not flags_value:
        return flags

    for bit, name in USER_FLAGS.items():
        if flags_value & bit:
            flags.append(name)

    return flags


def build_avatar_url(user_id, avatar_hash):
    if not avatar_hash:
        default_index = (int(user_id) >> 22) % 6
        return f"{DISCORD_CDN_BASE}/embed/avatars/{default_index}.png"

    ext = "gif" if avatar_hash.startswith("a_") else "png"
    return f"{DISCORD_CDN_BASE}/avatars/{user_id}/{avatar_hash}.{ext}?size=4096"


def build_banner_url(user_id, banner_hash):
    if not banner_hash:
        return None

    ext = "gif" if banner_hash.startswith("a_") else "png"
    return f"{DISCORD_CDN_BASE}/banners/{user_id}/{banner_hash}.{ext}?size=4096"


def classify_account_age(age_days):
    for label, threshold in sorted(ACCOUNT_AGE_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
        if age_days >= threshold:
            return label
    return "brand_new"


def calculate_risk_score(age_days, is_bot, badges, nitro_indicators):
    score = 50

    if age_days < 7:
        score += 30
    elif age_days < 30:
        score += 20
    elif age_days < 90:
        score += 10
    elif age_days < 365:
        score += 0
    elif age_days < 1095:
        score -= 10
    else:
        score -= 20

    if is_bot:
        score -= 10

    if badges:
        score -= len(badges) * 5

    if "Discord Employee" in badges:
        score -= 20
    if "Verified Bot" in badges:
        score -= 15
    if "Early Verified Bot Developer" in badges:
        score -= 10

    if nitro_indicators:
        score -= len(nitro_indicators) * 3

    return max(0, min(100, score))


def fetch_user_profile(api_client, user_id):
    response = api_client.get(f"/users/{user_id}/profile")

    if response is None or response.status_code != 200:
        return None

    data = response.json()

    profile = {
        "bio": data.get("user", {}).get("bio"),
        "pronouns": data.get("user_profile", {}).get("pronouns"),
        "theme_colors": data.get("user_profile", {}).get("theme_colors"),
        "connected_accounts": [],
        "mutual_guilds": [],
        "premium_since": data.get("premium_since"),
        "premium_type": data.get("premium_type"),
        "premium_guild_since": data.get("premium_guild_since"),
    }

    for account in data.get("connected_accounts", []):
        profile["connected_accounts"].append({
            "type": account.get("type"),
            "id": account.get("id"),
            "name": account.get("name"),
            "verified": account.get("verified"),
            "visibility": account.get("visibility"),
        })

    for guild in data.get("mutual_guilds", []):
        profile["mutual_guilds"].append({
            "id": guild.get("id"),
            "nick": guild.get("nick"),
        })

    if profile["premium_type"] is not None:
        profile["premium_type_name"] = NITRO_TYPES.get(profile["premium_type"], "Unknown")

    return profile
