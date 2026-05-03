import argparse
import os
from pathlib import Path
from typing import Any

import pandas as pd
from bson import ObjectId
from pymongo import MongoClient, ASCENDING


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_MONGO_URI = "mongodb://localhost:27017/"
DEFAULT_DB_NAME = "music_archive"

DEFAULT_MUSIC_INFO_PATH = PROJECT_ROOT / "dataset" / "music_info_cleaned.csv"
DEFAULT_LISTENING_HISTORY_PATH = PROJECT_ROOT / "dataset" / "listening_history_cleaned.csv"

AUDIO_FEATURE_COLUMNS = [
    "danceability",
    "energy",
    "key",
    "loudness",
    "mode",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "time_signature",
]


def clean_value(value: Any) -> Any:
    """
    Converte NaN pandas in None per evitare valori non validi nei documenti MongoDB.
    """
    if pd.isna(value):
        return None
    return value


def parse_tags(tags_value: Any) -> list[str]:
    """
    Converte il campo tags del CSV in una lista di stringhe.
    """
    if pd.isna(tags_value):
        return []

    return [
        tag.strip()
        for tag in str(tags_value).split(",")
        if tag.strip()
    ]


def build_audio_features(row: pd.Series) -> dict[str, Any]:
    """
    Costruisce l'oggetto embedded audio_features a partire dalle colonne audio del dataset.
    """
    return {
        column: clean_value(row[column])
        for column in AUDIO_FEATURE_COLUMNS
    }


