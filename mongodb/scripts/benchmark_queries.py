import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.errors import OperationFailure, PyMongoError


MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "music_archive"

# Il report viene salvato nella cartella docs del repository.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "docs" / "mongodb-query-benchmark-results.json"


def get_database():
    """Crea la connessione a MongoDB e restituisce il database."""
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=5000,
    )

    client.admin.command("ping")
    return client[DB_NAME]


def serialize_value(value: Any) -> Any:
    """Converte ricorsivamente ObjectId, date e altri tipi BSON in stringhe."""
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


def collect_plan_stages(plan: Any) -> list[str]:
    """
    Estrae ricorsivamente gli stage del piano di esecuzione,
    ad esempio IXSCAN, COLLSCAN e FETCH.
    """
    stages = []

    if isinstance(plan, dict):
        stage = plan.get("stage")

        if stage:
            stages.append(stage)

        for value in plan.values():
            stages.extend(collect_plan_stages(value))

    elif isinstance(plan, list):
        for item in plan:
            stages.extend(collect_plan_stages(item))

    # Rimuove duplicati mantenendo l'ordine.
    return list(dict.fromkeys(stages))


def determine_scan_type(stages: list[str]) -> str:
    """Determina il tipo principale di scansione usato dalla query."""
    if "IXSCAN" in stages:
        return "IXSCAN"

    if "COLLSCAN" in stages:
        return "COLLSCAN"

    if "IDHACK" in stages:
        return "IDHACK"

    if "EXPRESS_IXSCAN" in stages:
        return "EXPRESS_IXSCAN"

    return "NON DETERMINATO"


def get_indexes(collection: Collection) -> list[dict]:
    """
    Restituisce gli indici definiti su una collection.

    L'indice MongoDB `_id_` è sempre univoco, anche quando il campo
    `unique` non viene restituito esplicitamente da list_indexes().
    """
    indexes = []

    for index in collection.list_indexes():
        index_name = index.get("name")

        indexes.append(
            {
                "name": index_name,
                "key": dict(index.get("key", {})),
                "unique": (
                    index.get("unique", False)
                    or index_name == "_id_"
                ),
            }
        )

    return indexes


def find_index_name(collection: Collection, field_name: str) -> str | None:
    """
    Cerca un indice il cui primo campo corrisponde al campo richiesto.

    Restituisce il nome dell'indice, oppure None se non è presente.
    """
    for index in collection.list_indexes():
        index_keys = list(index.get("key", {}).keys())

        if index_keys and index_keys[0] == field_name:
            return index.get("name")

    return None


def explain_find(
    db,
    collection_name: str,
    query: dict,
    hint: str | dict | None = None,
    limit: int | None = None,
) -> dict:
    """
    Esegue explain con executionStats su una query find.

    L'utilizzo di db.command permette di specificare esplicitamente
    il livello executionStats e l'eventuale hint.
    """
    find_command = {
        "find": collection_name,
        "filter": query,
    }

    if hint is not None:
        find_command["hint"] = hint

    if limit is not None:
        find_command["limit"] = limit

    return db.command(
        "explain",
        find_command,
        verbosity="executionStats",
    )


def extract_metrics(explain_result: dict) -> dict:
    """Estrae le principali metriche dal risultato di explain."""
    execution_stats = explain_result.get("executionStats", {})
    execution_stages = execution_stats.get("executionStages", {})

    stages = collect_plan_stages(execution_stages)

    if not stages:
        winning_plan = (
            explain_result
            .get("queryPlanner", {})
            .get("winningPlan", {})
        )
        stages = collect_plan_stages(winning_plan)

    return {
        "scan_type": determine_scan_type(stages),
        "stages": stages,
        "execution_time_ms": execution_stats.get(
            "executionTimeMillis"
        ),
        "documents_returned": execution_stats.get("nReturned"),
        "documents_examined": execution_stats.get(
            "totalDocsExamined"
        ),
        "keys_examined": execution_stats.get(
            "totalKeysExamined"
        ),
    }


def execute_benchmark(
    db,
    title: str,
    collection_name: str,
    query: dict,
    indexed_hint: str | None,
    limit: int | None = None,
) -> dict:
    """
    Confronta la query eseguita tramite indice con la stessa query
    forzata a usare l'ordine naturale della collection.
    """
    collection = db[collection_name]

    benchmark = {
        "title": title,
        "collection": collection_name,
        "query": serialize_value(query),
        "limit": limit,
        "index_name": indexed_hint,
        "with_index": None,
        "without_index": None,
    }

    print(f"\n{title}")
    print("-" * len(title))
    print("Collection:", collection_name)
    print("Filtro:", serialize_value(query))

    if indexed_hint is not None:
        try:
            indexed_explain = explain_find(
                db=db,
                collection_name=collection_name,
                query=query,
                hint=indexed_hint,
                limit=limit,
            )

            indexed_metrics = extract_metrics(indexed_explain)
            benchmark["with_index"] = indexed_metrics

            print_metrics(
                f"Con indice ({indexed_hint})",
                indexed_metrics,
            )

        except OperationFailure as error:
            benchmark["with_index"] = {
                "error": str(error)
            }
            print(
                f"Benchmark con indice non eseguito: {error}"
            )

    else:
        print(
            "Nessun indice specifico trovato per il campo "
            "della query."
        )

    try:
        natural_explain = explain_find(
            db=db,
            collection_name=collection_name,
            query=query,
            hint={"$natural": 1},
            limit=limit,
        )

        natural_metrics = extract_metrics(natural_explain)
        benchmark["without_index"] = natural_metrics

        print_metrics(
            "Senza indice ($natural)",
            natural_metrics,
        )

    except OperationFailure as error:
        benchmark["without_index"] = {
            "error": str(error)
        }
        print(
            f"Benchmark senza indice non eseguito: {error}"
        )

    return benchmark


