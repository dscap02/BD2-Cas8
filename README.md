# Music Archive NoSQL

Progetto per il corso di Basi di Dati 2 del Corso di Laurea Magistrale in Informatica dell'Università degli Studi di Salerno.

## Descrizione
Sistema NoSQL per la gestione e analisi della cronologia di ascolto musicale.  
Permette di esplorare brani, artisti e utenti, ed eseguire operazioni di query e analisi sui dati.

## Obiettivo
Costruire una piattaforma che simula un archivio musicale utilizzando database NoSQL, con focus su:
- modellazione dati
- query e aggregazioni
- operazioni CRUD
- analisi delle interazioni utente

## Dataset
Dataset musicale contenente:
- tracce 
- utenti 
- cronologia ascolti 

## Preprocessing e Data Analysis

Prima dell’ingestione in MongoDB, i dataset sono stati analizzati e validati tramite notebook dedicati.

In particolare:
- **music_info**: operazioni di data cleaning e gestione dei valori mancanti (in particolare sulla variabile `genre`)
- **listening_history**: analisi esplorativa e verifica della qualità dei dati

Le principali attività svolte includono:
- analisi della struttura dei dataset (colonne, dimensioni, tipi di dato)
- verifica di valori nulli, duplicati e inconsistenze
- studio delle distribuzioni (es. `playcount`, con evidenza di long tail)
- validazione delle chiavi logiche (es. `user_id` + `track_id`)

I risultati hanno evidenziato dataset complessivamente consistenti e pronti per l’utilizzo, con interventi minimi di preprocessing.

I dataset risultanti vengono quindi utilizzati come base per:
- l’ingestione in MongoDB
- la progettazione delle collection
- le query e analisi successive

## Schema MongoDB

Lo schema del database MongoDB è stato progettato a partire dai dataset preprocessati, con l’obiettivo di rappresentare in modo chiaro le entità principali del dominio musicale.

Il database `music_archive` è composto da 5 collection principali:
- `artists`
- `genres_tags`
- `tracks`
- `listeners`
- `listening_history`

La progettazione utilizza principalmente riferimenti tramite `ObjectId` tra le collection, mentre le `audio_features` sono modellate come oggetto embedded all’interno dei documenti della collection `tracks`.

La documentazione completa dello schema, con descrizione delle collection, campi, relazioni e scelte di modellazione, è disponibile in:

[`mongodb/README.md`](mongodb/README.md)

## Data Ingestion

L’ingestione dei dati in MongoDB viene eseguita tramite uno script Python dedicato, che legge i dataset preprocessati e popola il database secondo lo schema definito.

Lo script crea e popola le collection nel seguente ordine:
1. `artists`
2. `genres_tags`
3. `tracks`
4. `listeners`
5. `listening_history`

Questo ordine rispetta le dipendenze tra documenti, poiché `tracks` referenzia `artists` e `genres_tags`, mentre `listening_history` referenzia `listeners` e `tracks`.

La documentazione completa della procedura di ingestione, con comandi di esecuzione, verifica delle collection, controllo dei riferimenti e indici creati, è disponibile in:

[`mongodb/ingestion/README.md`](mongodb/ingestion/README.md)

## Data Validation

Il progetto include uno script per verificare l’integrità dei documenti e dei riferimenti tra le collection MongoDB.

Per eseguire la validazione:

```bash
python mongodb/scripts/validate_database.py
```

Lo script controlla:

- validità dei riferimenti tra `tracks`, `artists` e `genres_tags`;
- validità dei riferimenti tra `listening_history`, `tracks` e `listeners`;
- presenza dei campi obbligatori;
- eventuali identificativi logici duplicati;
- struttura del campo embedded `audio_features`;
- eventuali coppie duplicate `listener_id` e `track_id`.

I risultati vengono salvati nel file:

```text
docs/mongodb-validation-results.json
```

Lo script esegue esclusivamente operazioni di lettura e non modifica i dati presenti nel database.

## Requisiti
- Python 3.12
- MongoDB 8.0

Eseguire questo comando per scaricare i pacchetti di python necessari
```bash 
pip install -r requirements.txt
```