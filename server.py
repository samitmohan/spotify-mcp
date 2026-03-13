import logging
import os
import re

import mcp.server.fastmcp
import requests
from bs4 import BeautifulSoup
from spotipy import Spotify
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyOAuth

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("spotify-mcp")

GENIUS_API_KEY = os.environ.get("GENIUS_API_KEY", "")
GENIUS_BASE_URL = "https://api.genius.com"

REQUEST_TIMEOUT = 10

auth = SpotifyOAuth(
    client_id=os.environ["SPOTIFY_CLIENT_ID"],
    client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
    scope=(
        "user-library-read user-read-recently-played "
        "user-read-playback-state user-modify-playback-state "
        "user-read-currently-playing playlist-modify-public "
        "playlist-modify-private"
    ),
    cache_path=".cache",
    open_browser=True,
)


def get_genius_lyrics(song_name: str, artist_name: str = "") -> str:
    """Search Genius by song and optional artist, extract lyrics from page."""
    search_query = f"{song_name} {artist_name}".strip()
    search_url = f"{GENIUS_BASE_URL}/search"
    headers = {"Authorization": f"Bearer {GENIUS_API_KEY}"}
    params = {"q": search_query}

    try:
        response = requests.get(search_url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        logger.error("Genius search request failed: %s", exc)
        return f"Failed to reach Genius API: {exc}"

    if response.status_code != 200:
        return f"Genius API error: {response.status_code}"

    hits = response.json().get("response", {}).get("hits", [])
    if not hits:
        return f"No lyrics found for '{search_query}'."

    # Find best match by artist name
    match = None
    for hit in hits:
        primary_artist = hit["result"]["primary_artist"]["name"].lower()
        if artist_name.lower() in primary_artist:
            match = hit
            break
    if not match:
        match = hits[0]  # Fallback to first result

    song_url = match["result"]["url"]
    try:
        page = requests.get(song_url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        logger.error("Genius lyrics page request failed: %s", exc)
        return "Could not load Genius lyrics page."

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

server = mcp.server.fastmcp.FastMCP("Spotify")


# -- Playback Controls --


@server.tool()
def play_music() -> str:
    """Plays music when user tells agent to play the current track."""
    try:
        sp.start_playback()
    except SpotifyException as exc:
        logger.error("play_music failed: %s", exc)
        return f"Failed to start playback: {exc}"
    return "Playback started!"


@server.tool()
def pause_music() -> str:
    """Pauses music when user tells agent to pause the current track."""
    try:
        sp.pause_playback()
    except SpotifyException as exc:
        logger.error("pause_music failed: %s", exc)
        return f"Failed to pause playback: {exc}"
    return "Playback paused!"


@server.tool()
def next_track() -> str:
    """Plays the next track queued."""
    try:
        sp.next_track()
    except SpotifyException as exc:
        logger.error("next_track failed: %s", exc)
        return f"Failed to skip track: {exc}"
    return "Skipped to next track!"


@server.tool()
def add_to_queue(query: str) -> str:
    """Adds user choice of song to queue for next."""
    try:
        results = sp.search(q=query, limit=1, type="track")
        if not results["tracks"]["items"]:
            return f"Could not find '{query}'."

        uri = results["tracks"]["items"][0]["uri"]
        sp.add_to_queue(uri)
    except SpotifyException as exc:
        logger.error("add_to_queue failed: %s", exc)
        return f"Failed to add to queue: {exc}"
    return f"Added '{query}' to queue!"


@server.tool()
def play_song(query: str) -> str:
    """Takes custom query from user and plays that song on Spotify."""
    try:
        results = sp.search(q=query, limit=1, type="track")
        if not results["tracks"]["items"]:
            return "Song not found."
        uri = results["tracks"]["items"][0]["uri"]
        sp.start_playback(uris=[uri])
    except SpotifyException as exc:
        logger.error("play_song failed: %s", exc)
        return f"Failed to play song: {exc}"
    return f"Playing {query}."


@server.tool()
def now_playing() -> str:
    """Shows what is currently playing, including lyrics."""
    try:
        current = sp.current_playback()
    except SpotifyException as exc:
        logger.error("now_playing failed: %s", exc)
        return f"Failed to get playback info: {exc}"

    if not current or not current.get("item"):
        return "Nothing playing."
    track = current["item"]
    name = track["name"]
    artist = track["artists"][0]["name"]
    lyrics = get_genius_lyrics(name, artist)
    return f"Currently playing: {name} by {artist}\n\n{lyrics}"


@server.tool()
def shuffle_playback(shuffle: bool) -> str:
    """Toggles shuffle playback."""
    try:
        sp.shuffle(shuffle)
    except SpotifyException as exc:
        logger.error("shuffle_playback failed: %s", exc)
        return f"Failed to set shuffle: {exc}"
    return "Shuffle is now " + ("on." if shuffle else "off.")


@server.tool()
def repeat_playback(state: str) -> str:
    """Sets repeat mode. State must be 'track', 'context', or 'off'."""
    if state not in ["track", "context", "off"]:
        return "Repeat state must be 'track', 'context', or 'off'."
    try:
        sp.repeat(state)
    except SpotifyException as exc:
        logger.error("repeat_playback failed: %s", exc)
        return f"Failed to set repeat: {exc}"
    return f"Repeat mode set to {state}."


@server.tool()
def play_album(album_name: str) -> str:
    """Search and play an entire album."""
    try:
        results = sp.search(q=album_name, type="album", limit=1)
        if not results["albums"]["items"]:
            return f"Album '{album_name}' not found."
        album_uri = results["albums"]["items"][0]["uri"]
        sp.start_playback(context_uri=album_uri)
    except SpotifyException as exc:
        logger.error("play_album failed: %s", exc)
        return f"Failed to play album: {exc}"
    return f"Playing album '{album_name}'."


# -- Playlist Management --


@server.tool()
def get_playlists() -> str:
    """Lists all of the user's playlists."""
    try:
        playlists = []
        offset = 0
        while True:
            response = sp.current_user_playlists(limit=50, offset=offset)
            items = response.get("items", [])
            for i, playlist in enumerate(items, start=offset + 1):
                name = playlist["name"]
                url = playlist["external_urls"]["spotify"]
                playlists.append(f"{i}. {name} - {url}")
            if response["next"]:
                offset += 50
            else:
                break
    except SpotifyException as exc:
        logger.error("get_playlists failed: %s", exc)
        return f"Failed to fetch playlists: {exc}"
    return "\n".join(playlists) if playlists else "No playlists found."


@server.tool()
def get_songs_from_playlist(playlist_id: str) -> str:
    """Returns list of all songs from a playlist, along with artist."""
    try:
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
    except SpotifyException as exc:
        logger.error("get_songs_from_playlist failed: %s", exc)
        return f"Failed to fetch playlist songs: {exc}"
    return (
        "\n".join(f"{i + 1}. {song}" for i, song in enumerate(song_names))
        if song_names
        else "No songs found in that playlist."
    )


@server.tool()
def create_playlist_from_genre(genre: str, limit: int = 20) -> str:
    """Create a new playlist based on genre and add tracks to it."""
    limit = min(limit, 50)
    try:
        user_id = sp.me()["id"]
        playlist_name = f"{genre.title()} Vibes"
        playlist = sp.user_playlist_create(user_id, playlist_name, public=False)
        results = sp.recommendations(seed_genres=[genre], limit=limit)
        tracks = results.get("tracks", [])
        if not tracks:
            return f"No tracks found for genre '{genre}'."
        track_uris = [track["uri"] for track in tracks]
        sp.playlist_add_items(playlist["id"], track_uris)
    except SpotifyException as exc:
        logger.error("create_playlist_from_genre failed: %s", exc)
        return f"Failed to create genre playlist: {exc}"
    return f"Created playlist '{playlist_name}' with {len(track_uris)} {genre} tracks."


@server.tool()
def add_song_to_playlist(song: str, playlist_name: str) -> str:
    """Add a specific song to a playlist by name."""
    try:
        playlists = sp.current_user_playlists(limit=50)
        target = next(
            (p for p in playlists["items"] if p["name"].lower() == playlist_name.lower()),
            None,
        )
        if not target:
            return f"Playlist '{playlist_name}' not found."

        results = sp.search(q=song, limit=1, type="track")
        if not results["tracks"]["items"]:
            return f"Song '{song}' not found."

        track_uri = results["tracks"]["items"][0]["uri"]
        sp.playlist_add_items(target["id"], [track_uri])
    except SpotifyException as exc:
        logger.error("add_song_to_playlist failed: %s", exc)
        return f"Failed to add song to playlist: {exc}"
    return f"Added '{song}' to playlist '{playlist_name}'."


@server.tool()
def create_playlist_with_song(song: str) -> str:
    """Creates a playlist with a specific song."""
    try:
        user_id = sp.me()["id"]
        results = sp.search(q=song, type="track", limit=1)
        track = results.get("tracks", {}).get("items", [None])[0]
        if not track:
            return f"Song '{song}' not found."
        playlist = sp.user_playlist_create(user_id, "new playlist", public=False)
        sp.playlist_add_items(playlist["id"], [track["uri"]])
    except SpotifyException as exc:
        logger.error("create_playlist_with_song failed: %s", exc)
        return f"Failed to create playlist: {exc}"
    return f"Created playlist 'new playlist' with 1 song: '{track['name']}' by {track['artists'][0]['name']}."


@server.tool()
def create_playlist_with_multiple_tracks(track_list: list) -> str:
    """Creates a playlist with multiple tracks."""
    try:
        user_id = sp.me()["id"]
        playlist_name = "Custom Playlist"
        playlist = sp.user_playlist_create(user_id, playlist_name, public=False)
        track_uris = []
        for track in track_list:
            results = sp.search(q=track, limit=1, type="track")
            if results["tracks"]["items"]:
                track_uris.append(results["tracks"]["items"][0]["uri"])
            else:
                return f"Could not find track: '{track}'."
        sp.playlist_add_items(playlist["id"], track_uris)
    except SpotifyException as exc:
        logger.error("create_playlist_with_multiple_tracks failed: %s", exc)
        return f"Failed to create playlist: {exc}"
    return f"Created playlist '{playlist_name}' with {len(track_uris)} tracks."


@server.tool()
def create_playlist_from_mood(mood: str) -> str:
    """Create a playlist based on mood (happy, chill, or energetic)."""
    mood_genres = {
        "happy": ["pop", "dance", "indie"],
        "chill": ["acoustic", "ambient"],
        "energetic": ["rock", "electronic", "metal"],
    }
    genre_list = mood_genres.get(mood.lower())
    if not genre_list:
        return f"Mood '{mood}' not recognized. Try 'happy', 'chill', or 'energetic'."

    try:
        available = sp.recommendation_genre_seeds()
        available_genres = available.get("genres", [])
    except SpotifyException as exc:
        logger.error("create_playlist_from_mood failed to get genre seeds: %s", exc)
        return f"Failed to fetch available genres: {exc}"

    valid_genres = [g for g in genre_list if g in available_genres]
    if not valid_genres:
        return f"No valid genres found for mood '{mood}'."

    return create_playlist_from_genre(valid_genres[0])


@server.tool()
def delete_playlist(playlist_name: str) -> str:
    """Deletes a playlist by name."""
    try:
        user_id = sp.me()["id"]
        playlists = sp.current_user_playlists(limit=50)
        target = next(
            (p for p in playlists["items"] if p["name"].lower() == playlist_name.lower()),
            None,
        )
        if not target:
            return f"Playlist '{playlist_name}' not found."

        sp.user_playlist_unfollow(user_id, target["id"])
    except SpotifyException as exc:
        logger.error("delete_playlist failed: %s", exc)
        return f"Failed to delete playlist: {exc}"
    return f"Playlist '{playlist_name}' has been deleted."


# -- Track Info & Lyrics --


@server.tool()
def get_track_info() -> str:
    """Gets information about the currently playing song."""
    try:
        curr = sp.current_playback()
    except SpotifyException as exc:
        logger.error("get_track_info failed: %s", exc)
        return f"Failed to get track info: {exc}"

    if not curr or not curr.get("item"):
        return "Nothing is currently playing."
    track = curr["item"]
    info = {
        "name": track["name"],
        "artist": track["artists"][0]["name"],
        "album": track["album"]["name"],
        "release_date": track["album"]["release_date"],
        "url": track["external_urls"]["spotify"],
    }
    return "\n".join(f"{k}: {v}" for k, v in info.items())


@server.tool()
def get_lyrics(song_name: str, artist_name: str = "") -> str:
    """Fetches lyrics for a song from the Genius API."""
    return get_genius_lyrics(song_name, artist_name)


# -- Library & Discovery --


@server.tool()
def list_liked_songs() -> str:
    """Returns list of liked songs by user."""
    try:
        songs = []
        offset = 0
        while offset < 100:
            results = sp.current_user_saved_tracks(limit=50, offset=offset)
            items = results.get("items", [])
            for item in items:
                track = item["track"]
                songs.append(f"{track['name']} - {track['artists'][0]['name']}")
            offset += 50
            if not results["next"]:
                break
    except SpotifyException as exc:
        logger.error("list_liked_songs failed: %s", exc)
        return f"Failed to fetch liked songs: {exc}"
    return "\n".join(songs) if songs else "You don't have any liked songs."


@server.tool()
def get_recently_played_artists() -> str:
    """Gets recently played artists by the user."""
    try:
        results = sp.current_user_recently_played(limit=50)
        items = results.get("items", [])
        seen = set()
        artists = []
        for item in items:
            name = item["track"]["artists"][0]["name"]
            if name not in seen:
                seen.add(name)
                artists.append(name)
    except SpotifyException as exc:
        logger.error("get_recently_played_artists failed: %s", exc)
        return f"Failed to fetch recent artists: {exc}"
    return (
        "\n".join(f"{i + 1}. {name}" for i, name in enumerate(artists))
        if artists
        else "No recent artists found."
    )


@server.tool()
def get_artist_albums(artist_name: str) -> str:
    """Gets list of albums by the artist."""
    try:
        results = sp.search(q=artist_name, type="artist", limit=1)
        artists = results.get("artists", {}).get("items", [])
        if not artists:
            return f"Artist '{artist_name}' not found."
        artist_id = artists[0]["id"]
        albums = sp.artist_albums(artist_id, album_type="album", limit=50).get("items", [])
    except SpotifyException as exc:
        logger.error("get_artist_albums failed: %s", exc)
        return f"Failed to fetch albums: {exc}"
    if not albums:
        return f"No albums found for artist '{artist_name}'."
    return "\n".join(
        f"{i + 1}. {album['name']} ({album['release_date']})" for i, album in enumerate(albums)
    )


@server.tool()
def recommend_from_history() -> str:
    """Recommends songs based on recently played tracks."""
    try:
        tracks = sp.current_user_recently_played(limit=10)["items"]
        seed_tracks = [t["track"]["id"] for t in tracks[:5]]
        recommendations = sp.recommendations(seed_tracks=seed_tracks, limit=10)["tracks"]
    except SpotifyException as exc:
        logger.error("recommend_from_history failed: %s", exc)
        return f"Failed to get recommendations: {exc}"
    names = [f"{t['name']} - {t['artists'][0]['name']}" for t in recommendations]
    return "Try these:\n" + "\n".join(names)


if __name__ == "__main__":
    logger.info("Starting Spotify MCP server")
    server.run(transport="stdio")
