Blog-:
https://samit.bearblog.dev/mcp-servers/

Video Demo-:
https://youtu.be/BExl8jhthoE

To start-:

1. Clone repo
2. Download dependencies -> uv, requests, mcp, spotipy via pip
3. Use ngrok for tunnelling localhost -> ngrok http 3000 {spotify doesn't support localhost anymore}
4. Go to Spotify Dashboard and get your client ID and secret ID, paste that in server.py
5. In dashboard create a new app and add the redirect uri = your ngrok url
6. Download Claude Local -> Go to settings -> Edit configuration and edit the claude_desktop_config.json to the following and restart Claude-:

```json
{
  "mcpServers": {
    "spotify": {
      "command": "/Users/smol/.local/bin/uv",
      "args": [
        "--directory",
        "/Users/smol/fun/mcp-server/mcp-server-demo",
        "run",
        "server.py"
      ]
    }
  }
}
```

7. uv run server.py and open Claude again. Now you'll see all the MCP tools and you can ask Claude to access Spotify for you.

Features-:
🔊 Playback Controls
  ✅ Play/pause/next
  🔁 Shuffle and repeat modes
  🎧 Play full album by name
  🔄 Autoplay based on mood (infinite playlist)

🎶 Playlist Wizardry
📀 Create playlists by:
  Genre
  Mood
  Custom song list
  ➕ Add a song to an existing playlist by name
  🗑️ Delete playlists by name
  🎯 Fetch playlist content with track + artist

🎙️ Lyrics & Info
  📃 Get lyrics of any song (Genius API)
  🎵 Get lyrics of currently playing song
  📌 Show current playing song + metadata

💡 Smart Recommendations
  🧠 Recommend songs based on recent listening
  👥 Get recently played artists
  🔍 Find albums by artist
  📚 List liked songs
