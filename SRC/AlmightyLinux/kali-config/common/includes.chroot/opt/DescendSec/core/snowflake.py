from datetime import datetime, timezone
from utils.constants import DISCORD_EPOCH


def decode_snowflake(snowflake_id):
    snowflake_id = int(snowflake_id)

    timestamp_ms = (snowflake_id >> 22) + DISCORD_EPOCH
    worker_id = (snowflake_id & 0x3E0000) >> 17
    process_id = (snowflake_id & 0x1F000) >> 12
    increment = snowflake_id & 0xFFF

    created_at = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    age_delta = datetime.now(timezone.utc) - created_at

    age_days = age_delta.days
    age_hours = age_delta.seconds // 3600
    age_minutes = (age_delta.seconds % 3600) // 60

    if age_days > 365:
        age_years = age_days / 365.25
        age_str = f"{age_years:.1f} years ({age_days} days)"
    elif age_days > 30:
        age_months = age_days / 30.44
        age_str = f"{age_months:.1f} months ({age_days} days)"
    else:
        age_str = f"{age_days} days, {age_hours}h {age_minutes}m"

    return {
        "snowflake_id": str(snowflake_id),
        "timestamp_ms": timestamp_ms,
        "created_at_utc": created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "created_at_iso": created_at.isoformat(),
        "created_at_unix": int(created_at.timestamp()),
        "age": age_str,
        "age_days": age_days,
        "worker_id": worker_id,
        "process_id": process_id,
        "increment": increment,
        "binary": format(snowflake_id, "064b"),
        "hex": format(snowflake_id, "016x"),
    }


def batch_decode(snowflake_ids):
    results = []
    for sid in snowflake_ids:
        try:
            results.append(decode_snowflake(sid))
        except (ValueError, OverflowError):
            results.append({
                "snowflake_id": str(sid),
                "error": "Invalid snowflake ID",
            })
    return results


def snowflake_to_timestamp(snowflake_id):
    snowflake_id = int(snowflake_id)
    timestamp_ms = (snowflake_id >> 22) + DISCORD_EPOCH
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)


def timestamp_to_snowflake(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    timestamp_ms = int(dt.timestamp() * 1000) - DISCORD_EPOCH
    return timestamp_ms << 22


def estimate_entity_type(snowflake_id):
    created = snowflake_to_timestamp(snowflake_id)
    age_days = (datetime.now(timezone.utc) - created).days

    hints = []

    increment = int(snowflake_id) & 0xFFF
    if increment == 0:
        hints.append("Likely first entity created in that millisecond")

    if age_days > 3650:
        hints.append("Pre-2016 era entity (very early Discord)")
    elif age_days > 2555:
        hints.append("2016-2019 era entity (early Discord)")
    elif age_days > 1460:
        hints.append("2019-2021 era entity")
    elif age_days > 730:
        hints.append("2021-2023 era entity")
    else:
        hints.append("Recent entity")

    return hints
