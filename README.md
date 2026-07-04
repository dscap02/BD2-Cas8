# Music Archive NoSQL

Progetto per il corso di Basi di Dati 2 del Corso di Laurea Magistrale in Informatica dell'Università degli Studi di Salerno.

## Descrizione

Sistema NoSQL per la gestione e l’analisi di un archivio musicale e della relativa cronologia di ascolto.

Il progetto permette di:

* esplorare brani, artisti, generi e listener;
* eseguire operazioni CRUD controllate;
* analizzare i dati tramite aggregation pipeline MongoDB;
* verificare l’integrità dei riferimenti tra le collection;
* confrontare le prestazioni delle query con e senza indici;
* consultare i dati tramite una dashboard web Flask.

## Obiettivo

Costruire una piattaforma che simula un archivio musicale utilizzando MongoDB, con particolare attenzione a:

* modellazione dei dati;
* preprocessing e validazione dei dataset;
* ingestion dei dati;
* query e aggregazioni;
* operazioni CRUD;
* analisi delle interazioni degli utenti;
* verifica degli indici e delle prestazioni;
* visualizzazione dei dati tramite interfaccia web.

## Dataset

Il progetto utilizza due dataset preprocessati:

* `music_info_cleaned.csv`;
* `listening_history_cleaned.csv`.

I dataset contengono informazioni relative a:

* tracce musicali;
* artisti;
* generi e tag;
* utenti;
* cronologia degli ascolti;
* caratteristiche audio delle tracce.

## Preprocessing e Data Analysis

Prima dell’ingestione in MongoDB, i dataset sono stati analizzati e validati tramite notebook dedicati.

In particolare:

* **music_info**: operazioni di data cleaning e gestione dei valori mancanti, con particolare attenzione alla variabile `genre`;
* **listening_history**: analisi esplorativa e verifica della qualità dei dati.

Le principali attività svolte includono:

* analisi della struttura dei dataset, delle colonne, delle dimensioni e dei tipi di dato;
* verifica di valori nulli, duplicati e inconsistenze;
* studio delle distribuzioni, come quella di `playcount`, caratterizzata da una long tail;
* analisi della cardinalità di `user_id` e `track_id`;
* validazione delle chiavi logiche, come la coppia `user_id` e `track_id`;
* verifica della compatibilità dei dati con il successivo caricamento in MongoDB.

I risultati hanno evidenziato dataset complessivamente consistenti e pronti per l’utilizzo, con interventi mirati di preprocessing.

I dataset risultanti vengono utilizzati come base per:

* l’ingestione in MongoDB;
* la progettazione delle collection;
* le query e le analisi successive;
* la dashboard web.

## Schema MongoDB

Lo schema del database MongoDB è stato progettato a partire dai dataset preprocessati, con l’obiettivo di rappresentare in modo chiaro le entità principali del dominio musicale.

Il database `music_archive` è composto da cinque collection principali:

* `artists`;
* `genres_tags`;
* `tracks`;
* `listeners`;
* `listening_history`.

La progettazione utilizza principalmente riferimenti tramite `ObjectId` tra le collection.

In particolare:

* `tracks.artist_id` referenzia `artists._id`;
* `tracks.genre_tag_id` referenzia `genres_tags._id`;
* `listening_history.listener_id` referenzia `listeners._id`;
* `listening_history.track_id` referenzia `tracks._id`.

Le `audio_features` sono modellate come oggetto embedded all’interno dei documenti della collection `tracks`.

La documentazione completa dello schema, con descrizione delle collection, dei campi, delle relazioni e delle scelte di modellazione, è disponibile in:

[`mongodb/README.md`](mongodb/README.md)

## Data Ingestion

L’ingestione dei dati in MongoDB viene eseguita tramite uno script Python dedicato, che legge i dataset preprocessati e popola il database secondo lo schema definito.

Lo script crea e popola le collection nel seguente ordine:

1. `artists`;
2. `genres_tags`;
3. `tracks`;
4. `listeners`;
5. `listening_history`.

