import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.display import (
    print_banner, print_section, print_field, print_success, print_error,
    print_warning, print_info, print_status, create_table, print_dict_panel,
    print_list_panel, print_risk_score, print_separator, print_json_data, console,
)
from utils.api import DiscordAPIClient
from utils.export import ExportManager
from core.snowflake import decode_snowflake, batch_decode, estimate_entity_type
from core.user import fetch_user, fetch_user_profile
from core.guild import fetch_guild_widget, fetch_guild_preview
from core.invite import fetch_invite
from core.webhook import fetch_webhook
from core.token import analyze_token
from core.scanner import BulkScanner
from core.permissions import decode_permissions, lookup_application


def handle_export(data, args, prefix="descendsec"):
    fmt = getattr(args, "format", "table")
    output = getattr(args, "output", None)
    if fmt in ("json", "csv", "txt") or output:
        if fmt == "table":
            fmt = "json"
        exporter = ExportManager(output_path=output, output_format=fmt)
        path = exporter.export(data, prefix=prefix)
        print_success(f"Exported to {path}")


def cmd_user(args):
    print_status("User Reconnaissance")

    with DiscordAPIClient(
        token=args.token, proxy=args.proxy,
        timeout=args.timeout, max_retries=args.retries, delay=args.delay,
    ) as client:
        data = fetch_user(client, args.id)

    if "error" in data:
        print_error(data["error"])
        return

    print_section("Identity")
    print_field("User ID", data["user_id"])
    print_field("Username", data["username"])
    print_field("Display Name", data["display_name"])
    print_field("Full Tag", data["full_tag"])
    print_field("Bot Account", "Yes" if data["bot"] else "No")
    print_field("System Account", "Yes" if data["system"] else "No")
    print_field("Legacy Username", "Yes" if data["legacy_username_system"] else "No")

    print_section("Timestamps")
    print_field("Created At (UTC)", data["created_at"])
    print_field("Account Age", data["account_age"])
    print_field("Age Classification", data["account_age_class"])
    print_field("Unix Timestamp", data["created_at_unix"])

    print_section("Visual Assets")
    print_field("Avatar URL", data["avatar_url"])
    print_field("Animated Avatar", "Yes" if data["avatar_animated"] else "No")
    print_field("Banner URL", data.get("banner_url") or "None")
    print_field("Animated Banner", "Yes" if data.get("banner_animated") else "No")
    print_field("Banner Color", data.get("banner_color") or "None")
    print_field("Accent Color", data.get("accent_color_hex") or "None")
    print_field("Avatar Decoration", "Yes" if data.get("avatar_decoration") else "No")

    if data["badges"]:
        print_section("Badges & Flags")
        print_field("Flags (raw)", data["public_flags"])
        print_field("Flags (binary)", data.get("public_flags_binary"))
        for badge in data["badges"]:
            print_field("  Badge", badge, value_style="bold green")

    if data["nitro_indicators"]:
        print_section("Nitro Evidence")
        for ind in data["nitro_indicators"]:
            print_field("  Indicator", ind, value_style="bold magenta")

    print_section("Snowflake Internals")
    print_field("Worker ID", data["snowflake_worker_id"])
    print_field("Process ID", data["snowflake_process_id"])
    print_field("Increment", data["snowflake_increment"])

    print_risk_score(data["risk_score"])

    if args.download_avatar and data.get("avatar_url"):
        dest = os.path.join(args.avatar_dir or ".", f"{data['user_id']}_avatar.png")
        with DiscordAPIClient(proxy=args.proxy) as dl:
            if dl.download(data["avatar_url"], dest):
                print_success(f"Avatar saved to {dest}")

    if args.download_banner and data.get("banner_url"):
        dest = os.path.join(args.avatar_dir or ".", f"{data['user_id']}_banner.png")
        with DiscordAPIClient(proxy=args.proxy) as dl:
            if dl.download(data["banner_url"], dest):
                print_success(f"Banner saved to {dest}")

    export_data = {k: v for k, v in data.items() if k != "raw_data"}
    handle_export(export_data, args, prefix=f"user_{data['user_id']}")

    if getattr(args, "format", "table") == "table" and getattr(args, "raw", False):
        print_json_data(data["raw_data"], "Raw API Response")


