# Spotify MCP Server

An MCP (Model Context Protocol) server that connects Claude to Spotify. It exposes 21 tools that let Claude control playback, manage playlists, fetch lyrics, and recommend music - all through natural language.

**Blog post:** https://samit.bearblog.dev/mcp-servers/
**Video demo:** https://youtu.be/BExl8jhthoE

## How it works

MCP is a protocol that lets AI assistants call external tools. This server registers Spotify actions as MCP tools, so when you ask Claude Desktop something like "play some chill music," it can directly call the Spotify API on your behalf.

```
You (natural language) -> Claude Desktop -> MCP Server -> Spotify API
```

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (package manager)
- A [Spotify Developer](https://developer.spotify.com/dashboard) account with a registered app
- A [Genius API](https://genius.com/api-clients) key (for lyrics)
- [Claude Desktop](https://claude.ai/download)

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/yourusername/spotify-mcp.git
cd spotify-mcp
uv sync
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
- `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` from your Spotify Developer Dashboard
- `SPOTIFY_REDIRECT_URI` - your redirect URI (use ngrok since Spotify doesn't support localhost)
- `GENIUS_API_KEY` from the Genius API

### 3. Set up the redirect URI

Spotify doesn't support `localhost` as a redirect URI. Use ngrok to tunnel:

```bash
ngrok http 3000
```

Copy the ngrok URL and add it as a redirect URI in your Spotify Developer Dashboard app settings. Set it as `SPOTIFY_REDIRECT_URI` in your `.env`.

### 4. Configure Claude Desktop

Open Claude Desktop settings and edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "spotify": {
      "command": "<path-to-uv>",
      "args": [
        "--directory",
        "<path-to-spotify-mcp>",
        "run",
        "server.py"
      ],
      "env": {
        "SPOTIFY_CLIENT_ID": "your_client_id",
        "SPOTIFY_CLIENT_SECRET": "your_client_secret",
        "SPOTIFY_REDIRECT_URI": "your_redirect_uri",
        "GENIUS_API_KEY": "your_genius_api_key"
      }
    }
  }
}
```

Replace `<path-to-uv>` with the output of `which uv` and `<path-to-spotify-mcp>` with the project directory.

### 5. Start the server

```bash
uv run server.py
```

Restart Claude Desktop. You should see the Spotify MCP tools available.

## Features

**Playback Controls**
- Play, pause, skip tracks
- Shuffle and repeat modes
- Play a full album by name
- Queue songs by name

**Playlist Management**
- Create playlists by genre, mood, or custom song list
- Add songs to existing playlists by name
- Delete playlists by name
- List all playlists with links
- Fetch playlist contents

**Lyrics and Info**
- Get lyrics for any song (via Genius API)
- Get lyrics for the currently playing song
- Show current track metadata

**Discovery**
- Recommend songs based on listening history
- List recently played artists
- Find albums by artist
- List liked songs

## Development

```bash
# Run tests
uv run pytest

# Lint
uv run ruff check .

# Format
uv run ruff format .
```

## License

MIT