Questo ordine rispetta le dipendenze tra i documenti, poiché `tracks` referenzia `artists` e `genres_tags`, mentre `listening_history` referenzia `listeners` e `tracks`.

La documentazione completa della procedura di ingestione, con comandi di esecuzione, verifica delle collection, controllo dei riferimenti e indici creati, è disponibile in:

[`mongodb/ingestion/README.md`](mongodb/ingestion/README.md)

## Operazioni CRUD MongoDB

Il progetto include lo script:

```text
mongodb/scripts/crud_operations.py
```

Lo script verifica il corretto funzionamento delle operazioni CRUD sulle collection principali:

* `artists`;
* `genres_tags`;
* `tracks`;
* `listeners`.

Le operazioni implementate sono:

* `create`: inserimento di documenti di test;
* `read`: lettura dei documenti creati;
* `update`: aggiornamento controllato dei documenti di test;
* `delete`: cancellazione dei documenti di test;
* verifica finale della corretta rimozione dei documenti temporanei.

I documenti di test sono identificati tramite il campo:

```python
test_marker = "crud_test"
```

La collection `listening_history` viene utilizzata esclusivamente in lettura, poiché rappresenta dati storici di ascolto.

Per eseguire lo script:

```bash
python mongodb/scripts/crud_operations.py
```

Lo script non modifica né cancella i dati reali provenienti dai dataset preprocessati.

## Query di analisi MongoDB

Il progetto include uno script dedicato alle query di analisi sul database MongoDB `music_archive`.

Lo script utilizza aggregation pipeline per analizzare le relazioni tra:

* `listening_history`;
* `tracks`;
* `artists`;
* `genres_tags`;
* `listeners`.

Per eseguire lo script:

```bash
python mongodb/scripts/aggregation_queries.py
```

Le analisi incluse sono:

* riepilogo del numero di documenti per collection;
* top tracce più ascoltate;
* top artisti più ascoltati;
* top generi più ascoltati;
* listener più attivi;
* distribuzione degli ascolti per genere.

Le pipeline utilizzano operatori MongoDB come:

* `$lookup`;
* `$unwind`;
* `$group`;
* `$sort`;
* `$limit`;
* `$project`.

Le query sono esclusivamente in lettura e non modificano i dati presenti nel database.

## Benchmark delle query MongoDB

Il progetto include uno script per analizzare le prestazioni delle principali query sul database `music_archive`.

Per eseguire il benchmark:

```bash
python mongodb/scripts/benchmark_queries.py
```

Lo script confronta l’esecuzione delle query tramite indice con una scansione naturale della collection, utilizzando:

```python
hint({"$natural": 1})
```

Per ogni query vengono riportati:

* tipo di scansione, come `IXSCAN` o `COLLSCAN`;
* tempo di esecuzione;
* documenti restituiti;
* documenti esaminati;
* chiavi dell’indice esaminate;
* indice utilizzato.

I benchmark includono:

* ricerca di una traccia tramite `_id`;
* ricerca di un listener tramite `_id`;
* ricerca degli ascolti tramite `track_id`;
* ricerca degli ascolti tramite `listener_id`.

I risultati vengono salvati nel file:

```text
docs/mongodb-query-benchmark-results.json
```

Lo script esegue esclusivamente operazioni di lettura e non elimina o modifica gli indici presenti nel database.

## Validazione dell’integrità del database

Il progetto include uno script per verificare l’integrità dei documenti e dei riferimenti tra le collection MongoDB.

Per eseguire la validazione:

```bash
python mongodb/scripts/validate_database.py
```

Lo script controlla:

* validità dei riferimenti tra `tracks`, `artists` e `genres_tags`;
* validità dei riferimenti tra `listening_history`, `tracks` e `listeners`;
* presenza dei campi obbligatori;
* eventuali identificativi logici duplicati;
* struttura del campo embedded `audio_features`;
* eventuali coppie duplicate `listener_id` e `track_id`;
* conteggi complessivi delle collection.

I risultati vengono salvati nel file:

```text
docs/mongodb-validation-results.json
```

