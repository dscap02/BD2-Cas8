import colorsys
import json
import os
import re
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, UnidentifiedImageError
from bson import ObjectId
from flask import Flask, abort, render_template, request
from pymongo import MongoClient
from pymongo.errors import PyMongoError


MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb://localhost:27017/",
)

DB_NAME = os.getenv(
    "MONGO_DB_NAME",
    "music_archive",
)

RESULTS_PER_PAGE = 20

WEBAPP_ROOT = Path(__file__).resolve().parent

DASHBOARD_CACHE_PATH = (
    WEBAPP_ROOT
    / "data"
    / "dashboard_cache.json"
)

DEFAULT_THEME = {
    "accent": "#6c4df6",
    "accent_dark": "#5034d5",
    "text": "#ffffff",
    "muted_text": "rgba(255, 255, 255, 0.72)",
    "thumbnail_url": None,
}


app = Flask(__name__)

mongo_client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
)

db = mongo_client[DB_NAME]

http_session = requests.Session()

http_session.headers.update(
    {
        "User-Agent": "Music-Archive-NoSQL/1.0",
    }
)


def load_dashboard_cache() -> dict:
    """
    Carica le statistiche pre-calcolate della dashboard.
    """
    if not DASHBOARD_CACHE_PATH.exists():
        raise FileNotFoundError(
            "Cache dashboard non trovata. "
            "Eseguire prima: "
            "python mongodb/scripts/generate_dashboard_cache.py"
        )

    with DASHBOARD_CACHE_PATH.open(
        "r",
        encoding="utf-8",
    ) as cache_file:
        return json.load(cache_file)


def parse_object_id(value: str) -> ObjectId:
    """
    Converte una stringa in ObjectId oppure restituisce errore 404.
    """
    if not ObjectId.is_valid(value):
        abort(404)

    return ObjectId(value)


def normalize_tags(tags) -> list[str]:
    """
    Normalizza il campo tags in una lista di stringhe.
    """
    if tags is None:
        return []

    if isinstance(tags, (list, tuple)):
        return [
            str(tag).strip()
            for tag in tags
            if str(tag).strip()
        ]

    if isinstance(tags, str):
        return [
            tag.strip()
            for tag in tags.split(",")
            if tag.strip()
        ]

    return [str(tags).strip()]


def normalize_spotify_id(value) -> Optional[str]:
    """
    Estrae uno Spotify track ID da:
    - ID semplice;
    - URI spotify:track:ID;
    - URL open.spotify.com/track/ID.
    """
    if value is None:
        return None

    raw_value = str(value).strip()

    if not raw_value:
        return None

    if raw_value.startswith("spotify:track:"):
        raw_value = raw_value.rsplit(":", 1)[-1]

    if "open.spotify.com/track/" in raw_value:
        raw_value = raw_value.split(
            "open.spotify.com/track/",
            1,
        )[1]

        raw_value = raw_value.split("?", 1)[0]
        raw_value = raw_value.split("/", 1)[0]

    if re.fullmatch(r"[A-Za-z0-9]{22}", raw_value):
        return raw_value

    return None


def extract_spotify_id(track: dict) -> Optional[str]:
    """
    Cerca lo Spotify ID nelle possibili varianti del campo.
    """
    possible_fields = [
        "spotify_id",
        "spotify_track_id",
        "spotifyId",
        "spotify_uri",
        "spotify_url",
    ]

    for field_name in possible_fields:
        spotify_id = normalize_spotify_id(
            track.get(field_name)
        )

        if spotify_id:
            return spotify_id

    return None


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """
    Converte una tripla RGB in colore esadecimale.
    """
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def mix_with_black(
    rgb: tuple[int, int, int],
    amount: float = 0.32,
) -> tuple[int, int, int]:
    """
    Produce una variante più scura del colore.
    """
    return tuple(
        max(0, min(255, int(channel * (1 - amount))))
        for channel in rgb
    )


def relative_luminance(
    rgb: tuple[int, int, int],
) -> float:
    """
    Calcola la luminanza relativa approssimata del colore.
    """
    def linearize(channel: int) -> float:
        value = channel / 255

        if value <= 0.04045:
            return value / 12.92

        return ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (
        linearize(channel)
        for channel in rgb
    )

    return (
        0.2126 * red
        + 0.7152 * green
        + 0.0722 * blue
    )