def cmd_snowflake(args):
    print_status("Snowflake Decoder")

    ids = []
    if args.id:
        ids.append(args.id)
    if args.batch:
        ids.extend([x.strip() for x in args.batch.split(",") if x.strip()])

    if not ids:
        print_error("No snowflake IDs provided")
        return

    results = batch_decode(ids)

    for res in results:
        if "error" in res:
            print_error(f"ID {res['snowflake_id']}: {res['error']}")
            continue

        print_section(f"Snowflake: {res['snowflake_id']}")
        print_field("Created At (UTC)", res["created_at_utc"])
        print_field("ISO 8601", res["created_at_iso"])
        print_field("Unix Timestamp", res["created_at_unix"])
        print_field("Age", res["age"])
        print_field("Worker ID", res["worker_id"])
        print_field("Process ID", res["process_id"])
        print_field("Increment", res["increment"])
        print_field("Binary", res["binary"])
        print_field("Hex", res["hex"])

        hints = estimate_entity_type(res["snowflake_id"])
        if hints:
            for hint in hints:
                print_field("  Hint", hint, value_style="yellow")

    handle_export(results, args, prefix="snowflake")


def cmd_invite(args):
    print_status("Invite Resolver")

    with DiscordAPIClient(
        proxy=args.proxy, timeout=args.timeout, max_retries=args.retries,
    ) as client:
        data = fetch_invite(client, args.code, args.with_counts, args.with_expiration)

    if "error" in data:
        print_error(data["error"])
        return

    print_section("Invite Details")
    print_field("Invite Code", data["invite_code"])
    print_field("Invite URL", data["invite_url"])
    print_field("Expires At", data.get("expires_at") or "Never")

    guild = data.get("guild", {})
    print_section("Guild Information")
    print_field("Guild ID", guild.get("id"))
    print_field("Guild Name", guild.get("name"))
    print_field("Description", guild.get("description") or "None")
    print_field("Verification", guild.get("verification_name"))
    print_field("NSFW Level", guild.get("nsfw_name"))
    print_field("Vanity URL", guild.get("vanity_url_code") or "None")
    print_field("Boosts", guild.get("premium_subscription_count"))
    print_field("Created At", guild.get("created_at"))
    print_field("Guild Age", guild.get("guild_age"))
    print_field("Icon URL", guild.get("icon_url") or "None")
    print_field("Splash URL", guild.get("splash_url") or "None")
    print_field("Banner URL", guild.get("banner_url") or "None")

    if guild.get("feature_names"):
        print_section("Guild Features")
        for feat in guild["feature_names"]:
            print_field("  Feature", feat, value_style="green")

    print_section("Channel")
    ch = data.get("channel", {})
    print_field("Channel ID", ch.get("id"))
    print_field("Channel Name", ch.get("name"))

    print_section("Member Counts")
    print_field("Total Members", data.get("approximate_member_count"))
    print_field("Online Members", data.get("approximate_presence_count"))
    print_field("Online Ratio", f"{data.get('online_ratio', 0)}%")

    if data.get("inviter"):
        inv = data["inviter"]
        print_section("Inviter")
        print_field("User ID", inv.get("id"))
        print_field("Username", inv.get("username"))
        print_field("Display Name", inv.get("global_name"))
        print_field("Bot", "Yes" if inv.get("bot") else "No")
        print_field("Created At", inv.get("created_at"))
        print_field("Account Age", inv.get("account_age"))
        print_field("Animated Avatar", "Yes" if inv.get("avatar_animated") else "No")

    handle_export(data, args, prefix=f"invite_{data['invite_code']}")


