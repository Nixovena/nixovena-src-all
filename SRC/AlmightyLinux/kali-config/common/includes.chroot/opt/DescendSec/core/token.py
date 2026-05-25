import base64
import struct
import re
from datetime import datetime, timezone
from utils.constants import DISCORD_EPOCH
from core.snowflake import decode_snowflake


TOKEN_PATTERN = re.compile(
    r"^([a-zA-Z0-9_-]+)\.([a-zA-Z0-9_-]+)\.([a-zA-Z0-9_-]+)$"
)

MFA_TOKEN_PATTERN = re.compile(
    r"^mfa\.[a-zA-Z0-9_-]+$"
)


def _pad_base64(data):
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return data


def analyze_token(token_str):
    token_str = token_str.strip()

    result = {
        "raw_token_length": len(token_str),
        "token_preview": f"{token_str[:8]}{'*' * (len(token_str) - 16)}{token_str[-8:]}" if len(token_str) > 20 else "***",
        "is_mfa_token": False,
        "is_bot_token": False,
        "is_user_token": False,
        "valid_format": False,
        "user_id": None,
        "user_snowflake": None,
        "timestamp_decoded": None,
        "hmac_fragment": None,
        "warnings": [],
        "analysis": [],
    }

    if MFA_TOKEN_PATTERN.match(token_str):
        result["is_mfa_token"] = True
        result["valid_format"] = True
        result["analysis"].append("MFA (Multi-Factor Authentication) token detected")
        result["analysis"].append("This token belongs to an account with 2FA enabled")
        result["analysis"].append("MFA tokens have a different structure than standard tokens")
        return result

    match = TOKEN_PATTERN.match(token_str)
    if not match:
        result["warnings"].append("Token does not match standard Discord token format")
        return result

    result["valid_format"] = True
    part1, part2, part3 = match.group(1), match.group(2), match.group(3)

    try:
        decoded_id = base64.b64decode(_pad_base64(part1)).decode("utf-8")
        if decoded_id.isdigit():
            result["user_id"] = decoded_id
            snowflake_data = decode_snowflake(decoded_id)
            result["user_snowflake"] = snowflake_data
            result["analysis"].append(f"User ID: {decoded_id}")
            result["analysis"].append(f"Account created: {snowflake_data['created_at_utc']}")
            result["analysis"].append(f"Account age: {snowflake_data['age']}")

            if int(decoded_id) < 100000000000000000:
                result["analysis"].append("Very early Discord account (low snowflake)")

        else:
            result["warnings"].append(f"Decoded first segment is not numeric: {decoded_id}")
    except Exception:
        result["warnings"].append("Failed to decode first segment as base64")

    try:
        padded = _pad_base64(part2)
        decoded_bytes = base64.b64decode(padded)

        if len(decoded_bytes) >= 4:
            timestamp_int = struct.unpack(">I", decoded_bytes[:4])[0]
            token_epoch = datetime.fromtimestamp(timestamp_int, tz=timezone.utc)

            if datetime(2015, 1, 1, tzinfo=timezone.utc) <= token_epoch <= datetime.now(timezone.utc):
                result["timestamp_decoded"] = {
                    "unix": timestamp_int,
                    "utc": token_epoch.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "iso": token_epoch.isoformat(),
                }
                result["analysis"].append(f"Token generated at: {token_epoch.strftime('%Y-%m-%d %H:%M:%S UTC')}")

                if result.get("user_snowflake"):
                    account_created = datetime.fromisoformat(result["user_snowflake"]["created_at_iso"])
                    if token_epoch < account_created:
                        result["warnings"].append("Token timestamp predates account creation")

    except Exception:
        result["analysis"].append("Could not decode timestamp segment")

    result["hmac_fragment"] = f"{part3[:6]}...{part3[-6:]}" if len(part3) > 12 else "***"
    result["hmac_length"] = len(part3)

    total_len = len(token_str)
    if total_len > 70:
        result["is_bot_token"] = True
        result["analysis"].append("Token length suggests BOT token")
    elif total_len > 55:
        result["is_user_token"] = True
        result["analysis"].append("Token length suggests USER token")
    else:
        result["analysis"].append("Token length is unusual")

    result["segment_lengths"] = {
        "user_id_segment": len(part1),
        "timestamp_segment": len(part2),
        "hmac_segment": len(part3),
    }

    return result


def validate_token_live(api_client, token_str):
    import httpx

    headers = {
        "Authorization": token_str,
        "Content-Type": "application/json",
    }

    try:
        response = httpx.get(
            "https://discord.com/api/v10/users/@me",
            headers=headers,
            timeout=10,
        )

        if response.status_code == 200:
            data = response.json()
            return {
                "valid": True,
                "user_id": data.get("id"),
                "username": data.get("username"),
                "email": data.get("email"),
                "phone": data.get("phone"),
                "verified": data.get("verified"),
                "mfa_enabled": data.get("mfa_enabled"),
                "locale": data.get("locale"),
                "flags": data.get("flags"),
                "premium_type": data.get("premium_type"),
            }
        elif response.status_code == 401:
            return {"valid": False, "reason": "Invalid token"}
        elif response.status_code == 403:
            return {"valid": False, "reason": "Token is valid but lacks permissions"}
        else:
            return {"valid": False, "reason": f"Unexpected status: {response.status_code}"}

    except Exception as e:
        return {"valid": False, "reason": f"Connection error: {str(e)}"}
