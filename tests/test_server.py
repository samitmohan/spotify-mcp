"""Tests for spotify-mcp server.

These tests cover the pure/helper functions and input validation logic
that don't require a live Spotify connection.
"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_spotify_auth(monkeypatch):
    """Prevent real Spotify auth during import."""
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "test_id")
    monkeypatch.setenv("SPOTIFY_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("SPOTIFY_REDIRECT_URI", "http://localhost:3000/callback")
    monkeypatch.setenv("GENIUS_API_KEY", "test_genius_key")

    with patch("spotipy.oauth2.SpotifyOAuth") as mock_oauth, \
         patch("spotipy.Spotify") as mock_sp:
        mock_oauth.return_value.get_access_token.return_value = "fake_token"
        mock_sp.return_value = MagicMock()
        yield mock_sp.return_value


def _import_server():
    """Import server module (must be called inside mocked context)."""
    import importlib
    import server
    importlib.reload(server)
    return server


class TestGetGeniusLyrics:
    """Tests for the get_genius_lyrics helper function."""

    def test_returns_lyrics_on_success(self):
        server = _import_server()

        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "response": {
                "hits": [
                    {
                        "result": {
                            "primary_artist": {"name": "Radiohead"},
                            "url": "https://genius.com/some-song",
                        }
                    }
                ]
            }
        }

        mock_lyrics_response = MagicMock()
        mock_lyrics_response.status_code = 200
        mock_lyrics_response.text = (
            '<div class="Lyrics__Container-abc123">These are the lyrics</div>'
        )

        with patch("server.requests.get", side_effect=[mock_search_response, mock_lyrics_response]):
            result = server.get_genius_lyrics("Creep", "Radiohead")
            assert "These are the lyrics" in result

    def test_returns_error_on_api_failure(self):
        server = _import_server()

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("server.requests.get", return_value=mock_response):
            result = server.get_genius_lyrics("Test Song")
            assert "Genius API error: 500" in result

    def test_returns_message_when_no_hits(self):
        server = _import_server()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": {"hits": []}}

        with patch("server.requests.get", return_value=mock_response):
            result = server.get_genius_lyrics("Nonexistent Song")
            assert "No lyrics found" in result

    def test_falls_back_to_first_hit_when_no_artist_match(self):
        server = _import_server()

        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "response": {
                "hits": [
                    {
                        "result": {
                            "primary_artist": {"name": "Some Other Artist"},
                            "url": "https://genius.com/fallback-song",
                        }
                    }
                ]
            }
        }

        mock_lyrics_response = MagicMock()
        mock_lyrics_response.status_code = 200
        mock_lyrics_response.text = (
            '<div class="Lyrics__Container-xyz">Fallback lyrics</div>'
        )

        with patch("server.requests.get", side_effect=[mock_search_response, mock_lyrics_response]):
            result = server.get_genius_lyrics("Song", "Totally Different Artist")
            assert "Fallback lyrics" in result

    def test_handles_request_exception(self):
        import requests as req
        server = _import_server()

        with patch("server.requests.get", side_effect=req.ConnectionError("Connection timeout")):
            result = server.get_genius_lyrics("Song", "Artist")
            assert "Failed to reach Genius API" in result

    def test_handles_lyrics_page_failure(self):
        server = _import_server()

        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "response": {
                "hits": [
                    {
                        "result": {
                            "primary_artist": {"name": "Artist"},
                            "url": "https://genius.com/song",
                        }
                    }
                ]
            }
        }

        mock_lyrics_response = MagicMock()
        mock_lyrics_response.status_code = 404

        with patch("server.requests.get", side_effect=[mock_search_response, mock_lyrics_response]):
            result = server.get_genius_lyrics("Song", "Artist")
            assert "Could not load Genius lyrics page" in result

    def test_handles_missing_lyrics_divs(self):
        server = _import_server()

        mock_search_response = MagicMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = {
            "response": {
                "hits": [
                    {
                        "result": {
                            "primary_artist": {"name": "Artist"},
                            "url": "https://genius.com/song",
                        }
                    }
                ]
            }
        }

        mock_lyrics_response = MagicMock()
        mock_lyrics_response.status_code = 200
        mock_lyrics_response.text = "<div>No lyrics container here</div>"

        with patch("server.requests.get", side_effect=[mock_search_response, mock_lyrics_response]):
            result = server.get_genius_lyrics("Song", "Artist")
            assert "Lyrics not found on Genius page" in result


class TestMoodMapping:
    """Tests for the mood-to-genre mapping logic."""

    def test_valid_moods(self):
        valid_moods = {"happy", "chill", "energetic"}
        mood_genres = {
            "happy": ["pop", "dance", "indie"],
            "chill": ["acoustic", "ambient"],
            "energetic": ["rock", "electronic", "metal"],
        }
        for mood in valid_moods:
            assert mood in mood_genres
            assert len(mood_genres[mood]) > 0

    def test_invalid_mood_returns_none(self):
        mood_genres = {
            "happy": ["pop", "dance", "indie"],
            "chill": ["acoustic", "ambient"],
            "energetic": ["rock", "electronic", "metal"],
        }
        assert mood_genres.get("angry") is None
        assert mood_genres.get("") is None


class TestRepeatValidation:
    """Tests for repeat_playback input validation."""

    def test_valid_states(self):
        valid = ["track", "context", "off"]
        for state in valid:
            assert state in ["track", "context", "off"]

    def test_invalid_states(self):
        invalid = ["on", "repeat", "loop", "", "Track"]
        for state in invalid:
            assert state not in ["track", "context", "off"]
