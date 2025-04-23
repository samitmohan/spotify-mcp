# server.py
import mcp.server.fastmcp
import requests
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

auth = SpotifyOAuth(
    client_id="5b9cbf0ca9a74465b95990d35533b683",
    client_secret="cef1471968c64093bf54d55a1b0030df",
    redirect_uri="https://677f-2401-4900-1c66-8714-2985-b5c4-138c-e774.ngrok-free.app/callback/",
    scope="user-modify-playback-state user-read-playback-state user-read-currently-playing"
)

sp = Spotify(auth_manager=auth)

# Create an MCP server
server = mcp.server.fastmcp.FastMCP("Demo")

# Spotify tools
@server.tool()
def play_music():
    """Plays music when user tells agent to plays the current track"""
    sp.start_playback()
    return "Playback started!"

@server.tool()
def pause_music():
    """Pauses music when user tells agent to pause the current track"""
    sp.pause_playback()
    return "Playback paused!"

@server.tool()
def next_track():
    """Plays the next track queued"""
    sp.next_track()
    return "Skipped to next track!"

@server.tool()
def addQueue(query: str):
    """Adds user choice of song to queue for next"""
    song_name = query
    sp.add_to_queue(song_name)
    return "Added to queue!"

@server.tool()
def play_song(query: str):
    """Takes custom query from user and plays that song on Spotify"""
    results = sp.search(q=query, limit=1, type="track")
    if not results["tracks"]["items"]: return "Song not found."
    uri = results["tracks"]["items"][0]["uri"]
    sp.start_playback(uris=[uri])
    return f"Playing {query}."

@server.tool()
def spotify_current_track() -> str:
    """What's playing now?"""
    current = sp.current_playback()
    if current and current['item']:
        track = current['item']
        return f"Currently playing: {track['name']} by {track['artists'][0]['name']}"
    return "Nothing is currently playing."

@server.tool()
def create_playlist_from_genre(genre: str) -> str:
    """
    Create a new playlist based on genre and add tracks to it.
    """
    user = sp.me()
    user_id = user["id"]
    
    playlist_name = f"{genre.title()} Vibes"
    playlist = sp.user_playlist_create(user_id, playlist_name, public=False)
    
    # Search for tracks by genre
    results = sp.search(q=f"genre:{genre}", type="track", limit=13)
    tracks = results["tracks"]["items"]
    
    if not tracks: return f"No tracks found for genre '{genre}'."

    track_uris = [track["uri"] for track in tracks]
    sp.playlist_add_items(playlist["id"], track_uris)

    return f"Created playlist '{playlist_name}' with {len(track_uris)} {genre} tracks."

@server.tool()
def add_song_to_named_playlist(song: str, playlist_name: str) -> str:
    """
    Add a specific song to a playlist by name.
    """
    user_id = sp.me()["id"]
    playlists = sp.current_user_playlists(limit=50)

    # Search for matching playlist (case-insensitive)
    target = next((p for p in playlists["items"] if p["name"].lower() == playlist_name.lower()), None)

    if not target:
        return f"Playlist '{playlist_name}' not found."

    # Search for the song
    results = sp.search(q=song, limit=1, type="track")
    if not results["tracks"]["items"]:
        return f"Song '{song}' not found."

    track_uri = results["tracks"]["items"][0]["uri"]

    # Add to playlist
    sp.playlist_add_items(target["id"], [track_uri])
    return f"Added '{song}' to playlist '{playlist_name}'."


if __name__ == "__main__":
    server.run(transport='stdio')