def choose_text_colors(
    rgb: tuple[int, int, int],
) -> tuple[str, str]:
    """
    Sceglie automaticamente testo chiaro o scuro.
    """
    luminance = relative_luminance(rgb)

    if luminance > 0.52:
        return (
            "#18181f",
            "rgba(24, 24, 31, 0.68)",
        )

    return (
        "#ffffff",
        "rgba(255, 255, 255, 0.72)",
    )


def extract_dominant_color(
    image_content: bytes,
) -> tuple[int, int, int]:
    """
    Estrae un colore dominante dalla copertina.

    Vengono privilegiati colori frequenti e sufficientemente saturi,
    evitando per quanto possibile bianco, nero e grigi neutri.
    """
    with Image.open(BytesIO(image_content)) as image:
        image = image.convert("RGB")
        image.thumbnail((180, 180))

        quantized = image.quantize(colors=12)
        palette = quantized.getpalette()
        color_counts = quantized.getcolors()

        if not palette or not color_counts:
            return 108, 77, 246

        candidates = []

        for count, palette_index in color_counts:
            palette_position = palette_index * 3

            rgb = tuple(
                palette[
                    palette_position:
                    palette_position + 3
                ]
            )

            if len(rgb) != 3:
                continue

            red, green, blue = rgb
            maximum = max(rgb)
            minimum = min(rgb)
            brightness = sum(rgb) / 3

            saturation = (
                (maximum - minimum) / maximum
                if maximum > 0
                else 0
            )

            if brightness > 242:
                continue

            if brightness < 18:
                continue

            hue, hsv_saturation, value = colorsys.rgb_to_hsv(
                red / 255,
                green / 255,
                blue / 255,
            )

            del hue

            score = (
                count
                * (0.40 + saturation + hsv_saturation)
                * (0.65 + value)
            )

            candidates.append(
                (
                    score,
                    rgb,
                )
            )

        if not candidates:
            count, palette_index = max(
                color_counts,
                key=lambda item: item[0],
            )

            del count

            position = palette_index * 3

            return tuple(
                palette[position:position + 3]
            )

        candidates.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return candidates[0][1]


@lru_cache(maxsize=256)
def get_spotify_theme(
    spotify_id: str,
) -> dict:
    """
    Recupera la copertina tramite Spotify oEmbed ed estrae
    il colore da applicare alla navbar.

    In caso di errore viene restituito il tema viola predefinito.
    """
    if not spotify_id:
        return DEFAULT_THEME.copy()

    spotify_url = (
        f"https://open.spotify.com/track/{spotify_id}"
    )

    try:
        oembed_response = http_session.get(
            "https://open.spotify.com/oembed",
            params={
                "url": spotify_url,
            },
            timeout=6,
        )

        oembed_response.raise_for_status()

        oembed_data = oembed_response.json()
        thumbnail_url = oembed_data.get("thumbnail_url")

        if not thumbnail_url:
            return DEFAULT_THEME.copy()

        image_response = http_session.get(
            thumbnail_url,
            timeout=8,
        )

        image_response.raise_for_status()

        dominant_rgb = extract_dominant_color(
            image_response.content
        )

        dark_rgb = mix_with_black(
            dominant_rgb,
            amount=0.34,
        )

        text_color, muted_text_color = (
            choose_text_colors(dominant_rgb)
        )

        return {
            "accent": rgb_to_hex(dominant_rgb),
            "accent_dark": rgb_to_hex(dark_rgb),
            "text": text_color,
            "muted_text": muted_text_color,
            "thumbnail_url": thumbnail_url,
        }

    except (
        requests.RequestException,
        ValueError,
        KeyError,
        UnidentifiedImageError,
        OSError,
    ):
        app.logger.warning(
            "Impossibile generare il tema Spotify per %s",
            spotify_id,
        )

        return DEFAULT_THEME.copy()


def enrich_track(track: dict) -> dict:
    """
    Aggiunge durata formattata, tag e collegamenti Spotify.
    """
    duration_ms = track.get("duration_ms")

    if duration_ms is not None:
        try:
            total_seconds = int(
                float(duration_ms)
            ) // 1000

            minutes, seconds = divmod(
                total_seconds,
                60,
            )

            track["formatted_duration"] = (
                f"{minutes}:{seconds:02d}"
            )

        except (TypeError, ValueError):
            track["formatted_duration"] = None

    else:
        track["formatted_duration"] = None

    spotify_id = extract_spotify_id(track)

    track["spotify_id"] = spotify_id

    if spotify_id:
        track["spotify_app_url"] = (
            f"spotify:track:{spotify_id}"
        )

        track["spotify_web_url"] = (
            f"https://open.spotify.com/track/{spotify_id}"
        )

    else:
        track["spotify_app_url"] = None
        track["spotify_web_url"] = None

    track["tags"] = normalize_tags(
        track.get("tags")
    )

    return track