def cmd_webhook(args):
    print_status("Webhook Analysis")

    with DiscordAPIClient(
        proxy=args.proxy, timeout=args.timeout, max_retries=args.retries,
    ) as client:
        data = fetch_webhook(client, args.url)

    if "error" in data:
        print_error(data["error"])
        return

    print_section("Webhook Identity")
    print_field("Webhook ID", data["webhook_id"])
    print_field("Name", data["name"])
    print_field("Type", data["type_name"])
    print_field("Token Preview", data.get("token_prefix"))
    print_field("Avatar URL", data.get("avatar_url") or "None")
    print_field("Created At", data["created_at"])
    print_field("Webhook Age", data["webhook_age"])

    print_section("Location")
    print_field("Guild ID", data.get("guild_id"))
    print_field("Guild Created", data.get("guild_created_at"))
    print_field("Channel ID", data.get("channel_id"))
    print_field("Channel Created", data.get("channel_created_at"))
    print_field("Application ID", data.get("application_id") or "None")

    if data.get("creator"):
        cr = data["creator"]
        print_section("Creator")
        print_field("User ID", cr.get("id"))
        print_field("Username", cr.get("username"))
        print_field("Display Name", cr.get("global_name"))
        print_field("Bot", "Yes" if cr.get("bot") else "No")
        print_field("Created At", cr.get("created_at"))

    if data.get("source"):
        src = data["source"]
        print_section("Source (Channel Follower)")
        print_field("Source Guild ID", src.get("guild_id"))
        print_field("Source Guild Name", src.get("guild_name"))
        print_field("Source Channel ID", src.get("channel_id"))
        print_field("Source Channel Name", src.get("channel_name"))

    export_data = {k: v for k, v in data.items() if k != "raw_data"}
    handle_export(export_data, args, prefix=f"webhook_{data['webhook_id']}")


def cmd_token(args):
    print_status("Token Structure Analysis")

    data = analyze_token(args.value)

    print_section("Token Format")
    print_field("Token Length", data["raw_token_length"])
    print_field("Preview", data["token_preview"])
    print_field("Valid Format", "Yes" if data["valid_format"] else "No")
    print_field("MFA Token", "Yes" if data["is_mfa_token"] else "No")
    print_field("Bot Token", "Yes" if data["is_bot_token"] else "No")
    print_field("User Token", "Yes" if data["is_user_token"] else "No")

    if data.get("user_id"):
        print_section("Extracted User ID")
        print_field("User ID", data["user_id"])
        if data.get("user_snowflake"):
            sf = data["user_snowflake"]
            print_field("Account Created", sf.get("created_at_utc"))
            print_field("Account Age", sf.get("age"))

    if data.get("timestamp_decoded"):
        ts = data["timestamp_decoded"]
        print_section("Token Timestamp")
        print_field("Generated At", ts.get("utc"))
        print_field("Unix", ts.get("unix"))

    if data.get("hmac_fragment"):
        print_section("HMAC Signature")
        print_field("HMAC Preview", data["hmac_fragment"])
        print_field("HMAC Length", data.get("hmac_length"))

    if data.get("segment_lengths"):
        print_section("Segment Analysis")
        for seg, length in data["segment_lengths"].items():
            print_field(f"  {seg}", length)

    if data.get("analysis"):
        print_section("Analysis Notes")
        for note in data["analysis"]:
            print_info(note)

    if data.get("warnings"):
        print_section("Warnings")
        for warn in data["warnings"]:
            print_warning(warn)

    handle_export(data, args, prefix="token_analysis")


def cmd_guild(args):
    print_status("Guild Reconnaissance")

    with DiscordAPIClient(
        token=args.token, proxy=args.proxy,
        timeout=args.timeout, max_retries=args.retries,
    ) as client:
        widget = fetch_guild_widget(client, args.id)

        preview = None
        if args.token:
            preview = fetch_guild_preview(client, args.id)

    if "error" in widget and preview is None:
        print_error(widget["error"])
        sf = decode_snowflake(args.id)
        print_section("Snowflake Only")
        print_field("Guild ID", args.id)
        print_field("Created At", sf["created_at_utc"])
        print_field("Guild Age", sf["age"])
        return

    if "error" not in widget:
        print_section("Widget Data")
        print_field("Guild Name", widget.get("name"))
        print_field("Guild ID", widget.get("guild_id"))
        print_field("Created At", widget.get("created_at"))
        print_field("Guild Age", widget.get("guild_age"))
        print_field("Online Count", widget.get("online_count"))
        print_field("Voice Count", widget.get("voice_count"))
        print_field("Instant Invite", widget.get("instant_invite") or "None")

        if widget.get("channels"):
            print_section("Visible Channels")
            rows = [(ch["id"], ch["name"], ch.get("position", "N/A"))
                    for ch in widget["channels"]]
            create_table("Channels", [
                ("ID", "cyan", "left"),
                ("Name", "white", "left"),
                ("Position", "dim", "right"),
            ], rows)

        if widget.get("members_online"):
            print_section(f"Online Members ({widget['online_count']})")
            rows = []
            for m in widget["members_online"][:25]:
                activity = m.get("activity", {}).get("name", "")
                rows.append((m.get("username", ""), m.get("status_name", ""), activity))
            create_table("Members", [
                ("Username", "white", "left"),
                ("Status", "green", "left"),
                ("Activity", "dim", "left"),
            ], rows)

        if widget.get("status_distribution"):
            print_section("Status Distribution")
            for status, count in widget["status_distribution"].items():
                print_field(f"  {status}", count)

    if preview:
        print_section("Guild Preview")
        print_field("Name", preview.get("name"))
        print_field("Description", preview.get("description") or "None")
        print_field("Members", preview.get("approximate_member_count"))
        print_field("Online", preview.get("approximate_presence_count"))
        print_field("Emojis", preview.get("emoji_count"))
        print_field("Stickers", preview.get("sticker_count"))
        print_field("Icon URL", preview.get("icon_url") or "None")
        print_field("Splash URL", preview.get("splash_url") or "None")
        print_field("Banner URL", preview.get("banner_url") or "None")

        if preview.get("feature_names"):
            print_section("Features")
            for feat in preview["feature_names"]:
                print_field("  Feature", feat, value_style="green")

    export_data = {}
    if "error" not in widget:
        export_data["widget"] = widget
    if preview:
        export_data["preview"] = preview
    handle_export(export_data, args, prefix=f"guild_{args.id}")


def cmd_bulkscan(args):
    print_status("Bulk User Scanner")

    scanner = BulkScanner(
        token=args.token, proxy=args.proxy, timeout=args.timeout,
        max_retries=args.retries, delay=args.delay, workers=args.workers,
    )

    ids = []
    if args.file:
        ids = scanner.load_ids_from_file(args.file)
        print_info(f"Loaded {len(ids)} IDs from {args.file}")
    if args.ids:
        ids.extend([x.strip() for x in args.ids.split(",") if x.strip()])

    if not ids:
        print_error("No user IDs provided")
        return

    print_info(f"Scanning {len(ids)} user IDs with {args.workers} worker(s)...")

    def progress(done, total, uid):
        console.print(f"  [dim][{done}/{total}] Scanned {uid}[/dim]", end="\r")

    report = scanner.scan_ids(ids, progress_callback=progress)
    console.print()

    print_section("Scan Results")
    print_field("Total Scanned", report["total_scanned"])
    print_field("Found", report["total_found"])
    print_field("Errors", report["total_errors"])
    print_field("Bots", report["bots"])
    print_field("Humans", report["humans"])
    print_field("Nitro Users", report["nitro_users"])
    print_field("High Risk", report["high_risk_count"])
    print_field("Avg Risk Score", report["average_risk_score"])

    if report.get("badge_distribution"):
        print_section("Badge Distribution")
        for badge, count in sorted(report["badge_distribution"].items(), key=lambda x: x[1], reverse=True):
            print_field(f"  {badge}", count)

    if report.get("age_distribution"):
        print_section("Age Distribution")
        for age_class, count in sorted(report["age_distribution"].items(), key=lambda x: x[1], reverse=True):
            print_field(f"  {age_class}", count)

    if report["results"]:
        rows = []
        for r in report["results"][:50]:
            rows.append((
                r.get("user_id", ""),
                r.get("username", ""),
                "Bot" if r.get("bot") else "User",
                r.get("account_age_class", ""),
                str(r.get("risk_score", 0)),
            ))
        create_table("Users Found", [
            ("ID", "cyan", "left"),
            ("Username", "white", "left"),
            ("Type", "yellow", "center"),
            ("Age Class", "green", "center"),
            ("Risk", "red", "right"),
        ], rows)

    if report["errors"]:
        print_section("Errors")
        for err in report["errors"][:20]:
            print_error(f"{err['user_id']}: {err['error']}")

    handle_export(report, args, prefix="bulkscan")


def cmd_permissions(args):
    print_status("Permission Decoder")

    data = decode_permissions(args.value)

    print_section("Permission Analysis")
    print_field("Integer", data["permission_integer"])
    print_field("Hex", data["permission_hex"])
    print_field("Is Administrator", "Yes" if data["is_administrator"] else "No")
    print_field("Granted Count", data["granted_count"])
    print_field("Risk Level", data["risk_level"])

    if data["dangerous_permissions"]:
        print_section("Dangerous Permissions")
        for perm in data["dangerous_permissions"]:
            print_field("  DANGER", perm, value_style="bold red")

    if data["granted"]:
        print_section("Granted Permissions")
        for perm in data["granted"]:
            print_field("  Granted", perm, value_style="green")

    handle_export(data, args, prefix="permissions")


def cmd_application(args):
    print_status("Application Lookup")

    with DiscordAPIClient(
        proxy=args.proxy, timeout=args.timeout, max_retries=args.retries,
    ) as client:
        data = lookup_application(client, args.id)

    if "error" in data:
        print_error(data["error"])
        return

    print_section("Application Details")
    for key, val in data.items():
        if val is not None:
            print_field(key.replace("_", " ").title(), val)

    handle_export(data, args, prefix=f"app_{args.id}")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="descendsec",
        description="DescendSec - Discord OSINT Intelligence Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--no-banner", action="store_true", help="Suppress banner")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    p_user = subparsers.add_parser("user", help="User OSINT reconnaissance")
    p_user.add_argument("--id", required=True, help="Target user ID")
    p_user.add_argument("--token", required=True, help="Discord bot token")
    p_user.add_argument("--proxy", help="HTTP/SOCKS proxy URL")
    p_user.add_argument("--format", default="table", choices=["table", "json", "csv", "txt"])
    p_user.add_argument("--output", help="Output file path")
    p_user.add_argument("--timeout", type=int, default=30)
    p_user.add_argument("--retries", type=int, default=3)
    p_user.add_argument("--delay", type=float, default=0.0)
    p_user.add_argument("--download-avatar", action="store_true")
    p_user.add_argument("--download-banner", action="store_true")
    p_user.add_argument("--avatar-dir", help="Directory for downloaded assets")
    p_user.add_argument("--raw", action="store_true", help="Show raw API response")

    p_sf = subparsers.add_parser("snowflake", help="Decode Discord snowflake IDs")
    p_sf.add_argument("--id", help="Single snowflake ID")
    p_sf.add_argument("--batch", help="Comma-separated snowflake IDs")
    p_sf.add_argument("--format", default="table", choices=["table", "json", "csv", "txt"])
    p_sf.add_argument("--output", help="Output file path")

    p_inv = subparsers.add_parser("invite", help="Resolve Discord invite links")
    p_inv.add_argument("--code", required=True, help="Invite code or full URL")
    p_inv.add_argument("--with-counts", action="store_true", default=True)
    p_inv.add_argument("--with-expiration", action="store_true", default=True)
    p_inv.add_argument("--proxy", help="HTTP/SOCKS proxy URL")
    p_inv.add_argument("--format", default="table", choices=["table", "json", "csv", "txt"])
    p_inv.add_argument("--output", help="Output file path")
    p_inv.add_argument("--timeout", type=int, default=30)
    p_inv.add_argument("--retries", type=int, default=3)

    p_wh = subparsers.add_parser("webhook", help="Webhook OSINT analysis")
    p_wh.add_argument("--url", required=True, help="Full webhook URL")
    p_wh.add_argument("--proxy", help="HTTP/SOCKS proxy URL")
    p_wh.add_argument("--format", default="table", choices=["table", "json", "csv", "txt"])
    p_wh.add_argument("--output", help="Output file path")
    p_wh.add_argument("--timeout", type=int, default=30)
    p_wh.add_argument("--retries", type=int, default=3)

    p_tk = subparsers.add_parser("token", help="Token structure analysis")
    p_tk.add_argument("--value", required=True, help="Token string to analyze")
    p_tk.add_argument("--format", default="table", choices=["table", "json", "csv", "txt"])
    p_tk.add_argument("--output", help="Output file path")

    p_g = subparsers.add_parser("guild", help="Guild/Server reconnaissance")
    p_g.add_argument("--id", required=True, help="Guild ID")
    p_g.add_argument("--token", help="Discord bot token (optional, for preview)")
    p_g.add_argument("--proxy", help="HTTP/SOCKS proxy URL")
    p_g.add_argument("--format", default="table", choices=["table", "json", "csv", "txt"])
    p_g.add_argument("--output", help="Output file path")
    p_g.add_argument("--timeout", type=int, default=30)
    p_g.add_argument("--retries", type=int, default=3)

    p_bs = subparsers.add_parser("bulkscan", help="Bulk user scanning")
    p_bs.add_argument("--file", help="File with user IDs (one per line)")
    p_bs.add_argument("--ids", help="Comma-separated user IDs")
    p_bs.add_argument("--token", required=True, help="Discord bot token")
    p_bs.add_argument("--proxy", help="HTTP/SOCKS proxy URL")
    p_bs.add_argument("--format", default="table", choices=["table", "json", "csv", "txt"])
    p_bs.add_argument("--output", help="Output file path")
    p_bs.add_argument("--timeout", type=int, default=30)
    p_bs.add_argument("--retries", type=int, default=3)
    p_bs.add_argument("--delay", type=float, default=0.5)
    p_bs.add_argument("--workers", type=int, default=3)

    p_perm = subparsers.add_parser("permissions", help="Decode permission integer")
    p_perm.add_argument("--value", required=True, type=int, help="Permission integer")
    p_perm.add_argument("--format", default="table", choices=["table", "json", "csv", "txt"])
    p_perm.add_argument("--output", help="Output file path")

    p_app = subparsers.add_parser("application", help="Application/Bot lookup")
    p_app.add_argument("--id", required=True, help="Application/Bot ID")
    p_app.add_argument("--proxy", help="HTTP/SOCKS proxy URL")
    p_app.add_argument("--format", default="table", choices=["table", "json", "csv", "txt"])
    p_app.add_argument("--output", help="Output file path")
    p_app.add_argument("--timeout", type=int, default=30)
    p_app.add_argument("--retries", type=int, default=3)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        print_banner()
        parser.print_help()
        return

    if not getattr(args, "quiet", False) and not args.no_banner:
        print_banner()

    commands = {
        "user": cmd_user,
        "snowflake": cmd_snowflake,
        "invite": cmd_invite,
        "webhook": cmd_webhook,
        "token": cmd_token,
        "guild": cmd_guild,
        "bulkscan": cmd_bulkscan,
        "permissions": cmd_permissions,
        "application": cmd_application,
    }

    handler = commands.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            print_warning("Interrupted by user")
            sys.exit(130)
        except Exception as e:
            print_error(f"Fatal: {e}")
            if getattr(args, "verbose", False):
                import traceback
                traceback.print_exc()
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
