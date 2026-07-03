from pymongo import MongoClient


MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "music_archive"


def get_database():
    client = MongoClient(MONGO_URI)
    return client[DB_NAME]


def print_results(title, results):
    print(f"\n{title}")
    print("-" * len(title))

    results = list(results)

    if not results:
        print("Nessun risultato trovato.")
        return

    for index, item in enumerate(results, start=1):
        print(f"{index}. {item}")


def top_tracks(db, limit=10):
    pipeline = [
        {
            "$group": {
                "_id": "$track_id",
                "listen_count": {"$sum": 1}
            }
        },
        {
            "$lookup": {
                "from": "tracks",
                "localField": "_id",
                "foreignField": "_id",
                "as": "track"
            }
        },
        {"$unwind": "$track"},
        {
            "$project": {
                "_id": 0,
                "track_id": "$_id",
                "track_name": "$track.name",
                "listen_count": 1
            }
        },
        {"$sort": {"listen_count": -1}},
        {"$limit": limit}
    ]

    return db.listening_history.aggregate(pipeline)


def top_artists(db, limit=10):
    pipeline = [
        {
            "$lookup": {
                "from": "tracks",
                "localField": "track_id",
                "foreignField": "_id",
                "as": "track"
            }
        },
        {"$unwind": "$track"},
        {
            "$lookup": {
                "from": "artists",
                "localField": "track.artist_id",
                "foreignField": "_id",
                "as": "artist"
            }
        },
        {"$unwind": "$artist"},
        {
            "$group": {
                "_id": "$artist._id",
                "artist_name": {"$first": "$artist.name"},
                "listen_count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "artist_name": 1,
                "listen_count": 1
            }
        },
        {"$sort": {"listen_count": -1}},
        {"$limit": limit}
    ]

    return db.listening_history.aggregate(pipeline)


def top_genres(db, limit=10):
    pipeline = [
        {
            "$lookup": {
                "from": "tracks",
                "localField": "track_id",
                "foreignField": "_id",
                "as": "track"
            }
        },
        {"$unwind": "$track"},
        {
            "$lookup": {
                "from": "genres_tags",
                "localField": "track.genre_tag_id",
                "foreignField": "_id",
                "as": "genre_tag"
            }
        },
        {"$unwind": "$genre_tag"},
        {
            "$group": {
                "_id": "$genre_tag._id",
                "genre": {"$first": "$genre_tag.genre"},
                "listen_count": {"$sum": 1}
            }
        },
        {
            "$project": {
                "_id": 0,
                "genre": 1,
                "listen_count": 1
            }
        },
        {"$sort": {"listen_count": -1}},
        {"$limit": limit}
    ]

    return db.listening_history.aggregate(pipeline)


def most_active_listeners(db, limit=10):
    pipeline = [
        {
            "$group": {
                "_id": "$listener_id",
                "listen_count": {"$sum": 1}
            }
        },
        {
            "$lookup": {
                "from": "listeners",
                "localField": "_id",
                "foreignField": "_id",
                "as": "listener"
            }
        },
        {"$unwind": "$listener"},
        {
            "$project": {
                "_id": 0,
                "listener_id": "$listener.user_id",
                "listen_count": 1
            }
        },
        {"$sort": {"listen_count": -1}},
        {"$limit": limit}
    ]

    return db.listening_history.aggregate(pipeline)


def listening_distribution_by_genre(db):
    pipeline = [
        {
            "$lookup": {
                "from": "tracks",
                "localField": "track_id",
                "foreignField": "_id",
                "as": "track"
            }
        },
        {"$unwind": "$track"},
        {
            "$lookup": {
                "from": "genres_tags",
                "localField": "track.genre_tag_id",
                "foreignField": "_id",
                "as": "genre_tag"
            }
        },
        {"$unwind": "$genre_tag"},
        {
            "$group": {
                "_id": "$genre_tag.genre",
                "listen_count": {"$sum": 1}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_listens": {"$sum": "$listen_count"},
                "genres": {
                    "$push": {
                        "genre": "$_id",
                        "listen_count": "$listen_count"
                    }
                }
            }
        },
        {"$unwind": "$genres"},
        {
            "$project": {
                "_id": 0,
                "genre": "$genres.genre",
                "listen_count": "$genres.listen_count",
                "percentage": {
                    "$round": [
                        {
                            "$multiply": [
                                {
                                    "$divide": [
                                        "$genres.listen_count",
                                        "$total_listens"
                                    ]
                                },
                                100
                            ]
                        },
                        2
                    ]
                }
            }
        },
        {"$sort": {"listen_count": -1}}
    ]

    return db.listening_history.aggregate(pipeline)


def database_summary(db):
    summary = [
        {
            "collection": "artists",
            "documents": db.artists.count_documents({})
        },
        {
            "collection": "genres_tags",
            "documents": db.genres_tags.count_documents({})
        },
        {
            "collection": "tracks",
            "documents": db.tracks.count_documents({})
        },
        {
            "collection": "listeners",
            "documents": db.listeners.count_documents({})
        },
        {
            "collection": "listening_history",
            "documents": db.listening_history.count_documents({})
        }
    ]

    return summary


def main():
    db = get_database()

    print("Avvio aggregation queries su database:", DB_NAME)

    print_results(
        "Riepilogo collection",
        database_summary(db)
    )

    print_results(
        "Top tracce più ascoltate",
        top_tracks(db)
    )

    print_results(
        "Top artisti più ascoltati",
        top_artists(db)
    )

    print_results(
        "Top generi più ascoltati",
        top_genres(db)
    )

    print_results(
        "Listener più attivi",
        most_active_listeners(db)
    )

    print_results(
        "Distribuzione ascolti per genere",
        listening_distribution_by_genre(db)
    )

    print("\nAggregation queries completate correttamente.")
    print("Le query sono solo in lettura e non modificano i dati del database.")


if __name__ == "__main__":
    main()