import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError


MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "music_archive"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "docs" / "mongodb-validation-results.json"

COLLECTIONS = [
    "artists",
    "genres_tags",
    "tracks",
    "listeners",
    "listening_history",
]

REQUIRED_FIELDS = {
    "artists": [
        "_id",
        "name",
    ],
    "genres_tags": [
        "_id",
        "genre",
    ],
    "tracks": [
        "_id",
        "track_id",
        "name",
        "artist_id",
        "genre_tag_id",
        "audio_features",
    ],
    "listeners": [
        "_id",
        "original_user_id",
    ],
    "listening_history": [
        "_id",
        "listener_id",
        "track_id",
    ],
}

LOGICAL_IDENTIFIERS = {
    "tracks": "track_id",
    "listeners": "original_user_id",
}


def get_database():
    """
    Crea la connessione a MongoDB e restituisce il database.

    La connessione viene verificata tramite ping.
    """
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
    )

    client.admin.command("ping")

    return client[DB_NAME]


def serialize_value(value: Any) -> Any:
    """Converte ricorsivamente i tipi BSON in valori serializzabili."""
    if isinstance(value, dict):
        return {
            str(key): serialize_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [serialize_value(item) for item in value]

    if isinstance(value, tuple):
        return [serialize_value(item) for item in value]

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    return str(value)


def get_collection_counts(db) -> dict:
    """Restituisce il numero di documenti presenti in ogni collection."""
    return {
        collection_name: db[collection_name].count_documents({})
        for collection_name in COLLECTIONS
    }


def validate_reference(
    db,
    source_collection: str,
    source_field: str,
    target_collection: str,
) -> dict:
    """
    Verifica che ogni riferimento presente nella collection sorgente
    corrisponda a un documento della collection destinazione.

    La verifica viene effettuata tramite aggregation pipeline con $lookup.
    """
    total_with_reference = db[source_collection].count_documents(
        {
            source_field: {
                "$exists": True,
                "$ne": None,
            }
        }
    )

    pipeline = [
        {
            "$match": {
                source_field: {
                    "$exists": True,
                    "$ne": None,
                }
            }
        },
        {
            "$lookup": {
                "from": target_collection,
                "localField": source_field,
                "foreignField": "_id",
                "as": "target_document",
            }
        },
        {
            "$match": {
                "target_document": {
                    "$size": 0,
                }
            }
        },
        {
            "$count": "invalid_references"
        },
    ]

    result = list(
        db[source_collection].aggregate(
            pipeline,
            allowDiskUse=True,
        )
    )

    invalid_references = (
        result[0]["invalid_references"]
        if result
        else 0
    )

    return {
        "source_collection": source_collection,
        "source_field": source_field,
        "target_collection": target_collection,
        "documents_with_reference": total_with_reference,
        "valid_references": total_with_reference - invalid_references,
        "invalid_references": invalid_references,
        "is_valid": invalid_references == 0,
    }


def find_missing_required_fields(
    db,
    collection_name: str,
    required_fields: list[str],
) -> dict:
    """
    Conta i documenti nei quali ciascun campo obbligatorio è assente o nullo.
    """
    missing_fields = {}

    for field_name in required_fields:
        missing_count = db[collection_name].count_documents(
            {
                "$or": [
                    {
                        field_name: {
                            "$exists": False,
                        }
                    },
                    {
                        field_name: None,
                    },
                ]
            }
        )

        missing_fields[field_name] = missing_count

    documents_with_any_missing_field = db[
        collection_name
    ].count_documents(
        {
            "$or": [
                {
                    field_name: {
                        "$exists": False,
                    }
                }
                for field_name in required_fields
            ]
            + [
                {
                    field_name: None,
                }
                for field_name in required_fields
            ]
        }
    )

    return {
        "collection": collection_name,
        "required_fields": required_fields,
        "missing_by_field": missing_fields,
        "documents_with_missing_fields": documents_with_any_missing_field,
        "is_valid": documents_with_any_missing_field == 0,
    }


def find_duplicate_values(
    db,
    collection_name: str,
    field_name: str,
    sample_limit: int = 10,
) -> dict:
    """
    Individua valori duplicati per un identificativo logico.

    I documenti con campo assente o nullo non vengono considerati duplicati,
    perché sono già rilevati dalla validazione dei campi obbligatori.
    """
    duplicate_pipeline = [
        {
            "$match": {
                field_name: {
                    "$exists": True,
                    "$ne": None,
                }
            }
        },
        {
            "$group": {
                "_id": f"${field_name}",
                "count": {
                    "$sum": 1,
                },
            }
        },
        {
            "$match": {
                "count": {
                    "$gt": 1,
                }
            }
        },
        {
            "$sort": {
                "count": -1,
            }
        },
    ]

    count_pipeline = duplicate_pipeline + [
        {
            "$count": "duplicate_values"
        }
    ]

    count_result = list(
        db[collection_name].aggregate(
            count_pipeline,
            allowDiskUse=True,
        )
    )

    duplicate_values = (
        count_result[0]["duplicate_values"]
        if count_result
        else 0
    )

    samples = list(
        db[collection_name].aggregate(
            duplicate_pipeline
            + [
                {
                    "$limit": sample_limit,
                }
            ],
            allowDiskUse=True,
        )
    )

    duplicate_documents = sum(
        item["count"] - 1
        for item in samples
    )

    return {
        "collection": collection_name,
        "field": field_name,
        "duplicate_values": duplicate_values,
        "sample_duplicate_documents": duplicate_documents,
        "samples": serialize_value(samples),
        "is_valid": duplicate_values == 0,
    }


def validate_audio_features(db) -> dict:
    """
    Controlla che audio_features in tracks sia un documento embedded.
    """
    missing_audio_features = db.tracks.count_documents(
        {
            "$or": [
                {
                    "audio_features": {
                        "$exists": False,
                    }
                },
                {
                    "audio_features": None,
                },
            ]
        }
    )

    invalid_audio_features_type = db.tracks.count_documents(
        {
            "audio_features": {
                "$exists": True,
                "$ne": None,
                "$not": {
                    "$type": "object",
                },
            }
        }
    )

    return {
        "missing_audio_features": missing_audio_features,
        "invalid_type": invalid_audio_features_type,
        "is_valid": (
            missing_audio_features == 0
            and invalid_audio_features_type == 0
        ),
    }


def validate_listening_history_pairs(db) -> dict:
    """
    Verifica eventuali duplicati logici della coppia
    listener_id + track_id nella collection listening_history.
    """
    pipeline = [
        {
            "$match": {
                "listener_id": {
                    "$exists": True,
                    "$ne": None,
                },
                "track_id": {
                    "$exists": True,
                    "$ne": None,
                },
            }
        },
        {
            "$group": {
                "_id": {
                    "listener_id": "$listener_id",
                    "track_id": "$track_id",
                },
                "count": {
                    "$sum": 1,
                },
            }
        },
        {
            "$match": {
                "count": {
                    "$gt": 1,
                }
            }
        },
        {
            "$count": "duplicate_pairs"
        },
    ]

    result = list(
        db.listening_history.aggregate(
            pipeline,
            allowDiskUse=True,
        )
    )

    duplicate_pairs = (
        result[0]["duplicate_pairs"]
        if result
        else 0
    )

    return {
        "collection": "listening_history",
        "fields": [
            "listener_id",
            "track_id",
        ],
        "duplicate_pairs": duplicate_pairs,
        "is_valid": duplicate_pairs == 0,
    }


def calculate_overall_status(
    reference_checks: list[dict],
    required_field_checks: list[dict],
    duplicate_checks: list[dict],
    audio_features_check: dict,
    history_pair_check: dict,
) -> dict:
    """Determina l'esito complessivo della validazione."""
    failed_checks = []

    for check in reference_checks:
        if not check["is_valid"]:
            failed_checks.append(
                f"Riferimenti non validi: "
                f"{check['source_collection']}."
                f"{check['source_field']}"
            )

    for check in required_field_checks:
        if not check["is_valid"]:
            failed_checks.append(
                f"Campi obbligatori mancanti: "
                f"{check['collection']}"
            )

    for check in duplicate_checks:
        if not check["is_valid"]:
            failed_checks.append(
                f"Identificativi duplicati: "
                f"{check['collection']}."
                f"{check['field']}"
            )

    if not audio_features_check["is_valid"]:
        failed_checks.append(
            "Struttura audio_features non valida"
        )

    if not history_pair_check["is_valid"]:
        failed_checks.append(
            "Coppie listener_id/track_id duplicate"
        )

    return {
        "status": "PASSED" if not failed_checks else "FAILED",
        "is_valid": not failed_checks,
        "failed_checks": failed_checks,
    }


def print_collection_counts(counts: dict):
    """Stampa i conteggi delle collection."""
    print("\nCONTEGGIO COLLECTION")
    print("====================")

    for collection_name, count in counts.items():
        print(f"- {collection_name}: {count}")


def print_reference_checks(reference_checks: list[dict]):
    """Stampa i risultati dei controlli sui riferimenti."""
    print("\nVALIDAZIONE RIFERIMENTI")
    print("=======================")

    for check in reference_checks:
        reference_name = (
            f"{check['source_collection']}."
            f"{check['source_field']} -> "
            f"{check['target_collection']}._id"
        )

        print(f"\n{reference_name}")
        print(
            "  Documenti con riferimento:",
            check["documents_with_reference"],
        )
        print(
            "  Riferimenti validi:",
            check["valid_references"],
        )
        print(
            "  Riferimenti non validi:",
            check["invalid_references"],
        )
        print(
            "  Esito:",
            "OK" if check["is_valid"] else "ERRORE",
        )


def print_required_field_checks(checks: list[dict]):
    """Stampa i controlli sui campi obbligatori."""
    print("\nCAMPI OBBLIGATORI")
    print("=================")

    for check in checks:
        print(f"\n{check['collection']}")

        for field_name, missing_count in (
            check["missing_by_field"].items()
        ):
            print(
                f"  {field_name}: "
                f"{missing_count} documenti mancanti/nulli"
            )

        print(
            "  Documenti con almeno un campo mancante:",
            check["documents_with_missing_fields"],
        )
        print(
            "  Esito:",
            "OK" if check["is_valid"] else "ERRORE",
        )


def print_duplicate_checks(checks: list[dict]):
    """Stampa i controlli sugli identificativi duplicati."""
    print("\nIDENTIFICATIVI DUPLICATI")
    print("========================")

    for check in checks:
        print(
            f"- {check['collection']}.{check['field']}: "
            f"{check['duplicate_values']} valori duplicati"
        )


def save_report(report: dict):
    """Salva il report di validazione in formato JSON."""
    REPORT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with REPORT_PATH.open(
        "w",
        encoding="utf-8",
    ) as report_file:
        json.dump(
            serialize_value(report),
            report_file,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\nReport salvato in: {REPORT_PATH}")


def main():
    try:
        db = get_database()

        print(
            "Avvio validazione database:",
            DB_NAME,
        )
        print(
            "Lo script esegue esclusivamente operazioni "
            "di lettura."
        )

        collection_counts = get_collection_counts(db)

        reference_checks = [
            validate_reference(
                db,
                source_collection="tracks",
                source_field="artist_id",
                target_collection="artists",
            ),
            validate_reference(
                db,
                source_collection="tracks",
                source_field="genre_tag_id",
                target_collection="genres_tags",
            ),
            validate_reference(
                db,
                source_collection="listening_history",
                source_field="track_id",
                target_collection="tracks",
            ),
            validate_reference(
                db,
                source_collection="listening_history",
                source_field="listener_id",
                target_collection="listeners",
            ),
        ]

        required_field_checks = [
            find_missing_required_fields(
                db,
                collection_name,
                required_fields,
            )
            for collection_name, required_fields
            in REQUIRED_FIELDS.items()
        ]

        duplicate_checks = [
            find_duplicate_values(
                db,
                collection_name,
                field_name,
            )
            for collection_name, field_name
            in LOGICAL_IDENTIFIERS.items()
        ]

        audio_features_check = validate_audio_features(db)
        history_pair_check = validate_listening_history_pairs(db)

        overall_status = calculate_overall_status(
            reference_checks=reference_checks,
            required_field_checks=required_field_checks,
            duplicate_checks=duplicate_checks,
            audio_features_check=audio_features_check,
            history_pair_check=history_pair_check,
        )

        print_collection_counts(collection_counts)
        print_reference_checks(reference_checks)
        print_required_field_checks(required_field_checks)
        print_duplicate_checks(duplicate_checks)

        print("\nSTRUTTURA AUDIO FEATURES")
        print("========================")
        print(
            "Campi mancanti:",
            audio_features_check["missing_audio_features"],
        )
        print(
            "Tipi non validi:",
            audio_features_check["invalid_type"],
        )
        print(
            "Esito:",
            "OK" if audio_features_check["is_valid"] else "ERRORE",
        )

        print("\nDUPLICATI LISTENING HISTORY")
        print("===========================")
        print(
            "Coppie listener_id/track_id duplicate:",
            history_pair_check["duplicate_pairs"],
        )
        print(
            "Esito:",
            "OK" if history_pair_check["is_valid"] else "ERRORE",
        )

        print("\nESITO COMPLESSIVO")
        print("=================")
        print("Status:", overall_status["status"])

        if overall_status["failed_checks"]:
            print("Controlli non superati:")

            for failed_check in overall_status["failed_checks"]:
                print(f"- {failed_check}")
        else:
            print(
                "Il database ha superato tutti i controlli "
                "di integrità."
            )

        report = {
            "database": DB_NAME,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "read_only": True,
            "collection_counts": collection_counts,
            "reference_checks": reference_checks,
            "required_field_checks": required_field_checks,
            "duplicate_checks": duplicate_checks,
            "audio_features_check": audio_features_check,
            "listening_history_pair_check": history_pair_check,
            "overall_status": overall_status,
        }

        save_report(report)

        print("\nValidazione completata.")
        print(
            "Nessun documento è stato modificato "
            "o cancellato."
        )

    except (PyMongoError, RuntimeError) as error:
        print(
            f"\nErrore durante la validazione: {error}"
        )
        raise


if __name__ == "__main__":
    main()