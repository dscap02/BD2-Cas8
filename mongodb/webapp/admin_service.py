import base64
import re
from datetime import datetime, timezone
from typing import Any, Optional

import requests
from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError


ADMIN_CREATED_MARKER = "admin_dashboard"

SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_TRACK_URL = "https://api.spotify.com/v1/tracks"
SPOTIFY_OEMBED_URL = "https://open.spotify.com/oembed"


def normalize_text(value: Any) -> str:
    """Restituisce una stringa pulita."""
    if value is None:
        return ""

    return str(value).strip()


def normalize_optional_number(value: Any, number_type=float):
    """Converte un valore numerico opzionale oppure restituisce None."""
    value = normalize_text(value)

    if not value:
        return None

    try:
        return number_type(value)

    except ValueError:
        return None


def normalize_tags(raw_tags: str) -> list[str]:
    """
    Converte una stringa di tag separati da virgola in lista pulita.
    """
    if not raw_tags:
        return []

    return [
        tag.strip()
        for tag in raw_tags.split(",")
        if tag.strip()
    ]


def normalize_spotify_id(value: Any) -> Optional[str]:
    """
    Estrae uno Spotify track ID da:
    - ID semplice;
    - URI spotify:track:ID;
    - URL open.spotify.com/track/ID;
    - URL album con highlight=spotify:track:ID;
    - URL con highlight codificato spotify%3Atrack%3AID.
    """
    raw_value = normalize_text(value)

    if not raw_value:
        return None

    patterns = [
        r"highlight=spotify%3Atrack%3A([A-Za-z0-9]{22})",
        r"highlight=spotify:track:([A-Za-z0-9]{22})",
        r"spotify:track:([A-Za-z0-9]{22})",
        r"open\.spotify\.com/(?:intl-[a-z]{2}/)?track/([A-Za-z0-9]{22})",
    ]

    for pattern in patterns:
        match = re.search(pattern, raw_value)

        if match:
            return match.group(1)

    if re.fullmatch(r"[A-Za-z0-9]{22}", raw_value):
        return raw_value

    return None


def duration_to_ms(minutes: Any, seconds: Any) -> Optional[int]:
    """Converte minuti e secondi in millisecondi."""
    minutes_value = normalize_optional_number(minutes, int)
    seconds_value = normalize_optional_number(seconds, int)

    if minutes_value is None and seconds_value is None:
        return None

    minutes_value = minutes_value or 0
    seconds_value = seconds_value or 0

    if minutes_value < 0 or seconds_value < 0:
        return None

    return ((minutes_value * 60) + seconds_value) * 1000


def split_duration_ms(duration_ms: Any) -> tuple[str, str]:
    """Converte duration_ms in minuti e secondi per il form."""
    if duration_ms is None:
        return "", ""

    try:
        total_seconds = int(float(duration_ms)) // 1000

    except (TypeError, ValueError):
        return "", ""

    minutes, seconds = divmod(total_seconds, 60)

    return str(minutes), str(seconds)


def duration_ms_to_form_values(duration_ms: Any) -> dict:
    """Restituisce minuti e secondi come dizionario per il frontend."""
    minutes, seconds = split_duration_ms(duration_ms)

    return {
        "duration_minutes": minutes,
        "duration_seconds": seconds,
    }


def build_audio_features(form_data) -> dict:
    """
    Costruisce audio_features dai campi opzionali del form.
    I campi vuoti non vengono inseriti.
    """
    numeric_fields = {
        "danceability": float,
        "energy": float,
        "key": int,
        "loudness": float,
        "mode": int,
        "speechiness": float,
        "acousticness": float,
        "instrumentalness": float,
        "liveness": float,
        "valence": float,
        "tempo": float,
    }

    audio_features = {}

    for field_name, number_type in numeric_fields.items():
        value = normalize_optional_number(
            form_data.get(field_name),
            number_type,
        )

        if value is not None:
            audio_features[field_name] = value

    return audio_features


