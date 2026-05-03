# MongoDB Data Ingestion

Questa sezione descrive la procedura di ingestione dei dataset preprocessati all’interno di MongoDB per il progetto **Music Archive NoSQL**.

L’ingestione popola il database `music_archive` seguendo lo schema definito nella documentazione MongoDB e crea le 5 collection principali:

- `artists`
- `genres_tags`
- `tracks`
- `listeners`
- `listening_history`

---

## Dataset utilizzati

Lo script di ingestione utilizza i dataset preprocessati:

- `data/processed/music_info_cleaned.csv`
- `data/processed/listening_history_cleaned.csv`

Il dataset `music_info_cleaned.csv` viene utilizzato per popolare:

- `artists`
- `genres_tags`
- `tracks`

Il dataset `listening_history_cleaned.csv` viene utilizzato per popolare:

- `listeners`
- `listening_history`

---

## Ordine di ingestione

L’ordine di popolamento delle collection segue le dipendenze tra i documenti:

1. `artists`
2. `genres_tags`
3. `tracks`
4. `listeners`
5. `listening_history`

Questo ordine è necessario perché:

- `tracks` contiene riferimenti a `artists` e `genres_tags`
- `listening_history` contiene riferimenti a `listeners` e `tracks`

---
<!--
## Avvio di MongoDB con Docker

Per avviare MongoDB tramite Docker:

```bash
docker run -d \
  --name music-archive-mongodb \
  -p 27017:27017 \
  -v music_archive_mongo_data:/data/db \
  mongo:8.0
```

Il database sarà disponibile su:

```text
mongodb://localhost:27017/
```

---
-->
## Esecuzione dello script di ingestione

Lo script principale si trova in:

```text
mongodb-schema/ingestion.py
```

Per eseguire l’ingestione:

```bash
python mongodb/mongodb-ingestion.py --drop
```

L’opzione `--drop` elimina le collection esistenti del progetto prima di reinserire i dati.  
È utile in fase di sviluppo per ottenere un caricamento pulito e replicabile.

In alternativa, è possibile specificare manualmente i path dei dataset:

```bash
python scripts/ingest_mongodb.py \
  --music-info data/processed/music_info_cleaned.csv \
  --listening-history data/processed/listening_history_cleaned.csv \
  --drop
```

---

## Collection create

Al termine dell’ingestione, il database `music_archive` contiene le seguenti collection:

```text
artists
genres_tags
listeners
listening_history
tracks
```

È possibile verificarle da `mongosh` con:

```javascript
show dbs
use music_archive
show collections
```

---

## Verifica dei documenti inseriti

Per controllare il numero di documenti presenti in ogni collection:

```javascript
print("artists:", db.artists.countDocuments())
print("genres_tags:", db.genres_tags.countDocuments())
print("tracks:", db.tracks.countDocuments())
print("listeners:", db.listeners.countDocuments())
print("listening_history:", db.listening_history.countDocuments())
```

---

## Verifica della struttura dei documenti

Esempio di verifica su `artists`:

```javascript
db.artists.findOne()
```

Esempio di verifica su `tracks`:

```javascript
db.tracks.findOne()
```

Un documento della collection `tracks` contiene:

- identificativo originale `track_id`
- titolo del brano
- riferimento all’artista tramite `artist_id`
- riferimento a genere/tag tramite `genre_tag_id`
- informazioni Spotify
- anno e durata
- campo `has_audio_features`
- oggetto embedded `audio_features`

---

## Verifica dei riferimenti

Per controllare che non siano presenti riferimenti nulli nelle relazioni principali:

```javascript
db.tracks.countDocuments({ artist_id: null })
db.tracks.countDocuments({ genre_tag_id: null })
db.listening_history.countDocuments({ listener_id: null })
db.listening_history.countDocuments({ track_id: null })
```

Output ottenuto:

```text
db.tracks.countDocuments({ artist_id: null })              -> 0
db.tracks.countDocuments({ genre_tag_id: null })           -> 0
db.listening_history.countDocuments({ listener_id: null }) -> 0
db.listening_history.countDocuments({ track_id: null })    -> 0
```

Questo conferma che i riferimenti principali tra le collection sono stati creati correttamente.

---

## Verifica degli indici

Per controllare gli indici creati:

```javascript
db.artists.getIndexes()
db.genres_tags.getIndexes()
db.listeners.getIndexes()
db.tracks.getIndexes()
db.listening_history.getIndexes()
```

Gli indici principali creati sono:

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

Gli indici unici impediscono la duplicazione logica di artisti, listener, tracce e coppie listener-traccia nella cronologia degli ascolti.

---

## Verifica dei collegamenti tra collection

Per verificare che una traccia sia collegata correttamente al proprio artista:

```javascript
db.tracks.aggregate([
  { $match: { name: "Mr. Brightside" } },
  {
    $lookup: {
      from: "artists",
      localField: "artist_id",
      foreignField: "_id",
      as: "artist"
    }
  },
  {
    $project: {
      _id: 0,
      name: 1,
      track_id: 1,
      artist: "$artist.name"
    }
  }
]).pretty()
```

Per verificare quali tracce sono associate a un artista:

```javascript
db.artists.aggregate([
  { $match: { name: "!!!" } },
  {
    $lookup: {
      from: "tracks",
      localField: "_id",
      foreignField: "artist_id",
      as: "tracks"
    }
  },
  { $unwind: "$tracks" },
  {
    $project: {
      _id: 0,
      artist: "$name",
      track_name: "$tracks.name",
      track_id: "$tracks.track_id",
      year: "$tracks.year"
    }
  }
]).pretty()
```

---

## Note

- Lo script popola MongoDB rispettando lo schema definito nella Issue 3.
- Le collection vengono collegate tramite riferimenti `ObjectId`.
- Le `audio_features` sono salvate come oggetto embedded dentro `tracks`.
- I listener rappresentano utenti già presenti nel dataset e non account registrati.
- Non vengono versionati dump MongoDB, volumi Docker o dati generati localmente.
- Il volume Docker contiene i dati del database solo in ambiente locale.