@lru_cache(maxsize=1)
def get_filter_options() -> dict:
    """
    Recupera e memorizza le opzioni dei filtri.
    """
    genres = sorted(
        genre
        for genre in db.genres_tags.distinct("genre")
        if genre
    )

    raw_tags = db.genres_tags.distinct("tags")
    tags = set()

    for value in raw_tags:
        for tag in normalize_tags(value):
            tags.add(tag)

    raw_years = db.tracks.distinct("year")
    years = set()

    for year in raw_years:
        if year is None or year == "":
            continue

        try:
            years.add(int(float(year)))

        except (TypeError, ValueError):
            continue

    return {
        "genres": genres,
        "tags": sorted(tags),
        "years": sorted(
            years,
            reverse=True,
        ),
    }


def search_tracks(
    title_query: str,
    genre: str,
    year: str,
    tag: str,
    page: int,
) -> tuple[list[dict], int]:
    """
    Cerca tracce applicando filtri combinabili.
    """
    initial_conditions = []

    if title_query:
        initial_conditions.append(
            {
                "name": {
                    "$regex": re.escape(title_query),
                    "$options": "i",
                }
            }
        )

    if year:
        initial_conditions.append(
            {
                "$expr": {
                    "$eq": [
                        {
                            "$convert": {
                                "input": "$year",
                                "to": "string",
                                "onError": "",
                                "onNull": "",
                            }
                        },
                        str(year),
                    ]
                }
            }
        )

    pipeline = []

    if initial_conditions:
        pipeline.append(
            {
                "$match": {
                    "$and": initial_conditions,
                }
            }
        )

    pipeline.extend(
        [
            {
                "$lookup": {
                    "from": "artists",
                    "localField": "artist_id",
                    "foreignField": "_id",
                    "as": "artist",
                }
            },
            {
                "$unwind": {
                    "path": "$artist",
                    "preserveNullAndEmptyArrays": True,
                }
            },
            {
                "$lookup": {
                    "from": "genres_tags",
                    "localField": "genre_tag_id",
                    "foreignField": "_id",
                    "as": "genre_tag",
                }
            },
            {
                "$unwind": {
                    "path": "$genre_tag",
                    "preserveNullAndEmptyArrays": True,
                }
            },
        ]
    )

    joined_conditions = []

    if genre:
        joined_conditions.append(
            {
                "genre_tag.genre": {
                    "$regex": (
                        f"^{re.escape(genre)}$"
                    ),
                    "$options": "i",
                }
            }
        )

    if tag:
        joined_conditions.append(
            {
                "genre_tag.tags": {
                    "$regex": re.escape(tag),
                    "$options": "i",
                }
            }
        )

    if joined_conditions:
        pipeline.append(
            {
                "$match": {
                    "$and": joined_conditions,
                }
            }
        )

    skip = (page - 1) * RESULTS_PER_PAGE

    pipeline.append(
        {
            "$facet": {
                "results": [
                    {
                        "$sort": {
                            "name": 1,
                        }
                    },
                    {
                        "$skip": skip,
                    },
                    {
                        "$limit": RESULTS_PER_PAGE,
                    },
                    {
                        "$project": {
                            "_id": 1,
                            "name": 1,
                            "year": 1,
                            "duration_ms": 1,
                            "artist_name": {
                                "$ifNull": [
                                    "$artist.name",
                                    "Artista sconosciuto",
                                ]
                            },
                            "artist_id": "$artist._id",
                            "genre": {
                                "$ifNull": [
                                    "$genre_tag.genre",
                                    "Genere sconosciuto",
                                ]
                            },
                            "tags": {
                                "$ifNull": [
                                    "$genre_tag.tags",
                                    [],
                                ]
                            },
                        }
                    },
                ],
                "metadata": [
                    {
                        "$count": "total",
                    }
                ],
            }
        }
    )

    aggregation_result = list(
        db.tracks.aggregate(
            pipeline,
            allowDiskUse=True,
        )
    )

    if not aggregation_result:
        return [], 0

    result = aggregation_result[0]
    tracks = result.get("results", [])
    metadata = result.get("metadata", [])

    total_results = (
        metadata[0]["total"]
        if metadata
        else 0
    )

    for track in tracks:
        enrich_track(track)

    return tracks, total_results