def get_spotify_access_token(
    client_id: Optional[str],
    client_secret: Optional[str],
) -> Optional[str]:
    """
    Recupera un access token Spotify tramite Client Credentials Flow.
    """
    if not client_id or not client_secret:
        return None

    credentials = f"{client_id}:{client_secret}".encode("utf-8")

    encoded_credentials = base64.b64encode(credentials).decode("utf-8")

    try:
        response = requests.post(
            SPOTIFY_TOKEN_URL,
            headers={
                "Authorization": f"Basic {encoded_credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
            },
            timeout=8,
        )

        response.raise_for_status()

        return response.json().get("access_token")

    except requests.RequestException:
        return None


def fetch_spotify_track_metadata(
    spotify_id: str,
    client_id: Optional[str],
    client_secret: Optional[str],
) -> Optional[dict]:
    """
    Recupera metadati completi di una traccia tramite Spotify Web API.

    Restituisce titolo, artista, album, anno, durata e immagine album.
    """
    access_token = get_spotify_access_token(
        client_id,
        client_secret,
    )

    if not access_token:
        return None

    try:
        response = requests.get(
            f"{SPOTIFY_TRACK_URL}/{spotify_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
            timeout=8,
        )

        response.raise_for_status()

        track_data = response.json()

        artists = track_data.get("artists", [])
        album = track_data.get("album", {})
        album_images = album.get("images", [])

        artist_name = (
            artists[0].get("name")
            if artists
            else ""
        )

        album_name = album.get("name", "")
        release_date = album.get("release_date", "")
        year = release_date[:4] if release_date else ""

        album_image_url = (
            album_images[0].get("url")
            if album_images
            else ""
        )

        return {
            "spotify_id": spotify_id,
            "name": track_data.get("name", ""),
            "artist_name": artist_name,
            "album_name": album_name,
            "album_release_date": release_date,
            "album_image_url": album_image_url,
            "year": year,
            "duration_ms": track_data.get("duration_ms"),
            **duration_ms_to_form_values(track_data.get("duration_ms")),
            "source": "spotify_web_api",
        }

    except requests.RequestException:
        return None


def fetch_spotify_oembed_metadata(
    spotify_id: str,
) -> Optional[dict]:
    """
    Fallback senza credenziali: recupera dati base tramite Spotify oEmbed.
    """
    if not spotify_id:
        return None

    spotify_url = f"https://open.spotify.com/track/{spotify_id}"

    try:
        response = requests.get(
            SPOTIFY_OEMBED_URL,
            params={
                "url": spotify_url,
            },
            timeout=6,
        )

        response.raise_for_status()

        data = response.json()

        return {
            "spotify_id": spotify_id,
            "name": normalize_text(data.get("title")),
            "artist_name": "",
            "album_name": "",
            "album_release_date": "",
            "album_image_url": data.get("thumbnail_url", ""),
            "year": "",
            "duration_ms": None,
            "duration_minutes": "",
            "duration_seconds": "",
            "source": "spotify_oembed",
        }

    except requests.RequestException:
        return None


def get_spotify_preview(
    spotify_value: str,
    client_id: Optional[str],
    client_secret: Optional[str],
) -> tuple[bool, dict | str]:
    """
    Estrae lo Spotify ID e prova a recuperare i metadati della traccia.

    Usa prima Spotify Web API, poi fallback oEmbed.
    """
    spotify_id = normalize_spotify_id(spotify_value)

    if not spotify_id:
        return False, "Link Spotify non valido."

    metadata = fetch_spotify_track_metadata(
        spotify_id=spotify_id,
        client_id=client_id,
        client_secret=client_secret,
    )

    if metadata:
        return True, metadata

    metadata = fetch_spotify_oembed_metadata(spotify_id)

    if metadata:
        return True, metadata

    return (
        False,
        "Non è stato possibile recuperare i dati da Spotify. Puoi comunque compilare il form manualmente.",
    )


def get_or_create_artist(
    db: Database,
    artist_name: str,
) -> ObjectId:
    """
    Recupera un artista esistente per nome oppure lo crea.
    """
    artist_name = normalize_text(artist_name)

    if not artist_name:
        raise ValueError("Inserisci il nome dell'artista.")

    existing_artist = db.artists.find_one(
        {
            "name": {
                "$regex": f"^{re.escape(artist_name)}$",
                "$options": "i",
            }
        }
    )

    if existing_artist:
        return existing_artist["_id"]

    result = db.artists.insert_one(
        {
            "name": artist_name,
            "created_by": ADMIN_CREATED_MARKER,
            "created_at": datetime.now(timezone.utc),
        }
    )

    return result.inserted_id


