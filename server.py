import re
import time
from bs4 import BeautifulSoup
import json
import mcp.server.fastmcp
import requests
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

GENIUS_API_KEY = 'api_key'  
GENIUS_BASE_URL = "https://api.genius.com"

auth = SpotifyOAuth(
    client_id="id",
    client_secret="secret",
    redirect_uri="https://7a2d-2401-4900-1c66-8714-384b-cd3a-6f79-58bb.ngrok-free.app/callback",

    scope="user-library-read user-read-recently-played user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-modify-public playlist-modify-private",
    cache_path=".cache",
    open_browser=True
)

def get_genius_lyrics(song_name: str, artist_name: str = "") -> str:
    '''Search Genius by song and optional artist, extract lyrics from page'''
    search_query = f"{song_name} {artist_name}".strip()
    search_url = f"{GENIUS_BASE_URL}/search"
    headers = {"Authorization": f"Bearer {GENIUS_API_KEY}"}
    params = {"q": search_query}

    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code != 200:
        return f"Genius API error: {response.status_code}"

    hits = response.json().get("response", {}).get("hits", [])
    if not hits:
        return f"No lyrics found for '{search_query}'."

    # find match
    match = None
    for hit in hits:
        primary_artist = hit["result"]["primary_artist"]["name"].lower()
        if artist_name.lower() in primary_artist:
            match = hit
            break
    if not match:
        match = hits[0]  # fallback to first result

    song_url = match["result"]["url"]
    page = requests.get(song_url)
    if page.status_code != 200:
        return "Could not load Genius lyrics page."

    soup = BeautifulSoup(page.text, "html.parser")
    lyrics_divs = soup.find_all("div", class_=re.compile("^Lyrics__Container"))
    if not lyrics_divs:
        return "Lyrics not found on Genius page."

    lyrics = "\n\n".join(div.get_text(separator="\n").strip() for div in lyrics_divs)
    return lyrics

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
def now_playing():
    """What's playing now?"""
    current = sp.current_playback()
    if not current or not current["item"]:
        return "Nothing playing."
    track = current["item"]
    name = track["name"]
    artist = track["artists"][0]["name"]
    lyrics = get_genius_lyrics(name, artist)
    return f"Currenly playing: {name} by {artist}\n\n{lyrics}"

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
        "uri": track["external_urls"]["spotify"] 
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
    """ Returns list of all songs from the playlist, along with artist"""
    song_names = []
    offset = 0
    while True:
        response = sp.playlist_items(playlist_id, limit=100, offset=offset)
        items = response.get("items", [])
        for item in items:
            track = item.get("track")
            if track:
                name = track["name"]
                artist = track["artists"][0]["name"]
                song_names.append(f"{name} - {artist}")
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
    genre_list = mood_genres.get(mood.lower())
    if not genre_list:
        return f"Mood '{mood}' not recognized. Try 'happy', 'chill', or 'energetic'."

    available_genres = sp.recommendation_genre_seeds()
    valid_genres = [g for g in genre_list if g in available_genres]
    if not valid_genres:
        return f"No valid genres found for mood '{mood}'."
    
    return create_playlist_from_genre(valid_genres[0])


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


@server.tool() 
def get_lyrics(song_name: str, artist_name: str = "") -> str:
    '''Fetches lyrics for the song from Genius API'''
    return get_genius_lyrics(song_name, artist_name)

@server.tool()
def recommend_from_history() -> str:
    """ What should I listen to? Recommends users songs from recently played"""
    tracks = sp.current_user_recently_played(limit=10)["items"]
    seed_tracks = [t["track"]["id"] for t in tracks[:5]]
    recommendations = sp.recommendations(seed_tracks=seed_tracks, limit=10)["tracks"]
    names = [f"{t['name']} — {t['artists'][0]['name']}" for t in recommendations]
    return "Try these:\n" + "\n".join(names)

if __name__ == "__main__":
    server.run(transport='stdio')