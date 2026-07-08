# MongoDB Schema Design

Questo documento descrive lo schema MongoDB progettato per il progetto **Music Archive NoSQL**.

Lo schema parte dai dataset preprocessati:

```text
dataset/music_info_cleaned.csv
dataset/listening_history_cleaned.csv
```

L’obiettivo è definire una struttura dati chiara, coerente e adatta a supportare:

- ingestione dei dati;
- operazioni CRUD;
- aggregation pipeline;
- benchmark;
- validazione dei riferimenti;
- dashboard web;
- dashboard amministratore.

## Database

Il database utilizzato dal progetto è:

```text
music_archive
```

Il database contiene cinque collection principali:

- `artists`;
- `genres_tags`;
- `tracks`;
- `listeners`;
- `listening_history`.

## Panoramica delle relazioni

Le relazioni principali sono:

```text
tracks.artist_id              -> artists._id
tracks.genre_tag_id           -> genres_tags._id
listening_history.listener_id -> listeners._id
listening_history.track_id    -> tracks._id
```

Schema logico semplificato:

```text
artists
   ↑
   |
tracks
   |
   ↓
genres_tags


listeners
   ↑
   |
listening_history
   |
   ↓
tracks
```

## Collection `artists`

La collection `artists` rappresenta gli artisti associati ai brani presenti nel catalogo.

Ogni documento rappresenta un artista e può essere referenziato da una o più tracce.

### Struttura

```json
{
  "_id": "ObjectId",
  "name": "string"
}
```

### Campi

| Campo | Tipo | Descrizione |
|---|---|---|
| `_id` | ObjectId | Identificativo generato da MongoDB |
| `name` | string | Nome dell’artista |

### Relazione

```text
artists._id -> tracks.artist_id
```

### Motivazione

Gli artisti sono modellati in una collection separata per evitare duplicazione del nome dell’artista in più tracce e per facilitare query come:

- tracce di un artista;
- numero di tracce per artista;
- artisti più ascoltati.

Durante la dashboard amministratore, quando viene inserita o modificata una traccia, il sistema cerca se l’artista esiste già. Se esiste, lo riutilizza; altrimenti crea un nuovo documento nella collection `artists`.

## Collection `genres_tags`

La collection `genres_tags` rappresenta la classificazione musicale delle tracce.

Ogni documento contiene un genere principale e una lista opzionale di tag.

### Struttura

```json
{
  "_id": "ObjectId",
  "genre": "string",
  "tags": ["string"]
}
```

### Campi

| Campo | Tipo | Descrizione |
|---|---|---|
| `_id` | ObjectId | Identificativo generato da MongoDB |
| `genre` | string | Genere principale |
| `tags` | array | Tag musicali associati |

### Relazione

```text
genres_tags._id -> tracks.genre_tag_id
```

### Motivazione

La separazione di `genres_tags` consente di:

- mantenere puliti i documenti `tracks`;
- centralizzare le informazioni di classificazione;
- supportare filtri per genere e tag;
- supportare aggregazioni sui generi più ascoltati.

Durante l’inserimento o la modifica di una traccia dalla dashboard amministratore, il sistema cerca una combinazione compatibile di genere e tag. Se esiste, la riutilizza; altrimenti crea un nuovo documento.

## Collection `tracks`

La collection `tracks` rappresenta il catalogo dei brani musicali.

Ogni documento corrisponde a una traccia.

### Struttura

```json
{
  "_id": "ObjectId",
  "track_id": "string",
  "name": "string",
  "artist_id": "ObjectId",
  "genre_tag_id": "ObjectId",
  "spotify_id": "string",
  "year": "number",
  "duration_ms": "number",
  "has_audio_features": "boolean",
  "audio_features": {
    "danceability": "number",
    "energy": "number",
    "key": "number",
    "loudness": "number",
    "mode": "number",
    "speechiness": "number",
    "acousticness": "number",
    "instrumentalness": "number",
    "liveness": "number",
    "valence": "number",
    "tempo": "number",
    "time_signature": "number"
  }
}
```

La dashboard amministratore può aggiungere anche campi opzionali come:

```json
{
  "album_name": "string",
  "album_release_date": "string",
  "album_image_url": "string",
  "created_by": "admin_dashboard",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Campi principali

| Campo | Tipo | Descrizione |
|---|---|---|
| `_id` | ObjectId | Identificativo generato da MongoDB |
| `track_id` | string | Identificativo logico della traccia |
| `name` | string | Titolo del brano |
| `artist_id` | ObjectId | Riferimento all’artista |
| `genre_tag_id` | ObjectId | Riferimento a genere/tag |
| `spotify_id` | string | Identificativo Spotify |
| `year` | number | Anno associato alla traccia |
| `duration_ms` | number | Durata in millisecondi |
| `has_audio_features` | boolean | Indica se le audio features sono disponibili |
| `audio_features` | object | Feature audio embedded |

### Relazioni

```text
tracks.artist_id    -> artists._id
tracks.genre_tag_id -> genres_tags._id
```

La collection `tracks` è inoltre referenziata da:

```text
listening_history.track_id -> tracks._id
```

### Motivazione

`tracks` è la collection centrale del dominio.

È stata modellata con riferimenti verso `artists` e `genres_tags` per evitare duplicazione e mantenere separate le entità principali.

Le `audio_features` sono invece embedded perché appartengono direttamente alla traccia e vengono normalmente lette insieme al brano.

## Collection `listeners`

La collection `listeners` rappresenta gli utenti/listener presenti nel dataset della cronologia di ascolto.

Questi listener non sono utenti registrati alla piattaforma e non prevedono autenticazione.

### Struttura

```json
{
  "_id": "ObjectId",
  "original_user_id": "string"
}
```

### Campi

| Campo | Tipo | Descrizione |
|---|---|---|
| `_id` | ObjectId | Identificativo generato da MongoDB |
| `original_user_id` | string | Identificativo originale del listener nel dataset |

### Relazione

```text
listeners._id -> listening_history.listener_id
```

### Motivazione

I listener sono modellati separatamente per evitare duplicazioni nella cronologia degli ascolti.

La dashboard amministratore permette di cercare un listener esistente e collegarlo a una traccia tramite un nuovo ascolto.

## Collection `listening_history`

La collection `listening_history` rappresenta la cronologia degli ascolti.

Ogni documento collega un listener a una traccia.

### Struttura

```json
{
  "_id": "ObjectId",
  "listener_id": "ObjectId",
  "track_id": "ObjectId",
  "playcount": "number"
}
```

I documenti creati dalla dashboard amministratore possono contenere anche:

```json
{
  "created_by": "admin_dashboard",
  "created_at": "datetime"
}
```

### Campi

| Campo | Tipo | Descrizione |
|---|---|---|
| `_id` | ObjectId | Identificativo generato da MongoDB |
| `listener_id` | ObjectId | Riferimento al listener |
| `track_id` | ObjectId | Riferimento alla traccia |
| `playcount` | number | Numero di ascolti, quando disponibile |

### Relazioni

```text
listening_history.listener_id -> listeners._id
listening_history.track_id    -> tracks._id
```

### Motivazione

La cronologia degli ascolti può contenere molti documenti. Per questo viene modellata tramite referencing, evitando di duplicare dentro ogni ascolto informazioni come:

- titolo della traccia;
- artista;
- genere;
- tag;
- audio features.

Queste informazioni restano disponibili tramite il riferimento alla collection `tracks`.

## Embedding vs Referencing

### Referencing

Viene usato il referencing per collegare:

- `tracks` e `artists`;
- `tracks` e `genres_tags`;
- `listening_history` e `listeners`;
- `listening_history` e `tracks`.

Questa scelta è motivata dal fatto che queste entità possono essere condivise da molti documenti.

### Embedding

Viene usato l’embedding per:

```text
tracks.audio_features
```

Le audio features sono proprietà della singola traccia e vengono generalmente lette insieme al documento del brano.

## Indici principali

Gli indici principali creati durante l’ingestione sono:

```text
artists.name                                  unique
genres_tags.genre + tags_key                  unique
listeners.original_user_id                    unique
tracks.track_id                               unique
tracks.artist_id                              index
tracks.genre_tag_id                           index
listening_history.listener_id + track_id      unique
listening_history.track_id                    index
```

Gli indici servono a:

- evitare duplicazioni logiche;
- velocizzare ricerche e aggregazioni;
- garantire che la stessa coppia listener-traccia non venga registrata più volte.

## Cancellazione controllata delle tracce

La dashboard amministratore consente di eliminare una traccia solo se non esistono documenti collegati in `listening_history`.

Se una traccia è già presente nella cronologia degli ascolti, la cancellazione viene bloccata per preservare l’integrità dei riferimenti e non perdere dati storici.

## Ordine di ingestione

L’ordine corretto di popolamento delle collection è:

```text
1. artists
2. genres_tags
3. tracks
4. listeners
5. listening_history
```

Questo ordine è necessario perché:

- `tracks` richiede riferimenti a `artists` e `genres_tags`;
- `listening_history` richiede riferimenti a `listeners` e `tracks`.

## Documentazione collegata

- Ingestione dati: `ingestion/README.md`
- Script MongoDB: `scripts/README.md`
- Web app Flask: `webapp/README.md`