def get_or_create_genre_tag(
    db: Database,
    genre: str,
    tags: list[str],
) -> ObjectId:
    """
    Recupera un documento genres_tags compatibile oppure lo crea.
    """
    genre = normalize_text(genre)

    if not genre:
        raise ValueError("Inserisci il genere della traccia.")

    existing_genre_tag = db.genres_tags.find_one(
        {
            "genre": {
                "$regex": f"^{re.escape(genre)}$",
                "$options": "i",
            },
            "tags": tags,
        }
    )

    if existing_genre_tag:
        return existing_genre_tag["_id"]

    result = db.genres_tags.insert_one(
        {
            "genre": genre,
            "tags": tags,
            "created_by": ADMIN_CREATED_MARKER,
            "created_at": datetime.now(timezone.utc),
        }
    )

    return result.inserted_id


def build_track_document(
    db: Database,
    form_data,
) -> dict:
    """
    Crea un documento tracks a partire dai dati del form.
    """
    spotify_id = normalize_spotify_id(
        form_data.get("spotify_url")
        or form_data.get("spotify_id")
    )

    title = normalize_text(form_data.get("name"))

    if not title:
        raise ValueError("Inserisci il titolo della traccia.")

    artist_name = normalize_text(form_data.get("artist_name"))
    genre = normalize_text(form_data.get("genre"))
    tags = normalize_tags(form_data.get("tags", ""))

    artist_id = get_or_create_artist(
        db,
        artist_name,
    )

    genre_tag_id = get_or_create_genre_tag(
        db,
        genre,
        tags,
    )

    duration_ms = duration_to_ms(
        form_data.get("duration_minutes"),
        form_data.get("duration_seconds"),
    )

    year = normalize_optional_number(
        form_data.get("year"),
        int,
    )

    album_name = normalize_text(
        form_data.get("album_name")
    )

    album_release_date = normalize_text(
        form_data.get("album_release_date")
    )

    album_image_url = normalize_text(
        form_data.get("album_image_url")
    )

    audio_features = build_audio_features(form_data)

    now = datetime.now(timezone.utc)

    track_document = {
        "track_id": f"admin_{ObjectId()}",
        "name": title,
        "artist_id": artist_id,
        "genre_tag_id": genre_tag_id,
        "audio_features": audio_features,
        "created_by": ADMIN_CREATED_MARKER,
        "created_at": now,
        "updated_at": now,
    }

    if year is not None:
        track_document["year"] = year

    if duration_ms is not None:
        track_document["duration_ms"] = duration_ms

    if spotify_id:
        track_document["spotify_id"] = spotify_id

    if album_name:
        track_document["album_name"] = album_name

    if album_release_date:
        track_document["album_release_date"] = album_release_date

    if album_image_url:
        track_document["album_image_url"] = album_image_url

    return track_document


def create_track(
    db: Database,
    form_data,
) -> ObjectId:
    """Inserisce una nuova traccia."""
    document = build_track_document(
        db,
        form_data,
    )

    result = db.tracks.insert_one(document)

    return result.inserted_id


def update_track(
    db: Database,
    track_id: ObjectId,
    form_data,
) -> None:
    """
    Aggiorna una traccia esistente.
    """
    existing_track = db.tracks.find_one(
        {
            "_id": track_id,
        }
    )

    if not existing_track:
        raise ValueError("Traccia non trovata.")

    spotify_id = normalize_spotify_id(
        form_data.get("spotify_url")
        or form_data.get("spotify_id")
    )

    name = normalize_text(form_data.get("name"))

    if not name:
        raise ValueError("Inserisci il titolo della traccia.")

    artist_id = get_or_create_artist(
        db,
        form_data.get("artist_name"),
    )

    genre_tag_id = get_or_create_genre_tag(
        db,
        form_data.get("genre"),
        normalize_tags(form_data.get("tags", "")),
    )

    duration_ms = duration_to_ms(
        form_data.get("duration_minutes"),
        form_data.get("duration_seconds"),
    )

    year = normalize_optional_number(
        form_data.get("year"),
        int,
    )

    update_fields = {
        "name": name,
        "artist_id": artist_id,
        "genre_tag_id": genre_tag_id,
        "audio_features": build_audio_features(form_data),
        "album_name": normalize_text(form_data.get("album_name")),
        "album_release_date": normalize_text(form_data.get("album_release_date")),
        "album_image_url": normalize_text(form_data.get("album_image_url")),
        "updated_at": datetime.now(timezone.utc),
        "updated_by": ADMIN_CREATED_MARKER,
    }

    update_fields["year"] = year
    update_fields["duration_ms"] = duration_ms
    update_fields["spotify_id"] = spotify_id

    db.tracks.update_one(
        {
            "_id": track_id,
        },
        {
            "$set": update_fields,
        },
    )