def search_artists(
    query: str,
    page: int,
) -> tuple[list[dict], int]:
    """
    Cerca artisti per nome.
    """
    search_filter = {}

    if query:
        search_filter = {
            "name": {
                "$regex": re.escape(query),
                "$options": "i",
            }
        }

    skip = (page - 1) * RESULTS_PER_PAGE

    artists = list(
        db.artists.find(
            search_filter,
            {
                "_id": 1,
                "name": 1,
            },
        )
        .sort("name", 1)
        .skip(skip)
        .limit(RESULTS_PER_PAGE)
    )

    for artist in artists:
        artist["track_count"] = (
            db.tracks.count_documents(
                {
                    "artist_id": artist["_id"],
                }
            )
        )

    total_results = db.artists.count_documents(
        search_filter
    )

    return artists, total_results


def get_track_detail(
    track_object_id: ObjectId,
) -> dict:
    """
    Recupera una traccia e i documenti collegati.
    """
    track = db.tracks.find_one(
        {
            "_id": track_object_id,
        }
    )

    if track is None:
        abort(404)

    artist = None
    genre_tag = None

    artist_id = track.get("artist_id")

    if artist_id:
        artist = db.artists.find_one(
            {
                "_id": artist_id,
            },
            {
                "_id": 1,
                "name": 1,
            },
        )

    genre_tag_id = track.get("genre_tag_id")

    if genre_tag_id:
        genre_tag = db.genres_tags.find_one(
            {
                "_id": genre_tag_id,
            }
        )

    if genre_tag:
        track["genre"] = genre_tag.get("genre")
        track["tags"] = genre_tag.get("tags")

    else:
        track["genre"] = None
        track["tags"] = []

    track["artist"] = artist

    return enrich_track(track)


def get_artist_tracks(
    artist_object_id: ObjectId,
    page: int,
) -> tuple[list[dict], int]:
    """
    Recupera le tracce associate a un artista.
    """
    skip = (page - 1) * RESULTS_PER_PAGE

    pipeline = [
        {
            "$match": {
                "artist_id": artist_object_id,
            }
        },
        {
            "$lookup": {
                "from": "genres_tags",
                "localField": "genre_tag_id",
                "foreignField": "_id",
                "as": "genre_tag",
            }
        },
        {
            "$unwind": {
                "path": "$genre_tag",
                "preserveNullAndEmptyArrays": True,
            }
        },
        {
            "$sort": {
                "year": -1,
                "name": 1,
            }
        },
        {
            "$skip": skip,
        },
        {
            "$limit": RESULTS_PER_PAGE,
        },
        {
            "$project": {
                "_id": 1,
                "name": 1,
                "year": 1,
                "duration_ms": 1,
                "genre": "$genre_tag.genre",
                "tags": "$genre_tag.tags",
            }
        },
    ]

    tracks = list(
        db.tracks.aggregate(
            pipeline,
            allowDiskUse=True,
        )
    )

    for track in tracks:
        enrich_track(track)

    total_results = db.tracks.count_documents(
        {
            "artist_id": artist_object_id,
        }
    )

    return tracks, total_results


@app.route("/")
def index():
    error = None

    try:
        dashboard_data = load_dashboard_cache()

        counts = dashboard_data.get("counts", {})
        top_tracks = dashboard_data.get("top_tracks", [])
        top_artists = dashboard_data.get("top_artists", [])
        top_genres = dashboard_data.get("top_genres", [])
        top_listeners = dashboard_data.get("top_listeners", [])
        generated_at = dashboard_data.get("generated_at")

    except (OSError, json.JSONDecodeError) as error_detail:
        app.logger.exception(
            "Errore durante il caricamento della cache"
        )

        counts = {}
        top_tracks = []
        top_artists = []
        top_genres = []
        top_listeners = []
        generated_at = None
        error = str(error_detail)

    return render_template(
        "index.html",
        counts=counts,
        top_tracks=top_tracks,
        top_artists=top_artists,
        top_genres=top_genres,
        top_listeners=top_listeners,
        generated_at=generated_at,
        error=error,
        page_theme=None,
    )


