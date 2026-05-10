from datetime import datetime, timezone
from pymongo import MongoClient


MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "music_archive"

TEST_MARKER = "crud_test"


def get_database():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]


def cleanup_test_documents(db):
    """
    Rimuove solo i documenti di test creati dallo script CRUD.
    Non modifica documenti reali del dataset.
    """
    db.tracks.delete_many({"test_marker": TEST_MARKER})
    db.artists.delete_many({"test_marker": TEST_MARKER})
    db.listeners.delete_many({"test_marker": TEST_MARKER})
    db.genres_tags.delete_many({"test_marker": TEST_MARKER})


def read_existing_documents(db):
    """
    Lettura non distruttiva di documenti reali già presenti nel database.
    """
    print("\nREAD - Documenti esistenti")

    artist = db.artists.find_one()
    genre = db.genres_tags.find_one()
    track = db.tracks.find_one()
    listener = db.listeners.find_one()
    history = db.listening_history.find_one()

    print("Artist trovato:", artist["_id"] if artist else "Nessun documento")
    print("Genre/tag trovato:", genre["_id"] if genre else "Nessun documento")
    print("Track trovata:", track["_id"] if track else "Nessun documento")
    print("Listener trovato:", listener["_id"] if listener else "Nessun documento")
    print("Listening history trovata:", history["_id"] if history else "Nessun documento")


def create_test_documents(db):
    """
    Inserisce documenti di test riconoscibili nelle collection principali.
    """
    print("\nCREATE - Inserimento documenti di test")

    now = datetime.now(timezone.utc)

    artist_doc = {
        "name": "CRUD Test Artist",
        "test_marker": TEST_MARKER,
        "created_at": now,
    }

    genre_doc = {
        "genre": "CRUD Test Genre",
        "tags": ["crud", "test"],
        "test_marker": TEST_MARKER,
        "created_at": now,
    }

    listener_doc = {
        "user_id": "CRUD_TEST_LISTENER",
        "display_name": "CRUD Test Listener",
        "test_marker": TEST_MARKER,
        "created_at": now,
    }

    artist_id = db.artists.insert_one(artist_doc).inserted_id
    genre_id = db.genres_tags.insert_one(genre_doc).inserted_id
    listener_id = db.listeners.insert_one(listener_doc).inserted_id

    track_doc = {
        "track_id": "CRUD_TEST_TRACK",
        "name": "CRUD Test Track",
        "artist_id": artist_id,
        "genre_tag_id": genre_id,
        "duration_ms": 180000,
        "audio_features": {
            "danceability": 0.5,
            "energy": 0.5,
            "tempo": 120.0,
        },
        "test_marker": TEST_MARKER,
        "created_at": now,
    }

    track_id = db.tracks.insert_one(track_doc).inserted_id

    print("Artist di test inserito:", artist_id)
    print("Genre/tag di test inserito:", genre_id)
    print("Listener di test inserito:", listener_id)
    print("Track di test inserita:", track_id)

    return {
        "artist_id": artist_id,
        "genre_id": genre_id,
        "listener_id": listener_id,
        "track_id": track_id,
    }


def read_test_documents(db):
    """
    Legge i documenti di test creati dallo script.
    La ricerca avviene tramite test_marker, così funziona anche dopo gli update.
    """
    print("\nREAD - Lettura documenti di test")

    test_artist = db.artists.find_one({"test_marker": TEST_MARKER})
    test_genre = db.genres_tags.find_one({"test_marker": TEST_MARKER})
    test_listener = db.listeners.find_one({"test_marker": TEST_MARKER})
    test_track = db.tracks.find_one({"test_marker": TEST_MARKER})

    print("Artist di test:", test_artist)
    print("Genre/tag di test:", test_genre)
    print("Listener di test:", test_listener)
    print("Track di test:", test_track)


def update_test_documents(db):
    """
    Aggiorna solo documenti di test.
    """
    print("\nUPDATE - Aggiornamento documenti di test")

    now = datetime.now(timezone.utc)

    artist_result = db.artists.update_one(
        {"name": "CRUD Test Artist", "test_marker": TEST_MARKER},
        {"$set": {"name": "CRUD Test Artist Updated", "updated_at": now}},
    )

    genre_result = db.genres_tags.update_one(
        {"genre": "CRUD Test Genre", "test_marker": TEST_MARKER},
        {"$set": {"tags": ["crud", "test", "updated"], "updated_at": now}},
    )

    listener_result = db.listeners.update_one(
        {"user_id": "CRUD_TEST_LISTENER", "test_marker": TEST_MARKER},
        {"$set": {"display_name": "CRUD Test Listener Updated", "updated_at": now}},
    )

    track_result = db.tracks.update_one(
        {"track_id": "CRUD_TEST_TRACK", "test_marker": TEST_MARKER},
        {"$set": {"name": "CRUD Test Track Updated", "updated_at": now}},
    )

    print("Artist aggiornati:", artist_result.modified_count)
    print("Genre/tag aggiornati:", genre_result.modified_count)
    print("Listener aggiornati:", listener_result.modified_count)
    print("Track aggiornate:", track_result.modified_count)


def delete_test_documents(db):
    """
    Cancella solo i documenti di test creati dallo script.
    """
    print("\nDELETE - Rimozione documenti di test")

    track_result = db.tracks.delete_many({"test_marker": TEST_MARKER})
    artist_result = db.artists.delete_many({"test_marker": TEST_MARKER})
    listener_result = db.listeners.delete_many({"test_marker": TEST_MARKER})
    genre_result = db.genres_tags.delete_many({"test_marker": TEST_MARKER})

    print("Track di test rimosse:", track_result.deleted_count)
    print("Artist di test rimossi:", artist_result.deleted_count)
    print("Listener di test rimossi:", listener_result.deleted_count)
    print("Genre/tag di test rimossi:", genre_result.deleted_count)


def verify_cleanup(db):
    """
    Verifica finale: nessun documento di test deve restare nel database.
    """
    print("\nCHECK FINALE - Verifica rimozione documenti di test")

    remaining_tracks = db.tracks.count_documents({"test_marker": TEST_MARKER})
    remaining_artists = db.artists.count_documents({"test_marker": TEST_MARKER})
    remaining_listeners = db.listeners.count_documents({"test_marker": TEST_MARKER})
    remaining_genres = db.genres_tags.count_documents({"test_marker": TEST_MARKER})

    print("Track di test residue:", remaining_tracks)
    print("Artist di test residui:", remaining_artists)
    print("Listener di test residui:", remaining_listeners)
    print("Genre/tag di test residui:", remaining_genres)

    if any([remaining_tracks, remaining_artists, remaining_listeners, remaining_genres]):
        raise RuntimeError("Cleanup incompleto: sono ancora presenti documenti di test.")

    print("Cleanup completato correttamente.")


def main():
    db = get_database()

    print("Avvio esempi CRUD su database:", DB_NAME)

    cleanup_test_documents(db)

    read_existing_documents(db)

    create_test_documents(db)
    read_test_documents(db)
    update_test_documents(db)
    read_test_documents(db)
    delete_test_documents(db)
    verify_cleanup(db)

    print("\nOperazioni CRUD completate senza modifiche distruttive ai dati reali.")


if __name__ == "__main__":
    main()