def load_datasets(music_info_path: str, listening_history_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Carica i dataset preprocessati.
    """
    music_df = pd.read_csv(music_info_path)
    listening_df = pd.read_csv(listening_history_path)

    return music_df, listening_df


def create_indexes(db) -> None:
    """
    Crea gli indici principali per evitare duplicati logici e facilitare le query.
    """
    db.artists.create_index([("name", ASCENDING)], unique=True)

    db.genres_tags.create_index(
        [
            ("genre", ASCENDING),
            ("tags_key", ASCENDING),
        ],
        unique=True,
    )

    db.tracks.create_index([("track_id", ASCENDING)], unique=True)
    db.tracks.create_index([("artist_id", ASCENDING)])
    db.tracks.create_index([("genre_tag_id", ASCENDING)])

    db.listeners.create_index([("original_user_id", ASCENDING)], unique=True)

    db.listening_history.create_index(
        [
            ("listener_id", ASCENDING),
            ("track_id", ASCENDING),
        ],
        unique=True,
    )
    db.listening_history.create_index([("track_id", ASCENDING)])


def reset_database(db) -> None:
    """
    Elimina le collection gestite dallo script.
    """
    collections = [
        "artists",
        "genres_tags",
        "tracks",
        "listeners",
        "listening_history",
    ]

    for collection in collections:
        db[collection].drop()


def ingest_artists(db, music_df: pd.DataFrame) -> dict[str, ObjectId]:
    """
    Inserisce gli artisti unici nella collection artists.
    Restituisce una mappa artist_name -> ObjectId.
    """
    artist_names = (
        music_df["artist"]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    artist_map: dict[str, ObjectId] = {}

    documents = []
    for artist_name in artist_names:
        artist_id = ObjectId()
        artist_map[artist_name] = artist_id

        documents.append({
            "_id": artist_id,
            "name": artist_name,
        })

    if documents:
        db.artists.insert_many(documents)

    return artist_map


def make_genre_tag_key(genre: Any, tags: list[str]) -> tuple[str, tuple[str, ...]]:
    """
    Crea una chiave logica stabile per identificare una combinazione genre + tags.
    """
    genre_value = str(genre).strip() if not pd.isna(genre) else "Unknown"
    tags_tuple = tuple(tags)

    return genre_value, tags_tuple


def ingest_genres_tags(db, music_df: pd.DataFrame) -> dict[tuple[str, tuple[str, ...]], ObjectId]:
    """
    Inserisce le combinazioni uniche genre + tags nella collection genres_tags.
    Restituisce una mappa (genre, tags_tuple) -> ObjectId.
    """
    genre_tag_map: dict[tuple[str, tuple[str, ...]], ObjectId] = {}
    documents = []

    for _, row in music_df.iterrows():
        tags = parse_tags(row["tags"])
        key = make_genre_tag_key(row["genre"], tags)

        if key not in genre_tag_map:
            genre_tag_id = ObjectId()
            genre_tag_map[key] = genre_tag_id

            genre, tags_tuple = key

            documents.append({
                "_id": genre_tag_id,
                "genre": genre,
                "tags": list(tags_tuple),
                "tags_key": "|".join(tags_tuple),
            })

    if documents:
        db.genres_tags.insert_many(documents)

    return genre_tag_map


def ingest_tracks(
    db,
    music_df: pd.DataFrame,
    artist_map: dict[str, ObjectId],
    genre_tag_map: dict[tuple[str, tuple[str, ...]], ObjectId],
) -> dict[str, ObjectId]:
    """
    Inserisce le tracce nella collection tracks.
    Restituisce una mappa original_track_id -> ObjectId MongoDB.
    """
    track_map: dict[str, ObjectId] = {}
    documents = []

    for _, row in music_df.iterrows():
        track_id_original = row["track_id"]
        artist_name = row["artist"]

        tags = parse_tags(row["tags"])
        genre_tag_key = make_genre_tag_key(row["genre"], tags)

        track_object_id = ObjectId()
        track_map[track_id_original] = track_object_id

        document = {
            "_id": track_object_id,
            "track_id": clean_value(row["track_id"]),
            "name": clean_value(row["name"]),
            "artist_id": artist_map.get(artist_name),
            "genre_tag_id": genre_tag_map.get(genre_tag_key),
            "spotify_id": clean_value(row["spotify_id"]),
            "year": clean_value(row["year"]),
            "duration_ms": clean_value(row["duration_ms"]),
            "has_audio_features": bool(row["has_audio_features"]),
            "audio_features": build_audio_features(row),
        }

        documents.append(document)

    if documents:
        db.tracks.insert_many(documents)

    return track_map


def ingest_listeners(db, listening_df: pd.DataFrame) -> dict[str, ObjectId]:
    """
    Inserisce i listener unici nella collection listeners.
    Restituisce una mappa original_user_id -> ObjectId.
    """
    user_ids = (
        listening_df["user_id"]
        .dropna()
        .drop_duplicates()
        .sort_values()
        .tolist()
    )

    listener_map: dict[str, ObjectId] = {}
    documents = []

    for user_id in user_ids:
        listener_id = ObjectId()
        listener_map[user_id] = listener_id

        documents.append({
            "_id": listener_id,
            "original_user_id": user_id,
        })

    if documents:
        db.listeners.insert_many(documents)

    return listener_map


def ingest_listening_history(
    db,
    listening_df: pd.DataFrame,
    listener_map: dict[str, ObjectId],
    track_map: dict[str, ObjectId],
) -> int:
    """
    Inserisce la cronologia degli ascolti nella collection listening_history.
    I record con user_id o track_id non mappabili vengono ignorati.
    """
    documents = []
    skipped_records = 0

    for _, row in listening_df.iterrows():
        original_user_id = row["user_id"]
        original_track_id = row["track_id"]

        listener_id = listener_map.get(original_user_id)
        track_id = track_map.get(original_track_id)

        if listener_id is None or track_id is None:
            skipped_records += 1
            continue

        documents.append({
            "_id": ObjectId(),
            "listener_id": listener_id,
            "track_id": track_id,
            "playcount": int(row["playcount"]),
        })

    if documents:
        db.listening_history.insert_many(documents)

    return skipped_records


def print_collection_counts(db) -> None:
    """
    Stampa il numero finale di documenti inseriti per ogni collection.
    """
    print("\nIngestion completed.")
    print("--------------------")
    print(f"artists:            {db.artists.count_documents({})}")
    print(f"genres_tags:        {db.genres_tags.count_documents({})}")
    print(f"tracks:             {db.tracks.count_documents({})}")
    print(f"listeners:          {db.listeners.count_documents({})}")
    print(f"listening_history:  {db.listening_history.count_documents({})}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest preprocessed Music Archive datasets into MongoDB."
    )

    parser.add_argument(
        "--music-info",
        default=DEFAULT_MUSIC_INFO_PATH,
        help="Path to music_info_cleaned.csv",
    )

    parser.add_argument(
        "--listening-history",
        default=DEFAULT_LISTENING_HISTORY_PATH,
        help="Path to preprocessed listening_history CSV",
    )

    parser.add_argument(
        "--mongo-uri",
        default=os.getenv("MONGO_URI", DEFAULT_MONGO_URI),
        help="MongoDB connection URI",
    )

    parser.add_argument(
        "--db-name",
        default=os.getenv("MONGO_DB_NAME", DEFAULT_DB_NAME),
        help="MongoDB database name",
    )

    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing project collections before ingestion",
    )

    args = parser.parse_args()

    print("Loading datasets...")
    music_df, listening_df = load_datasets(
        args.music_info,
        args.listening_history,
    )

    print(f"music_info rows: {len(music_df)}")
    print(f"listening_history rows: {len(listening_df)}")

    client = MongoClient(args.mongo_uri)
    db = client[args.db_name]

    if args.drop:
        print("Dropping existing collections...")
        reset_database(db)

    print("Creating indexes...")
    create_indexes(db)

    print("Ingesting artists...")
    artist_map = ingest_artists(db, music_df)

    print("Ingesting genres/tags...")
    genre_tag_map = ingest_genres_tags(db, music_df)

    print("Ingesting tracks...")
    track_map = ingest_tracks(db, music_df, artist_map, genre_tag_map)

    print("Ingesting listeners...")
    listener_map = ingest_listeners(db, listening_df)

    print("Ingesting listening history...")
    skipped_records = ingest_listening_history(
        db,
        listening_df,
        listener_map,
        track_map,
    )

    print_collection_counts(db)

    if skipped_records > 0:
        print(f"\nSkipped listening_history records: {skipped_records}")

    client.close()


if __name__ == "__main__":
    main()