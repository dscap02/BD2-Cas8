# MongoDB Scripts

Questa cartella contiene gli script operativi utilizzati nel progetto **Music Archive NoSQL**.

Gli script permettono di:

- verificare operazioni CRUD controllate;
- eseguire query di analisi;
- misurare le prestazioni delle query;
- validare l’integrità dei dati;
- generare la cache usata dalla dashboard web.

## Prerequisiti

Prima di eseguire gli script, assicurarsi che:

- MongoDB sia avviato;
- il database `music_archive` sia stato popolato;
- le dipendenze Python siano installate.

Installazione dipendenze:

```bash
pip install -r requirements.txt
pip install -r mongodb/webapp/requirements.txt
```

Con Docker, gli script possono essere eseguiti nel container `web` tramite:

```bash
docker compose exec web python <path_script>
```

## Operazioni CRUD controllate

Script:

```text
mongodb/scripts/crud_operations.py
```

Lo script verifica il corretto funzionamento delle principali operazioni CRUD sulle collection:

- `tracks`;
- `artists`;
- `listeners`;
- `genres_tags`.

La collection `listening_history` viene gestita in modo non distruttivo, poiché rappresenta dati storici di ascolto.

Lo script utilizza esclusivamente documenti di test riconoscibili tramite il campo:

```python
test_marker = "crud_test"
```

In questo modo le operazioni di creazione, aggiornamento e cancellazione non alterano i dati reali provenienti dai dataset preprocessati.

Esecuzione manuale:

```bash
python mongodb/scripts/crud_operations.py
```

Esecuzione con Docker:

```bash
docker compose exec web python mongodb/scripts/crud_operations.py
```

Lo script esegue:

- lettura di documenti esistenti;
- inserimento controllato di documenti di test;
- aggiornamento dei documenti di test;
- cancellazione dei documenti di test;
- verifica finale dell’assenza di documenti di test residui.

## Query di analisi

Script:

```text
mongodb/scripts/aggregation_queries.py
```

Lo script esegue query di analisi tramite aggregation pipeline MongoDB.

Analisi incluse:

- riepilogo del numero di documenti per collection;
- top tracce più ascoltate;
- top artisti più ascoltati;
- top generi più ascoltati;
- listener più attivi;
- distribuzione degli ascolti per genere.

Esecuzione manuale:

```bash
python mongodb/scripts/aggregation_queries.py
```

Esecuzione con Docker:

```bash
docker compose exec web python mongodb/scripts/aggregation_queries.py
```

Le query utilizzano operatori come:

- `$lookup`;
- `$unwind`;
- `$group`;
- `$sort`;
- `$limit`;
- `$project`.

Le query sono esclusivamente in lettura e non modificano i dati presenti nel database.

## Benchmark delle query

Script:

```text
mongodb/scripts/benchmark_queries.py
```

Lo script analizza le prestazioni delle principali query sul database `music_archive`.

Per ogni query vengono raccolte metriche come:

- tipo di scansione (`IXSCAN` o `COLLSCAN`);
- tempo di esecuzione;
- documenti restituiti;
- documenti esaminati;
- chiavi dell’indice esaminate;
- indice utilizzato.

Lo script confronta query indicizzate con query forzate tramite:

```python
hint({"$natural": 1})
```

Esecuzione manuale:

```bash
python mongodb/scripts/benchmark_queries.py
```

Esecuzione con Docker:

```bash
docker compose exec web python mongodb/scripts/benchmark_queries.py
```

Il report viene salvato in:

```text
docs/mongodb-query-benchmark-results.json
```

Lo script esegue esclusivamente operazioni di lettura.

## Validazione del database

Script:

```text
mongodb/scripts/validate_database.py
```

Lo script verifica l’integrità dei dati e dei riferimenti tra le collection.

Controlli principali:

- validità dei riferimenti `tracks.artist_id`;
- validità dei riferimenti `tracks.genre_tag_id`;
- validità dei riferimenti `listening_history.track_id`;
- validità dei riferimenti `listening_history.listener_id`;
- presenza dei campi obbligatori;
- duplicati logici;
- struttura del campo embedded `audio_features`;
- duplicati sulla coppia `listener_id` e `track_id`.

Esecuzione manuale:

```bash
python mongodb/scripts/validate_database.py
```

Esecuzione con Docker:

```bash
docker compose exec web python mongodb/scripts/validate_database.py
```

Il report viene salvato in:

```text
docs/mongodb-validation-results.json
```

La validazione restituisce un esito complessivo:

```text
PASSED
```

oppure:

```text
FAILED
```

## Generazione cache dashboard

Script:

```text
mongodb/scripts/generate_dashboard_cache.py
```

La dashboard web utilizza una cache pre-calcolata per evitare di eseguire aggregation pipeline pesanti a ogni apertura della home.

Lo script genera il file:

```text
mongodb/webapp/data/dashboard_cache.json
```

Esecuzione manuale:

```bash
python mongodb/scripts/generate_dashboard_cache.py
```

Esecuzione con Docker:

```bash
docker compose exec web python mongodb/scripts/generate_dashboard_cache.py
```

La cache contiene:

- conteggi delle collection;
- top tracce più ascoltate;
- top artisti più ascoltati;
- top generi più ascoltati;
- listener più attivi;
- timestamp di generazione.

La cache deve essere rigenerata quando cambiano i dati del database.

## Flusso consigliato degli script

Dopo aver eseguito l’ingestione:

```bash
python mongodb/scripts/crud_operations.py
python mongodb/scripts/aggregation_queries.py
python mongodb/scripts/benchmark_queries.py
python mongodb/scripts/validate_database.py
python mongodb/scripts/generate_dashboard_cache.py
```

Con Docker:

```bash
docker compose exec web python mongodb/scripts/crud_operations.py
docker compose exec web python mongodb/scripts/aggregation_queries.py
docker compose exec web python mongodb/scripts/benchmark_queries.py
docker compose exec web python mongodb/scripts/validate_database.py
docker compose exec web python mongodb/scripts/generate_dashboard_cache.py
```

## Note

- Gli script CRUD usano documenti di test e non modificano i dati reali.
- Gli script di analisi, benchmark e validazione sono in sola lettura.
- La cache della dashboard va aggiornata dopo modifiche significative al database.
- I report JSON in `docs/` documentano i risultati di benchmark e validazione.
