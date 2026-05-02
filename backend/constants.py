# Tracker/Stats
TRACKED_EVENTS = {
    "UpdateState",
    "MatchCreated",
    "MatchInitialized",
    "MatchDestroyed",
    "MatchEnded",
}
MAX_CONNECT_TRIES = 5

STATS_API_WARNING = """Before launching Rocket League, edit:

<Install Dir>\\TAGame\\Config\\DefaultStatsAPI.ini

Use at least:

PacketSendRate=30 (any value > 0 enables the exporter)
Port=49123
Restart the game after changing the file."""
TARGET_PORT = 49123


# Discord RPC
DEFAULT_DISCORD_CLIENT_ID = "1301217342012788826"

# Presence config and presets storage
PRESENCE_CONFIG_FILE = "presence-config.json"
PRESETS_FILE = "presence-presets.json"
PRESETS_VERSION = 1
MAX_PRESET_NAME_LEN = 64

# Promo
APP_PROMO_BUTTONS = [
    {
        "label": "Get RocketLeagueRPC",
        "url": "https://manucabral.github.io/RocketLeagueRPC/",
    }
]
