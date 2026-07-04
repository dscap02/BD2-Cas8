import json
import os
import re
from functools import lru_cache
from pathlib import Path

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


app = Flask(__name__)

mongo_client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000,
)

db = mongo_client[DB_NAME]


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


def normalize_tags(tags) -> list:
    """
    Normalizza il campo tags in una lista.

    Gestisce:
    - liste MongoDB;
    - tuple;
    - stringhe separate da virgola;
    - valori assenti.
    """
    if tags is None:
        return []

    if isinstance(tags, list):
        return [
            str(tag).strip()
            for tag in tags
            if str(tag).strip()
        ]

    if isinstance(tags, tuple):
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

    return [str(tags)]


def extract_spotify_id(track: dict):
    """
    Recupera lo Spotify ID da possibili varianti del nome del campo.
    """
    possible_fields = [
        "spotify_id",
        "spotify_track_id",
        "spotifyId",
    ]

    for field_name in possible_fields:
        value = track.get(field_name)

        if value:
            return str(value).strip()

    return None


def enrich_track(track: dict) -> dict:
    """
    Aggiunge dati utili alla visualizzazione della traccia.
    """
    duration_ms = track.get("duration_ms")

    if duration_ms is not None:
        try:
            total_seconds = int(float(duration_ms)) // 1000
            minutes, seconds = divmod(total_seconds, 60)
            track["formatted_duration"] = f"{minutes}:{seconds:02d}"
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

    track["tags"] = normalize_tags(track.get("tags"))

    return track


@lru_cache(maxsize=1)
def get_filter_options() -> dict:
    """
    Recupera le opzioni disponibili per i filtri.

    Il risultato viene mantenuto in memoria per evitare di rileggere
    le collection a ogni richiesta.
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
        "years": sorted(years, reverse=True),
    }


def search_tracks(
    title_query: str,
    genre: str,
    year: str,
    tag: str,
    page: int,
) -> tuple[list[dict], int]:
    """
    Cerca le tracce applicando filtri combinabili.
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
        artist["track_count"] = db.tracks.count_documents(
            {
                "artist_id": artist["_id"],
            }
        )

    total_results = db.artists.count_documents(
        search_filter
    )

    return artists, total_results


def get_track_detail(track_object_id: ObjectId):
    """
    Recupera la traccia e i documenti collegati.
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
    """
    Mostra la dashboard tramite dati pre-calcolati.
    """
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
    )


@app.route("/tracks")
def tracks():
    """
    Ricerca tracce con filtri combinabili.
    """
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
    has_next = page * RESULTS_PER_PAGE < total_results

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
    )


@app.route("/tracks/<track_id>")
def track_detail(track_id):
    """
    Mostra il dettaglio di una traccia.
    """
    try:
        track_object_id = parse_object_id(track_id)
        track = get_track_detail(track_object_id)

    except PyMongoError as error_detail:
        app.logger.exception(
            "Errore durante il caricamento della traccia"
        )

        return render_template(
            "track_detail.html",
            track=None,
            error=str(error_detail),
        )

    return render_template(
        "track_detail.html",
        track=track,
        error=None,
    )


@app.route("/artists")
def artists():
    """
    Ricerca artisti.
    """
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
    has_next = page * RESULTS_PER_PAGE < total_results

    return render_template(
        "artists.html",
        query=query,
        artists=results,
        page=page,
        total_results=total_results,
        has_previous=has_previous,
        has_next=has_next,
        error=error,
    )


@app.route("/artists/<artist_id>")
def artist_detail(artist_id):
    """
    Mostra il dettaglio dell'artista e le tracce associate.
    """
    artist_object_id = parse_object_id(artist_id)

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

    tracks_result, total_results = get_artist_tracks(
        artist_object_id,
        page,
    )

    has_previous = page > 1
    has_next = page * RESULTS_PER_PAGE < total_results

    return render_template(
        "artist_detail.html",
        artist=artist,
        tracks=tracks_result,
        total_results=total_results,
        page=page,
        has_previous=has_previous,
        has_next=has_next,
    )


@app.template_filter("format_number")
def format_number(value):
    """
    Formatta i numeri con separatore delle migliaia.
    """
    try:
        return f"{int(value):,}".replace(",", ".")
    except (TypeError, ValueError):
        return value


@app.template_filter("format_datetime")
def format_datetime(value):
    """
    Rende leggibile una data ISO.
    """
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