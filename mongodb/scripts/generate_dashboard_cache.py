import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient


MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "music_archive"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_PATH = PROJECT_ROOT / "mongodb" / "webapp" / "data" / "dashboard_cache.json"


def serialize_value(value):
    if isinstance(value, dict):
        return {
            str(key): serialize_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [serialize_value(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


def get_database():
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
    )
    client.admin.command("ping")
    return client[DB_NAME]


def get_collection_counts(db):
    return {
        "artists": db.artists.count_documents({}),
        "genres_tags": db.genres_tags.count_documents({}),
        "tracks": db.tracks.count_documents({}),
        "listeners": db.listeners.count_documents({}),
        "listening_history": db.listening_history.count_documents({}),
    }


def get_top_tracks(db, limit=10):
    pipeline = [
        {
            "$group": {
                "_id": "$track_id",
                "listen_count": {"$sum": 1},
            }
        },
        {"$sort": {"listen_count": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "tracks",
                "localField": "_id",
                "foreignField": "_id",
                "as": "track",
            }
        },
        {"$unwind": "$track"},
        {
            "$lookup": {
                "from": "artists",
                "localField": "track.artist_id",
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
            "$project": {
                "_id": 0,
                "track_name": "$track.name",
                "artist_name": {
                    "$ifNull": [
                        "$artist.name",
                        "Artista sconosciuto",
                    ]
                },
                "listen_count": 1,
            }
        },
    ]

    return list(
        db.listening_history.aggregate(
            pipeline,
            allowDiskUse=True,
        )
    )


def get_top_artists(db, limit=10):
    pipeline = [
        {
            "$lookup": {
                "from": "tracks",
                "localField": "track_id",
                "foreignField": "_id",
                "as": "track",
            }
        },
        {"$unwind": "$track"},
        {
            "$group": {
                "_id": "$track.artist_id",
                "listen_count": {"$sum": 1},
            }
        },
        {"$sort": {"listen_count": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "artists",
                "localField": "_id",
                "foreignField": "_id",
                "as": "artist",
            }
        },
        {"$unwind": "$artist"},
        {
            "$project": {
                "_id": 0,
                "artist_name": "$artist.name",
                "listen_count": 1,
            }
        },
    ]

    return list(
        db.listening_history.aggregate(
            pipeline,
            allowDiskUse=True,
        )
    )


def get_top_genres(db, limit=10):
    pipeline = [
        {
            "$lookup": {
                "from": "tracks",
                "localField": "track_id",
                "foreignField": "_id",
                "as": "track",
            }
        },
        {"$unwind": "$track"},
        {
            "$lookup": {
                "from": "genres_tags",
                "localField": "track.genre_tag_id",
                "foreignField": "_id",
                "as": "genre_tag",
            }
        },
        {"$unwind": "$genre_tag"},
        {
            "$group": {
                "_id": "$genre_tag.genre",
                "listen_count": {"$sum": 1},
            }
        },
        {"$sort": {"listen_count": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "genre": "$_id",
                "listen_count": 1,
            }
        },
    ]

    return list(
        db.listening_history.aggregate(
            pipeline,
            allowDiskUse=True,
        )
    )


def get_top_listeners(db, limit=10):
    pipeline = [
        {
            "$group": {
                "_id": "$listener_id",
                "listen_count": {"$sum": 1},
            }
        },
        {"$sort": {"listen_count": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "listeners",
                "localField": "_id",
                "foreignField": "_id",
                "as": "listener",
            }
        },
        {"$unwind": "$listener"},
        {
            "$project": {
                "_id": 0,
                "listener_id": "$listener.original_user_id",
                "listen_count": 1,
            }
        },
    ]

    return list(
        db.listening_history.aggregate(
            pipeline,
            allowDiskUse=True,
        )
    )


def main():
    db = get_database()

    print("Generazione cache dashboard in corso...")

    cache = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": get_collection_counts(db),
        "top_tracks": get_top_tracks(db),
        "top_artists": get_top_artists(db),
        "top_genres": get_top_genres(db),
        "top_listeners": get_top_listeners(db),
    }

    CACHE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with CACHE_PATH.open(
        "w",
        encoding="utf-8",
    ) as cache_file:
        json.dump(
            serialize_value(cache),
            cache_file,
            indent=2,
            ensure_ascii=False,
        )

    print(f"Cache salvata in: {CACHE_PATH}")


if __name__ == "__main__":
    main()