def get_track_form_data(
    db: Database,
    track_id: ObjectId,
) -> dict:
    """
    Recupera una traccia già arricchita per il form di modifica.
    """
    track = db.tracks.find_one(
        {
            "_id": track_id,
        }
    )

    if not track:
        raise ValueError("Traccia non trovata.")

    artist = db.artists.find_one(
        {
            "_id": track.get("artist_id"),
        }
    )

    genre_tag = db.genres_tags.find_one(
        {
            "_id": track.get("genre_tag_id"),
        }
    )

    minutes, seconds = split_duration_ms(
        track.get("duration_ms")
    )

    audio_features = track.get("audio_features") or {}

    return {
        "_id": track["_id"],
        "name": track.get("name", ""),
        "artist_name": artist.get("name", "") if artist else "",
        "genre": genre_tag.get("genre", "") if genre_tag else "",
        "tags": ", ".join(genre_tag.get("tags", [])) if genre_tag else "",
        "year": track.get("year", ""),
        "duration_minutes": minutes,
        "duration_seconds": seconds,
        "spotify_id": track.get("spotify_id", ""),
        "album_name": track.get("album_name", ""),
        "album_release_date": track.get("album_release_date", ""),
        "album_image_url": track.get("album_image_url", ""),
        "audio_features": audio_features,
    }


def delete_track_if_safe(
    db: Database,
    track_id: ObjectId,
) -> tuple[bool, str]:
    """
    Elimina una traccia solo se non esistono ascolti collegati.
    """
    linked_history_count = db.listening_history.count_documents(
        {
            "track_id": track_id,
        }
    )

    if linked_history_count > 0:
        return (
            False,
            (
                "Non posso eliminare questa traccia perché è già collegata "
                f"a {linked_history_count} ascolti. "
                "La cronologia viene preservata per non perdere dati storici."
            ),
        )

    result = db.tracks.delete_one(
        {
            "_id": track_id,
        }
    )

    if result.deleted_count == 0:
        return False, "Traccia non trovata."

    return True, "Traccia eliminata correttamente."


def register_listening_event(
    db: Database,
    track_id_value: str,
    listener_id_value: str,
) -> tuple[bool, str]:
    """
    Collega un listener esistente a una traccia esistente.
    Gli ObjectId arrivano da input hidden valorizzati tramite autocomplete.
    """
    if not ObjectId.is_valid(track_id_value):
        return False, "Seleziona una traccia dai suggerimenti."

    if not ObjectId.is_valid(listener_id_value):
        return False, "Seleziona un listener dai suggerimenti."

    track_id = ObjectId(track_id_value)
    listener_id = ObjectId(listener_id_value)

    track = db.tracks.find_one(
        {
            "_id": track_id,
        }
    )

    if not track:
        return False, "Traccia non trovata."

    listener = db.listeners.find_one(
        {
            "_id": listener_id,
        }
    )

    if not listener:
        return False, "Listener non trovato."

    existing_history = db.listening_history.find_one(
        {
            "track_id": track["_id"],
            "listener_id": listener["_id"],
        }
    )

    if existing_history:
        return False, "Questo ascolto è già stato registrato."

    try:
        db.listening_history.insert_one(
            {
                "track_id": track["_id"],
                "listener_id": listener["_id"],
                "created_by": ADMIN_CREATED_MARKER,
                "created_at": datetime.now(timezone.utc),
            }
        )

    except DuplicateKeyError:
        return False, "Questo ascolto è già presente."

    return True, "Ascolto registrato correttamente."