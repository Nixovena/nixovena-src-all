DISCORD_EPOCH = 1420070400000

DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_CDN_BASE = "https://cdn.discordapp.com"

USER_FLAGS = {
    1 << 0: "Discord Employee",
    1 << 1: "Partnered Server Owner",
    1 << 2: "HypeSquad Events",
    1 << 3: "Bug Hunter Level 1",
    1 << 6: "HypeSquad Bravery",
    1 << 7: "HypeSquad Brilliance",
    1 << 8: "HypeSquad Balance",
    1 << 9: "Early Supporter",
    1 << 10: "Team User",
    1 << 14: "Bug Hunter Level 2",
    1 << 16: "Verified Bot",
    1 << 17: "Early Verified Bot Developer",
    1 << 18: "Discord Certified Moderator",
    1 << 19: "Bot HTTP Interactions",
    1 << 22: "Active Developer",
}

NITRO_TYPES = {
    0: "None",
    1: "Nitro Classic",
    2: "Nitro",
    3: "Nitro Basic",
}

VERIFICATION_LEVELS = {
    0: "None",
    1: "Low (Verified Email)",
    2: "Medium (Registered > 5min)",
    3: "High (Member > 10min)",
    4: "Very High (Verified Phone)",
}

EXPLICIT_CONTENT_FILTER = {
    0: "Disabled",
    1: "Members Without Roles",
    2: "All Members",
}

MFA_LEVELS = {
    0: "Not Required",
    1: "Required",
}

NSFW_LEVELS = {
    0: "Default",
    1: "Explicit",
    2: "Safe",
    3: "Age Restricted",
}

PREMIUM_TIER = {
    0: "None (Level 0)",
    1: "Tier 1 (Level 1)",
    2: "Tier 2 (Level 2)",
    3: "Tier 3 (Level 3)",
}

CHANNEL_TYPES = {
    0: "Text Channel",
    1: "DM",
    2: "Voice Channel",
    3: "Group DM",
    4: "Category",
    5: "Announcement Channel",
    10: "Announcement Thread",
    11: "Public Thread",
    12: "Private Thread",
    13: "Stage Voice",
    14: "Directory",
    15: "Forum",
    16: "Media Channel",
}

ACTIVITY_TYPES = {
    0: "Playing",
    1: "Streaming",
    2: "Listening",
    3: "Watching",
    4: "Custom Status",
    5: "Competing",
}

STATUS_TYPES = {
    "online": "Online",
    "idle": "Idle",
    "dnd": "Do Not Disturb",
    "offline": "Offline",
    "invisible": "Invisible",
}

GUILD_FEATURES = {
    "ANIMATED_BANNER": "Animated Banner",
    "ANIMATED_ICON": "Animated Icon",
    "APPLICATION_COMMAND_PERMISSIONS_V2": "App Command Permissions v2",
    "AUTO_MODERATION": "Auto Moderation",
    "BANNER": "Banner",
    "COMMUNITY": "Community",
    "CREATOR_MONETIZABLE_PROVISIONAL": "Creator Monetization",
    "CREATOR_STORE_PAGE": "Creator Store",
    "DEVELOPER_SUPPORT_SERVER": "Dev Support Server",
    "DISCOVERABLE": "Discoverable",
    "FEATURABLE": "Featurable",
    "INVITES_DISABLED": "Invites Disabled",
    "INVITE_SPLASH": "Invite Splash",
    "MEMBER_VERIFICATION_GATE_ENABLED": "Member Verification",
    "MORE_STICKERS": "More Stickers",
    "NEWS": "News Channels",
    "PARTNERED": "Partnered",
    "PREVIEW_ENABLED": "Preview Enabled",
    "RAID_ALERTS_DISABLED": "Raid Alerts Disabled",
    "ROLE_ICONS": "Role Icons",
    "ROLE_SUBSCRIPTIONS_AVAILABLE_FOR_PURCHASE": "Role Subscriptions",
    "ROLE_SUBSCRIPTIONS_ENABLED": "Role Subscriptions Enabled",
    "TICKETED_EVENTS_ENABLED": "Ticketed Events",
    "VANITY_URL": "Vanity URL",
    "VERIFIED": "Verified",
    "VIP_REGIONS": "VIP Voice Regions",
    "WELCOME_SCREEN_ENABLED": "Welcome Screen",
}

PERMISSION_FLAGS = {
    1 << 0: "Create Instant Invite",
    1 << 1: "Kick Members",
    1 << 2: "Ban Members",
    1 << 3: "Administrator",
    1 << 4: "Manage Channels",
    1 << 5: "Manage Guild",
    1 << 6: "Add Reactions",
    1 << 7: "View Audit Log",
    1 << 8: "Priority Speaker",
    1 << 9: "Stream",
    1 << 10: "View Channel",
    1 << 11: "Send Messages",
    1 << 12: "Send TTS Messages",
    1 << 13: "Manage Messages",
    1 << 14: "Embed Links",
    1 << 15: "Attach Files",
    1 << 16: "Read Message History",
    1 << 17: "Mention Everyone",
    1 << 18: "Use External Emojis",
    1 << 19: "View Guild Insights",
    1 << 20: "Connect",
    1 << 21: "Speak",
    1 << 22: "Mute Members",
    1 << 23: "Deafen Members",
    1 << 24: "Move Members",
    1 << 25: "Use VAD",
    1 << 26: "Change Nickname",
    1 << 27: "Manage Nicknames",
    1 << 28: "Manage Roles",
    1 << 29: "Manage Webhooks",
    1 << 30: "Manage Expressions",
    1 << 31: "Use Application Commands",
    1 << 32: "Request to Speak",
    1 << 33: "Manage Events",
    1 << 34: "Manage Threads",
    1 << 35: "Create Public Threads",
    1 << 36: "Create Private Threads",
    1 << 37: "Use External Stickers",
    1 << 38: "Send Messages in Threads",
    1 << 39: "Use Embedded Activities",
    1 << 40: "Moderate Members",
    1 << 41: "View Creator Monetization Analytics",
    1 << 42: "Use Soundboard",
    1 << 43: "Create Guild Expressions",
    1 << 44: "Create Events",
    1 << 45: "Use External Sounds",
    1 << 46: "Send Voice Messages",
}

DEFAULT_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

ACCOUNT_AGE_THRESHOLDS = {
    "ancient": 2555,
    "old": 1825,
    "mature": 1095,
    "established": 365,
    "recent": 90,
    "new": 30,
    "fresh": 7,
}

WEBHOOK_TYPES = {
    1: "Incoming",
    2: "Channel Follower",
    3: "Application",
}