def print_metrics(label: str, metrics: dict):
    """Stampa le metriche di una singola esecuzione."""
    print(f"\n{label}")
    print("  Tipo scansione:", metrics.get("scan_type"))
    print("  Stage:", ", ".join(metrics.get("stages", [])))
    print(
        "  Tempo esecuzione:",
        metrics.get("execution_time_ms"),
        "ms",
    )
    print(
        "  Documenti restituiti:",
        metrics.get("documents_returned"),
    )
    print(
        "  Documenti esaminati:",
        metrics.get("documents_examined"),
    )
    print(
        "  Chiavi esaminate:",
        metrics.get("keys_examined"),
    )


def print_collection_indexes(db) -> dict:
    """Stampa e restituisce gli indici delle collection analizzate."""
    collection_names = [
        "tracks",
        "listeners",
        "listening_history",
    ]

    all_indexes = {}

    print("\nINDICI PRESENTI")
    print("================")

    for collection_name in collection_names:
        collection = db[collection_name]
        indexes = get_indexes(collection)
        all_indexes[collection_name] = indexes

        print(f"\n{collection_name}")

        for index in indexes:
            print(
                f"- {index['name']}: "
                f"{index['key']} "
                f"(unique={index['unique']})"
            )

    return all_indexes


def get_sample_values(db) -> dict:
    """
    Recupera identificativi reali da usare nei benchmark.

    Non vengono inseriti o modificati documenti.
    """
    track = db.tracks.find_one(
        {},
        {"_id": 1},
    )

    listener = db.listeners.find_one(
        {},
        {"_id": 1},
    )

    history = db.listening_history.find_one(
        {
            "track_id": {"$exists": True},
            "listener_id": {"$exists": True},
        },
        {
            "_id": 0,
            "track_id": 1,
            "listener_id": 1,
        },
    )

    if track is None:
        raise RuntimeError(
            "La collection tracks non contiene documenti."
        )

    if listener is None:
        raise RuntimeError(
            "La collection listeners non contiene documenti."
        )

    if history is None:
        raise RuntimeError(
            "Non è stato trovato un documento valido in "
            "listening_history."
        )

    return {
        "track_object_id": track["_id"],
        "listener_object_id": listener["_id"],
        "history_track_id": history["track_id"],
        "history_listener_id": history["listener_id"],
    }


def save_report(report: dict):
    """Salva il report completo in formato JSON."""
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

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
            "Avvio benchmark query sul database:",
            DB_NAME,
        )
        print(
            "Lo script esegue esclusivamente operazioni "
            "di lettura."
        )

        indexes = print_collection_indexes(db)
        samples = get_sample_values(db)

        benchmarks = []

        # 1. Ricerca di una traccia tramite ObjectId.
        track_index = find_index_name(
            db.tracks,
            "_id",
        )

        benchmarks.append(
            execute_benchmark(
                db=db,
                title="Ricerca traccia tramite _id",
                collection_name="tracks",
                query={
                    "_id": samples["track_object_id"]
                },
                indexed_hint=track_index,
            )
        )

        # 2. Ricerca di un listener tramite ObjectId.
        listener_index = find_index_name(
            db.listeners,
            "_id",
        )

        benchmarks.append(
            execute_benchmark(
                db=db,
                title="Ricerca listener tramite _id",
                collection_name="listeners",
                query={
                    "_id": samples["listener_object_id"]
                },
                indexed_hint=listener_index,
            )
        )

        # 3. Ricerca degli ascolti associati a una traccia.
        history_track_index = find_index_name(
            db.listening_history,
            "track_id",
        )

        benchmarks.append(
            execute_benchmark(
                db=db,
                title="Ricerca ascolti tramite track_id",
                collection_name="listening_history",
                query={
                    "track_id": samples["history_track_id"]
                },
                indexed_hint=history_track_index,
                limit=1000,
            )
        )

        # 4. Ricerca degli ascolti associati a un listener.
        history_listener_index = find_index_name(
            db.listening_history,
            "listener_id",
        )

        benchmarks.append(
            execute_benchmark(
                db=db,
                title="Ricerca ascolti tramite listener_id",
                collection_name="listening_history",
                query={
                    "listener_id": samples[
                        "history_listener_id"
                    ]
                },
                indexed_hint=history_listener_index,
                limit=1000,
            )
        )

        report = {
            "database": DB_NAME,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "read_only": True,
            "indexes": indexes,
            "sample_values": serialize_value(samples),
            "benchmarks": benchmarks,
        }

        save_report(report)

        print("\nBenchmark completato correttamente.")
        print(
            "Nessun indice è stato eliminato e nessun "
            "documento è stato modificato."
        )

    except (PyMongoError, RuntimeError) as error:
        print(f"\nErrore durante il benchmark: {error}")
        raise


if __name__ == "__main__":
    main()