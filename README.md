# Music Archive NoSQL

Progetto per il corso di **Basi di Dati 2** del Corso di Laurea Magistrale in Informatica dell'Università degli Studi di Salerno.

## Descrizione

**Music Archive NoSQL** è un sistema basato su MongoDB per la gestione e l’analisi di un archivio musicale e della relativa cronologia di ascolto.

Il progetto permette di:

- modellare un dominio musicale tramite database NoSQL;
- caricare dataset preprocessati in MongoDB;
- eseguire operazioni CRUD controllate;
- analizzare i dati tramite aggregation pipeline;
- verificare l’integrità dei riferimenti tra collection;
- analizzare le prestazioni delle query e degli indici;
- esplorare i dati tramite una dashboard web Flask;
- gestire tracce e ascolti tramite una dashboard amministratore;
- avviare il progetto manualmente o tramite Docker.

## Obiettivo

L’obiettivo del progetto è costruire una piattaforma che simula un archivio musicale NoSQL, con particolare attenzione a:

- progettazione dello schema MongoDB;
- preprocessing dei dataset;
- ingestione dei dati;
- query CRUD;
- aggregation pipeline;
- benchmark delle query;
- validazione dei riferimenti;
- visualizzazione tramite web app;
- replicabilità tramite Docker.

## Struttura del progetto

```text
.
├── Dockerfile
├── README.md
├── dataset/
│   ├── listening_history_cleaned.csv
│   └── music_info_cleaned.csv
├── docker-compose.yml
├── docs/
│   ├── mongodb-query-benchmark-results.json
│   └── mongodb-validation-results.json
├── mongodb/
│   ├── README.md
│   ├── ingestion/
│   │   ├── README.md
│   │   └── mongodb-ingestion.py
│   ├── scripts/
│   │   ├── README.md
│   │   ├── aggregation_queries.py
│   │   ├── benchmark_queries.py
│   │   ├── crud_operations.py
│   │   ├── generate_dashboard_cache.py
│   │   └── validate_database.py
│   └── webapp/
│       ├── admin_service.py
│       ├── app.py
│       ├── data/
│       │   └── dashboard_cache.json
│       ├── requirements.txt
│       ├── static/
│       │   ├── css/
│       │   │   └── style.css
│       │   └── js/
│       │       └── admin.js
│       └── templates/
└── notebooks/
    ├── data_analysis&pre-processing_ListeningHistory.ipynb
    └── data_analysis&pre-processing_Music_Info.ipynb
```

## Dataset

Il progetto utilizza due dataset preprocessati:

```text
dataset/music_info_cleaned.csv
dataset/listening_history_cleaned.csv
```

I dataset contengono informazioni relative a:

- tracce musicali;
- artisti;
- generi e tag;
- listener;
- cronologia degli ascolti;
- caratteristiche audio delle tracce.

I notebook di analisi e preprocessing sono disponibili nella cartella:

```text
notebooks/
```

## Schema MongoDB

Il database utilizzato dal progetto si chiama:

```text
music_archive
```

È composto da cinque collection principali:

- `artists`;
- `genres_tags`;
- `tracks`;
- `listeners`;
- `listening_history`.

Le collection sono collegate tramite riferimenti `ObjectId`.

Relazioni principali:

```text
tracks.artist_id              -> artists._id
tracks.genre_tag_id           -> genres_tags._id
listening_history.listener_id -> listeners._id
listening_history.track_id    -> tracks._id
```

Le `audio_features` sono salvate come oggetto embedded dentro i documenti della collection `tracks`.

La documentazione completa dello schema MongoDB è disponibile in:

```text
mongodb/README.md
```

## Ingestione dati

L’ingestione dei dati in MongoDB viene eseguita tramite lo script:

```text
mongodb/ingestion/mongodb-ingestion.py
```

Per eseguire l’ingestione partendo dai dataset preprocessati:

```bash
python mongodb/ingestion/mongodb-ingestion.py --drop
```

L’opzione `--drop` elimina le collection esistenti prima del nuovo caricamento, rendendo l’ingestione pulita e replicabile.

La documentazione completa della procedura di ingestione è disponibile in:

```text
mongodb/ingestion/README.md
```

## Script MongoDB

Il progetto include script dedicati per:

- operazioni CRUD controllate;
- query di analisi con aggregation pipeline;
- benchmark delle query;
- validazione dell’integrità del database;
- generazione della cache della dashboard.

Gli script sono disponibili in:

```text
mongodb/scripts/
```

Comandi principali:

```bash
python mongodb/scripts/crud_operations.py
python mongodb/scripts/aggregation_queries.py
python mongodb/scripts/benchmark_queries.py
python mongodb/scripts/validate_database.py
python mongodb/scripts/generate_dashboard_cache.py
```

La documentazione completa degli script è disponibile in:

```text
mongodb/scripts/README.md
```

## Dashboard web

Il progetto include una web app Flask che permette di esplorare il database tramite interfaccia grafica.

La dashboard permette di:

- visualizzare i conteggi delle collection principali;
- consultare le tracce più ascoltate;
- consultare gli artisti più ascoltati;
- consultare i generi più ascoltati;
- consultare i listener più attivi;
- cercare tracce per titolo;
- filtrare tracce per genere, anno e tag;
- visualizzare il dettaglio di una traccia;
- visualizzare il dettaglio di un artista;
- aprire una traccia su Spotify, quando disponibile.

La web app è disponibile in:

```text
mongodb/webapp/
```

La documentazione completa della dashboard è disponibile in:

```text
mongodb/webapp/README.md
```

## Dashboard amministratore

La web app include anche una dashboard amministratore accessibile da:

```text
/admin
```

La dashboard amministratore permette di:

- creare nuove tracce;
- modificare tracce esistenti;
- eliminare tracce solo se non sono collegate alla cronologia degli ascolti;
- registrare nuovi ascolti collegando un listener esistente a una traccia esistente;
- cercare tracce e listener tramite suggerimenti;
- evitare l’inserimento manuale di ObjectId nell’interfaccia;
- compilare in modo assistito alcuni campi tramite link Spotify.

L’integrazione Spotify è opzionale.

Se sono configurate credenziali valide per la Spotify Web API, il sistema prova a recuperare metadati come titolo, artista, album, anno e durata.

Se le credenziali non sono disponibili oppure l’accesso alla Web API non è consentito, il sistema usa un fallback tramite Spotify oEmbed e permette la compilazione manuale dei campi mancanti.

## Configurazione ambiente

Creare un file `.env` a partire da `.env.example`:

```bash
cp .env.example .env
```

Esempio di configurazione:

```env
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=music_archive

FLASK_HOST=127.0.0.1
FLASK_PORT=5000
FLASK_DEBUG=true
FLASK_SECRET_KEY=change_me_with_a_random_secret_key

SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
```

Il file `.env` non deve essere salvato nel repository.

Le credenziali Spotify sono opzionali.

## Requisiti

Per esecuzione manuale:

- Python 3.12;
- MongoDB 8.0;
- pip;
- ambiente virtuale Python consigliato.

Per esecuzione Docker:

- Docker;
- Docker Compose.

## Installazione manuale

Creare e attivare l’ambiente virtuale:

```bash
python -m venv .venv
source .venv/bin/activate
```

Installare le dipendenze principali:

```bash
pip install -r requirements.txt
```

Installare le dipendenze della web app:

```bash
pip install -r mongodb/webapp/requirements.txt
```

## Avvio manuale

Assicurarsi che MongoDB sia avviato localmente su:

```text
mongodb://localhost:27017/
```

Eseguire l’ingestione:

```bash
python mongodb/ingestion/mongodb-ingestion.py --drop
```

Validare il database:

```bash
python mongodb/scripts/validate_database.py
```

Generare la cache della dashboard:

```bash
python mongodb/scripts/generate_dashboard_cache.py
```

Avviare la web app:

```bash
python mongodb/webapp/app.py
```

La dashboard sarà disponibile su:

```text
http://127.0.0.1:5000
```

La dashboard amministratore sarà disponibile su:

```text
http://127.0.0.1:5000/admin
```

## Avvio con Docker

Il progetto può essere avviato tramite Docker Compose.

La configurazione Docker avvia:

- un container MongoDB;
- un container Flask;
- una rete interna tra web app e database;
- un volume persistente per i dati MongoDB.

Creare il file `.env`:

```bash
cp .env.example .env
```

Avviare i container:

```bash
docker compose up --build -d
```

Verificare lo stato:

```bash
docker compose ps
```

La web app in Docker sarà disponibile su:

```text
http://127.0.0.1:5050
```

La dashboard amministratore sarà disponibile su:

```text
http://127.0.0.1:5050/admin
```

MongoDB sarà esposto localmente sulla porta:

```text
27017
```

## Esecuzione script con Docker

Dopo aver avviato i container, è possibile eseguire gli script nel container `web`.

Ingestione:

```bash
docker compose exec web python mongodb/ingestion/mongodb-ingestion.py --drop
```

Validazione:

```bash
docker compose exec web python mongodb/scripts/validate_database.py
```

Query di analisi:

```bash
docker compose exec web python mongodb/scripts/aggregation_queries.py
```

Benchmark:

```bash
docker compose exec web python mongodb/scripts/benchmark_queries.py
```

Generazione cache dashboard:

```bash
docker compose exec web python mongodb/scripts/generate_dashboard_cache.py
```

## Flusso consigliato con Docker

```bash
docker compose up --build -d
docker compose exec web python mongodb/ingestion/mongodb-ingestion.py --drop
docker compose exec web python mongodb/scripts/validate_database.py
docker compose exec web python mongodb/scripts/generate_dashboard_cache.py
```

Poi aprire:

```text
http://127.0.0.1:5050
```

## Arresto Docker

Per fermare i container:

```bash
docker compose down
```

Per fermare i container ed eliminare anche il volume MongoDB:

```bash
docker compose down -v
```

Attenzione: usando `-v` vengono eliminati anche i dati salvati nel volume MongoDB.

## Flusso finale consigliato

Per una verifica completa del progetto:

```bash
python mongodb/ingestion/mongodb-ingestion.py --drop
python mongodb/scripts/crud_operations.py
python mongodb/scripts/aggregation_queries.py
python mongodb/scripts/benchmark_queries.py
python mongodb/scripts/validate_database.py
python mongodb/scripts/generate_dashboard_cache.py
python mongodb/webapp/app.py
```

Con Docker:

```bash
docker compose up --build -d
docker compose exec web python mongodb/ingestion/mongodb-ingestion.py --drop
docker compose exec web python mongodb/scripts/validate_database.py
docker compose exec web python mongodb/scripts/generate_dashboard_cache.py
```

## Documentazione dettagliata

- Schema MongoDB: `mongodb/README.md`
- Ingestione dati: `mongodb/ingestion/README.md`
- Script MongoDB: `mongodb/scripts/README.md`
- Web app Flask: `mongodb/webapp/README.md`