@app.route("/tracks")
def tracks():
    title_query = request.args.get(
        "q",
        "",
    ).strip()

    genre = request.args.get(
        "genre",
        "",
    ).strip()

    year = request.args.get(
        "year",
        "",
    ).strip()

    tag = request.args.get(
        "tag",
        "",
    ).strip()

    page = max(
        request.args.get(
            "page",
            default=1,
            type=int,
        ),
        1,
    )

    results = []
    total_results = 0
    error = None

    has_filters = any(
        [
            title_query,
            genre,
            year,
            tag,
        ]
    )

    try:
        filter_options = get_filter_options()

        if has_filters:
            results, total_results = search_tracks(
                title_query=title_query,
                genre=genre,
                year=year,
                tag=tag,
                page=page,
            )

    except PyMongoError as error_detail:
        app.logger.exception(
            "Errore durante la ricerca delle tracce"
        )

        filter_options = {
            "genres": [],
            "tags": [],
            "years": [],
        }

        error = str(error_detail)

    has_previous = page > 1
    has_next = (
        page * RESULTS_PER_PAGE
        < total_results
    )

    return render_template(
        "tracks.html",
        query=title_query,
        selected_genre=genre,
        selected_year=year,
        selected_tag=tag,
        filter_options=filter_options,
        tracks=results,
        page=page,
        total_results=total_results,
        has_filters=has_filters,
        has_previous=has_previous,
        has_next=has_next,
        error=error,
        page_theme=None,
    )


@app.route("/tracks/<track_id>")
def track_detail(track_id):
    try:
        track_object_id = parse_object_id(track_id)
        track = get_track_detail(track_object_id)

        page_theme = (
            get_spotify_theme(track["spotify_id"])
            if track.get("spotify_id")
            else DEFAULT_THEME.copy()
        )

    except PyMongoError as error_detail:
        app.logger.exception(
            "Errore durante il caricamento della traccia"
        )

        return render_template(
            "track_detail.html",
            track=None,
            error=str(error_detail),
            page_theme=None,
        )

    return render_template(
        "track_detail.html",
        track=track,
        error=None,
        page_theme=page_theme,
    )


@app.route("/artists")
def artists():
    query = request.args.get(
        "q",
        "",
    ).strip()

    page = max(
        request.args.get(
            "page",
            default=1,
            type=int,
        ),
        1,
    )

    results = []
    total_results = 0
    error = None

    if query:
        try:
            results, total_results = search_artists(
                query,
                page,
            )

        except PyMongoError as error_detail:
            app.logger.exception(
                "Errore durante la ricerca degli artisti"
            )

            error = str(error_detail)

    has_previous = page > 1
    has_next = (
        page * RESULTS_PER_PAGE
        < total_results
    )

    return render_template(
        "artists.html",
        query=query,
        artists=results,
        page=page,
        total_results=total_results,
        has_previous=has_previous,
        has_next=has_next,
        error=error,
        page_theme=None,
    )


@app.route("/artists/<artist_id>")
def artist_detail(artist_id):
    artist_object_id = parse_object_id(
        artist_id
    )

    artist = db.artists.find_one(
        {
            "_id": artist_object_id,
        },
        {
            "_id": 1,
            "name": 1,
        },
    )

    if artist is None:
        abort(404)

    page = max(
        request.args.get(
            "page",
            default=1,
            type=int,
        ),
        1,
    )

    tracks_result, total_results = (
        get_artist_tracks(
            artist_object_id,
            page,
        )
    )

    has_previous = page > 1
    has_next = (
        page * RESULTS_PER_PAGE
        < total_results
    )

    return render_template(
        "artist_detail.html",
        artist=artist,
        tracks=tracks_result,
        total_results=total_results,
        page=page,
        has_previous=has_previous,
        has_next=has_next,
        page_theme=None,
    )


@app.template_filter("format_number")
def format_number(value):
    try:
        return f"{int(value):,}".replace(
            ",",
            ".",
        )

    except (TypeError, ValueError):
        return value


@app.template_filter("format_datetime")
def format_datetime(value):
    if not value:
        return ""

    return (
        value.replace("T", " ")
        .replace("+00:00", " UTC")
    )


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )