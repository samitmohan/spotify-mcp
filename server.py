# server.py
import re
import time
import json
import mcp.server.fastmcp
import requests
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

auth = SpotifyOAuth(
    client_id="id",
    client_secret="secret",
    redirect_uri="https://baef-2401-4900-1c66-8714-2985-b5c4-138c-e774.ngrok-free.app/callback",
    scope="user-modify-playback-state user-read-playback-state user-read-currently-playing playlist-modify-public playlist-modify-private",
    cache_path=".cache",
    open_browser=True
)

token_info = auth.get_access_token(as_dict=False)
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
    # First, search for the track
    results = sp.search(q=query, limit=1, type="track")
    if not results["tracks"]["items"]:
        return f"Could not find '{query}'."

    # Extract the URI and add to queue
    uri = results["tracks"]["items"][0]["uri"]
    sp.add_to_queue(uri)
    return f"Added '{query}' to queue!"

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

"""
Do I even need this?
@server.tool()
def create_playlist_from_genre(genre: str) -> str:
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
"""

# Can I integrate this into the mood function?
@server.tool()
def create_playlist_from_genre(genre: str, limit: int = 20) -> str:
    """ Create a new playlist based on genre and add tracks to it.  """
    limit = min(limit, 50)
    user_id = sp.me()["id"]
    playlist_name = f"{genre.title()} Vibes"
    playlist = sp.user_playlist_create(user_id, playlist_name, public=False)
    results = sp.recommendations(seed_genres=[genre], limit=limit)
    tracks = results.get("tracks", [])
    if not tracks:
        return f"No tracks found for genre '{genre}'."
    track_uris = [track["uri"] for track in tracks]
    sp.playlist_add_items(playlist["id"], track_uris)
    return f"Created playlist '{playlist_name}' with {len(track_uris)} {genre} tracks."

# Can I integrate this to multiple song playlist function?
@server.tool()
def add_song_to_named_playlist(song: str, playlist_name: str) -> str:
    """
    Add a specific song to a playlist by name.
    """
    user_id = sp.me()["id"]
    playlists = sp.current_user_playlists(limit=50)
    time.sleep(2) # to prevent eventual consistency
    target = next((p for p in playlists["items"] if p["name"].lower() == playlist_name.lower()), None)

    if not target:
        return f"Playlist '{playlist_name}' not found."

    results = sp.search(q=song, limit=1, type="track")

    if not results["tracks"]["items"]:
        return f"Song '{song}' not found."

    track_uri = results["tracks"]["items"][0]["uri"]

    # add to playlist
    sp.playlist_add_items(target["id"], [track_uri])
    return f"Added '{song}' to playlist '{playlist_name}'."

@server.tool()
def spotify_getInfo() -> dict | str:
    """ Gets information about the current song """
    curr = sp.current_playback()
    if not curr or not curr.get("item"): return "Nothing is currently playing"
    track = curr["item"]
    return {
        "name": track["name"],
        "artist": track["artists"][0]["name"],
        "album": track["album"]["name"],
        "release_date": track["album"]["release_date"],
        "uri": track["uri"],
    }

@server.tool()
def get_myPlaylists() -> str:
    """Lists all of my playlists"""
    playlists = []
    offset = 0
    while True:
        response = sp.current_user_playlists(limit=50, offset=offset)
        items = response.get("items", [])
        for i, playlist in enumerate(items, start=offset+1):
            name = playlist["name"]
            url = playlist["external_urls"]["spotify"]
            playlists.append(f"{i}. {name} - {url}")
        if response["next"]: offset += 50
        else: break 
    return "\n".join(playlists) if playlists else "No playlists found"

@server.tool()
def get_songs_from_playlist(playlist_id: str) -> str:
    """ Returns list of all songs from the playlist"""
    song_names = []
    offset = 0
    while True:
        response = sp.playlist_items(playlist_id, limit=100, offset=offset)
        items = response.get("items", [])
        for item in items:
            track = item.get("track")
            if track:
                song_names.append(track["name"])
        if response.get("next"):
            offset += 100
        else:
            break
    return "\n".join([f"{i+1}. {song}" for i, song in enumerate(song_names)]) if song_names else "No songs found in that playlist."

@server.tool()
def create_playlist_with_song(song: str) -> str:
    """ Creates a playlist with a specific song """
    user_id = sp.me()["id"]
    results = sp.search(q=song, type="track", limit=1)
    track = results.get("tracks", {}).get("items", [None])[0]
    if not track:
        return f"Song '{song}' not found."
    playlist = sp.user_playlist_create(user_id, "new playlist", public=False)
    sp.playlist_add_items(playlist["id"], [track["uri"]])
    return f"Created playlist 'new playlist' with 1 song: '{track['name']}' by {track['artists'][0]['name']}."

@server.tool()
def list_favourite_songs() -> str:
    """ Returns list of all liked songs by user """
    songs = []
    offset = 0
    while offset < 100:
        results = sp.current_user_saved_tracks(limit=50, offset=offset)
        items = results.get("items", [])
        for item in items:
            track = item["track"]
            songs.append(f"{track['name']} — {track['artists'][0]['name']}")
        offset += 50
        if not results["next"]:
            break
    return "\n".join(songs) if songs else "You don't have any liked songs."

@server.tool()
def get_recently_played_artists() -> str:
    """ Gets recently played artist by the user """
    results = sp.current_user_recently_played(limit=50)
    items = results.get("items", [])
    seen = set()
    artists = []
    for item in items:
        name = item["track"]["artists"][0]["name"]
        if name not in seen:
            seen.add(name)
            artists.append(name)
    return "\n".join([f"{i+1}. {name}" for i, name in enumerate(artists)]) if artists else "No recent artists found."

@server.tool()
def get_artist_albums(artist_name: str) -> str:
    """ Gets list of albums by the artist """
    results = sp.search(q=artist_name, type="artist", limit=1)
    artists = results.get("artists", {}).get("items", [])
    if not artists:
        return f"Artist '{artist_name}' not found."
    artist_id = artists[0]["id"]
    albums = sp.artist_albums(artist_id, album_type="album", limit=50).get("items", [])
    if not albums:
        return f"No albums found for artist '{artist_name}'."
    return "\n".join([f"{i+1}. {album['name']} ({album['release_date']})" for i, album in enumerate(albums)])

@server.tool()
def shuffle_playback(shuffle: bool) -> str:
    """Toggles shuffle playback"""
    sp.shuffle(shuffle)
    return "Shuffle is now " + ("on" if shuffle else "off.")

@server.tool()
def repeat_playback(state: str) -> str:
    """Sets repeat mode"""
    if state not in ['track', 'context', 'off']:
        return "Repeat state must be 'track', 'context', or 'off'."
    sp.repeat(state)
    return f"Repeat mode set to {state}."

@server.tool()
def play_album(album_name: str):
    """Search and play an entire album"""
    results = sp.search(q=album_name, type="album", limit=1)
    if not results['albums']['items']:
        return f"Album '{album_name}' not found."
    album_uri = results['albums']['items'][0]['uri']
    sp.start_playback(context_uri=album_uri)
    return f"Playing album '{album_name}'."

@server.tool()
def create_playlist_with_multiple_tracks(track_list: list) -> str:
    """Creates a playlist with multiple tracks"""
    user_id = sp.me()["id"]
    playlist_name = "Custom Playlist"
    playlist = sp.user_playlist_create(user_id, playlist_name, public=False)
    track_uris = []
    for track in track_list:
        results = sp.search(q=track, limit=1, type="track")
        if results["tracks"]["items"]:
            track_uris.append(results["tracks"]["items"][0]["uri"])
        else:
            return f"Could not find one or more tracks from your list."
    sp.playlist_add_items(playlist["id"], track_uris)
    return f"Created playlist '{playlist_name}' with {len(track_uris)} tracks."

@server.tool()
def create_playlist_from_mood(mood: str) -> str:
    """Create a playlist based on mood"""
    mood_genres = {
        "happy": ["pop", "dance", "indie"],
        "chill": ["acoustic", "lofi", "ambient"],
        "energetic": ["rock", "electronic", "metal"],
    }
    genre = mood_genres.get(mood.lower())
    if not genre:
        return f"Mood '{mood}' not recognized. Try 'happy', 'chill', or 'energetic'."
    return create_playlist_from_genre(genre[0])  # Use the genre to generate playlist

@server.tool()
def delete_playlist(playlist_name: str) -> str:
    """Deletes a playlist by name"""
    user_id = sp.me()["id"]
    
    # Get user's playlists
    playlists = sp.current_user_playlists(limit=50)
    target = next((p for p in playlists["items"] if p["name"].lower() == playlist_name.lower()), None)
    
    if not target:
        return f"Playlist '{playlist_name}' not found."
    
    # Delete (unfollow) the playlist
    sp.user_playlist_unfollow(user_id, target["id"])
    return f"Playlist '{playlist_name}' has been deleted."

"""
GENIUS_API_KEY = 'apikey'  
GENIUS_BASE_URL = 'https://api.genius.com'

def get_genius_lyrics(song_name: str) -> str:
    '''Fetch lyrics from the Genius API'''
    search_url = f"{GENIUS_BASE_URL}/search"
    params = {'q': song_name}
    headers = {'Authorization': f'Bearer {GENIUS_API_KEY}'}
    
    # GET request
    response = requests.get(search_url, params=params, headers=headers)
    response_data = response.json()

    if response_data['response']['hits']:
        # best match
        song_info = response_data['response']['hits'][0]['result']
        song_url = song_info['url']
        
        # fetch lyrics
        song_page = requests.get(song_url)
        song_page_content = song_page.text
        
        # regex magic (html -> regex)
        lyrics_match = re.search(r'<div class="lyrics">.*?<p>(.*?)</p>', song_page_content, re.S)
        if lyrics_match:
            lyrics = lyrics_match.group(1).replace('<br/>', '\n')  # Clean up the lyrics
            return lyrics
        else:
            return "Lyrics not found on Genius."
    else:
        return "Song not found in Genius database."

# TODO : add genius api integeration for lyrics
@server.tool()
def get_lyrics(song_name: str) -> str:
    lyrics = genius_api.get_lyrics(song_name)  # Assuming integration with Genius
    return lyrics if lyrics else "Lyrics not found."
"""

if __name__ == "__main__":
    server.run(transport='stdio')