La validazione restituisce un esito complessivo `PASSED` oppure `FAILED`.

Lo script esegue esclusivamente operazioni di lettura e non modifica i dati presenti nel database.

## Dashboard web

Il progetto include una dashboard Flask per esplorare il database MongoDB tramite interfaccia web.

La dashboard permette di:

* visualizzare i conteggi delle collection principali;
* consultare le tracce più ascoltate;
* consultare gli artisti più ascoltati;
* consultare i generi più ascoltati;
* consultare i listener più attivi;
* cercare tracce per titolo;
* filtrare le tracce per genere, anno e tag;
* combinare più filtri nella stessa ricerca;
* visualizzare il dettaglio di una traccia;
* visualizzare il dettaglio di un artista;
* consultare le tracce associate a un artista;
* aprire una traccia tramite applicazione Spotify o Spotify Web, quando lo Spotify ID è disponibile.

La dashboard è organizzata nella directory:

```text
mongodb/webapp/
```

La struttura principale è:

```text
mongodb/webapp/
├── app.py
├── requirements.txt
├── data/
│   └── dashboard_cache.json
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── tracks.html
│   ├── track_detail.html
│   ├── artists.html
│   └── artist_detail.html
└── static/
    └── css/
        └── style.css
```

### Cache della dashboard

Le classifiche della dashboard vengono pre-calcolate per evitare di eseguire aggregation pipeline su milioni di documenti a ogni apertura della pagina.

Per generare o aggiornare la cache:

```bash
python mongodb/scripts/generate_dashboard_cache.py
```

Il file generato è:

```text
mongodb/webapp/data/dashboard_cache.json
```

La cache deve essere rigenerata quando cambiano i dati presenti nel database.

### Avvio della dashboard

Assicurarsi che MongoDB sia avviato e che il database `music_archive` sia già stato popolato.

Installare le dipendenze:

```bash
pip install -r mongodb/webapp/requirements.txt
```

Generare la cache, se non ancora presente:

```bash
python mongodb/scripts/generate_dashboard_cache.py
```

Avviare l’applicazione:

```bash
python mongodb/webapp/app.py
```

La dashboard sarà disponibile all’indirizzo:

```text
http://127.0.0.1:5000
```

Per utilizzare una configurazione MongoDB differente è possibile impostare le variabili d’ambiente:

```bash
export MONGO_URI="mongodb://localhost:27017/"
export MONGO_DB_NAME="music_archive"
```

La dashboard esegue esclusivamente operazioni di lettura e non modifica né cancella documenti.

## Flusso di esecuzione

L’ordine consigliato per eseguire il progetto è il seguente:

1. attivare l’ambiente virtuale;
2. installare le dipendenze;
3. avviare MongoDB;
4. eseguire l’ingestione dei dataset;
5. verificare le operazioni CRUD;
6. eseguire le query di analisi;
7. eseguire il benchmark;
8. validare l’integrità del database;
9. generare la cache della dashboard;
10. avviare la web app.

Esempio:

```bash
source .venv/bin/activate

pip install -r requirements.txt
pip install -r mongodb/webapp/requirements.txt

python mongodb/scripts/ingest_mongodb.py
python mongodb/scripts/crud_operations.py
python mongodb/scripts/aggregation_queries.py
python mongodb/scripts/benchmark_queries.py
python mongodb/scripts/validate_database.py
python mongodb/scripts/generate_dashboard_cache.py
python mongodb/webapp/app.py
```

Non è necessario eseguire tutti gli script a ogni avvio.

Dopo la prima configurazione, per avviare solamente la dashboard è sufficiente:

```bash
source .venv/bin/activate
python mongodb/webapp/app.py
```

La cache deve essere rigenerata solamente quando cambiano i dati del database.

## Requisiti

* Python 3.12;
* MongoDB 8.0.

Per installare i pacchetti Python necessari al progetto:

```bash
pip install -r requirements.txt
```

Per installare le dipendenze specifiche della dashboard Flask:

```bash
pip install -r mongodb/webapp/requirements.txt
```
