# MongoDB Data Ingestion

Questa sezione descrive la procedura di ingestione dei dataset preprocessati all’interno di MongoDB per il progetto **Music Archive NoSQL**.

L’ingestione popola il database:

```text
music_archive
```

seguendo lo schema definito nella documentazione MongoDB.

## Dataset utilizzati

Lo script di ingestione utilizza i dataset preprocessati presenti nella cartella `dataset/`:

```text
dataset/music_info_cleaned.csv
dataset/listening_history_cleaned.csv
```

Il dataset `music_info_cleaned.csv` viene utilizzato per popolare:

- `artists`;
- `genres_tags`;
- `tracks`.

Il dataset `listening_history_cleaned.csv` viene utilizzato per popolare:

- `listeners`;
- `listening_history`.

## Collection create

L’ingestione crea e popola le seguenti collection:

- `artists`;
- `genres_tags`;
- `tracks`;
- `listeners`;
- `listening_history`.

## Ordine di ingestione

L’ordine di popolamento segue le dipendenze tra i documenti:

```text
1. artists
2. genres_tags
3. tracks
4. listeners
5. listening_history
```

Questo ordine è necessario perché:

- `tracks` contiene riferimenti a `artists` e `genres_tags`;
- `listening_history` contiene riferimenti a `listeners` e `tracks`.

## Script di ingestione

Lo script principale si trova in:

```text
mongodb/ingestion/mongodb-ingestion.py
```

## Esecuzione manuale

Dalla root del progetto:

```bash
python mongodb/ingestion/mongodb-ingestion.py --drop
```

L’opzione `--drop` elimina le collection esistenti del progetto prima di reinserire i dati.

Questo è utile in fase di sviluppo per ottenere un caricamento pulito e replicabile.

## Esecuzione con path espliciti

È possibile specificare manualmente i path dei dataset:

```bash
python mongodb/ingestion/mongodb-ingestion.py \
  --music-info dataset/music_info_cleaned.csv \
  --listening-history dataset/listening_history_cleaned.csv \
  --drop
```

## Esecuzione con Docker

Se il progetto è avviato tramite Docker Compose:

```bash
docker compose exec web python mongodb/ingestion/mongodb-ingestion.py --drop
```

Con path espliciti:

```bash
docker compose exec web python mongodb/ingestion/mongodb-ingestion.py \
  --music-info dataset/music_info_cleaned.csv \
  --listening-history dataset/listening_history_cleaned.csv \
  --drop
```

## Configurazione MongoDB

Lo script utilizza le variabili d’ambiente:

```text
MONGO_URI
MONGO_DB_NAME
```

Esempio per esecuzione locale:

```env
MONGO_URI=mongodb://localhost:27017/
MONGO_DB_NAME=music_archive
```

Esempio per esecuzione tramite Docker:

```env
MONGO_URI=mongodb://mongo:27017/
MONGO_DB_NAME=music_archive
```

## Verifica delle collection

Dopo l’ingestione è possibile verificare le collection da `mongosh`:

```javascript
use music_archive
show collections
```

Output atteso:

```text
artists
genres_tags
listeners
listening_history
tracks
```

## Verifica dei documenti inseriti

Per controllare il numero di documenti presenti:

```javascript
print("artists:", db.artists.countDocuments())
print("genres_tags:", db.genres_tags.countDocuments())
print("tracks:", db.tracks.countDocuments())
print("listeners:", db.listeners.countDocuments())
print("listening_history:", db.listening_history.countDocuments())
```

## Verifica della struttura dei documenti

Esempio su `artists`:

```javascript
db.artists.findOne()
```

Esempio su `tracks`:

```javascript
db.tracks.findOne()
```

Un documento della collection `tracks` contiene:

- identificativo originale `track_id`;
- titolo del brano;
- riferimento all’artista tramite `artist_id`;
- riferimento a genere/tag tramite `genre_tag_id`;
- informazioni Spotify, quando disponibili;
- anno e durata;
- campo `has_audio_features`;
- oggetto embedded `audio_features`.

## Verifica dei riferimenti

Per controllare che non siano presenti riferimenti nulli nelle relazioni principali:

```javascript
db.tracks.countDocuments({ artist_id: null })
db.tracks.countDocuments({ genre_tag_id: null })
db.listening_history.countDocuments({ listener_id: null })
db.listening_history.countDocuments({ track_id: null })
```

Output atteso:

```text
0
0
0
0
```

## Verifica degli indici

Per controllare gli indici creati:

```javascript
db.artists.getIndexes()
db.genres_tags.getIndexes()
db.listeners.getIndexes()
db.tracks.getIndexes()
db.listening_history.getIndexes()
```

Indici principali:

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
  { $match: { name: "Coldplay" } },
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

## Note

- Lo script popola MongoDB rispettando lo schema definito.
- Le collection vengono collegate tramite riferimenti `ObjectId`.
- Le `audio_features` sono salvate come oggetto embedded dentro `tracks`.
- I listener rappresentano utenti già presenti nel dataset e non account registrati.
- L’opzione `--drop` elimina e ricrea i dati del progetto.
- Non vengono versionati dump MongoDB, volumi Docker o dati generati localmente.
