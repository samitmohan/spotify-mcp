To start -:

1. Clone repo
2. Download dependencies -> uv, requests, mcp, spotipy via pip
3. Use ngrok for tunnelling localhost -> ngrok 3000 {spotify doesn't support localhost anymore}
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

7: uv run server.py and open Claude again. Now you'll see all the MCP tools and you can ask Claude to access Spotify for you.

Blog on this -:
https://samit.bearblog.dev/mcp-servers/

Video Demo -:
