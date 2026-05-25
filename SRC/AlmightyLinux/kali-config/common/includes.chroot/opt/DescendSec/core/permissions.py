from utils.constants import PERMISSION_FLAGS


def decode_permissions(permission_int):
    permission_int = int(permission_int)
    granted = []
    denied = []

    for bit, name in sorted(PERMISSION_FLAGS.items()):
        if permission_int & bit:
            granted.append(name)
        else:
            denied.append(name)

    is_admin = bool(permission_int & (1 << 3))

    dangerous_perms = [
        "Administrator", "Ban Members", "Kick Members",
        "Manage Guild", "Manage Channels", "Manage Roles",
        "Manage Webhooks", "Manage Messages", "Mention Everyone",
    ]
    dangerous_granted = [p for p in granted if p in dangerous_perms]

    risk = "LOW"
    if is_admin:
        risk = "CRITICAL"
    elif len(dangerous_granted) >= 4:
        risk = "HIGH"
    elif len(dangerous_granted) >= 2:
        risk = "MEDIUM"

    return {
        "permission_integer": permission_int,
        "permission_hex": hex(permission_int),
        "permission_binary": bin(permission_int),
        "granted": granted,
        "granted_count": len(granted),
        "denied": denied,
        "denied_count": len(denied),
        "is_administrator": is_admin,
        "dangerous_permissions": dangerous_granted,
        "risk_level": risk,
    }


def generate_invite_url(client_id, permissions=0, guild_id=None, scopes=None):
    if scopes is None:
        scopes = ["bot", "applications.commands"]

    scope_str = "+".join(scopes)
    url = f"https://discord.com/oauth2/authorize?client_id={client_id}&permissions={permissions}&scope={scope_str}"

    if guild_id:
        url += f"&guild_id={guild_id}"

    return url


def lookup_application(api_client, application_id):
    response = api_client.get(f"/applications/{application_id}/rpc")

    if response is None:
        return {"error": "Connection failed", "application_id": str(application_id)}

    if response.status_code != 200:
        return {"error": f"API returned status {response.status_code}", "application_id": str(application_id)}

    data = response.json()

    return {
        "application_id": data.get("id"),
        "name": data.get("name"),
        "description": data.get("description"),
        "icon": data.get("icon"),
        "bot_public": data.get("bot_public"),
        "bot_require_code_grant": data.get("bot_require_code_grant"),
        "terms_of_service_url": data.get("terms_of_service_url"),
        "privacy_policy_url": data.get("privacy_policy_url"),
        "custom_install_url": data.get("custom_install_url"),
        "verify_key": data.get("verify_key"),
        "flags": data.get("flags"),
        "tags": data.get("tags"),
        "type": data.get("type"),
    }
