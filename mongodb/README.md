# MongoDB Schema Design

Questo documento descrive lo schema MongoDB progettato per il progetto **Music Archive NoSQL**.

Lo schema parte dai dataset già analizzati e preprocessati nelle issue precedenti:

- `music_info_cleaned.csv`
- `listening_history.csv` preprocessato

L’obiettivo è definire una struttura dati chiara, coerente e adatta alle future fasi di:

- ingestione in MongoDB
- query CRUD
- aggregazioni
- ricerca e filtro nella web app
- analisi della cronologia di ascolto

Il database sarà composto da 5 collection principali:

- `artists`
- `genres_tags`
- `tracks`
- `listeners`
- `listening_history`

---

## Dataset di partenza

### `music_info_cleaned.csv`

Il dataset contiene le informazioni principali sui brani musicali.

Campi principali utilizzati:

- `track_id`
- `name`
- `artist`
- `spotify_id`
- `tags`
- `genre`
- `year`
- `duration_ms`
- `danceability`
- `energy`
- `key`
- `loudness`
- `mode`
- `speechiness`
- `acousticness`
- `instrumentalness`
- `liveness`
- `valence`
- `tempo`
- `time_signature`
- `has_audio_features`

Campi esclusi dallo schema applicativo:

- `genre_source`
- `spotify_preview_url`

Il campo `genre_source` viene escluso perché rappresenta un’informazione tecnica prodotta durante il preprocessing.  
Il campo `spotify_preview_url` viene ignorato per ora perché non è necessario per le funzionalità iniziali del progetto.

### `listening_history.csv`

Il dataset contiene la cronologia degli ascolti degli utenti/listener.

Campi principali utilizzati:

- `user_id`
- `track_id`
- `playcount`

Il campo `user_id` verrà usato per generare i documenti della collection `listeners`.  
Il campo `track_id` verrà usato per collegare gli ascolti ai brani presenti nella collection `tracks`.

---

## Collections

## `artists`

La collection `artists` rappresenta gli artisti associati ai brani presenti nel dataset.

Gli artisti vengono estratti come valori unici dalla colonna `artist` del dataset `music_info_cleaned.csv`.

Ogni documento rappresenta un singolo artista e può essere referenziato da una o più tracce nella collection `tracks`.

### Struttura del documento

```json
{
  "_id": "ObjectId",
  "name": "string"
}
```

### Campi

| Campo | Tipo | Descrizione |
|---|---|---|
| `_id` | ObjectId | Identificativo generato automaticamente da MongoDB |
| `name` | string | Nome dell’artista estratto dal dataset |

### Esempio

```json
{
  "_id": "ObjectId('...')",
  "name": "Coldplay"
}
```

### Relazioni

```text
artists._id -> tracks.artist_id
```

Ogni artista può essere associato a più tracce, mentre ogni traccia fa riferimento a un artista principale.

### Motivazione progettuale

È stata scelta una collection separata per gli artisti per evitare la duplicazione del nome dell’artista in più documenti `tracks` e per facilitare query e aggregazioni future, come:

- ricerca dei brani di un artista
- conteggio delle tracce per artista
- calcolo degli artisti più ascoltati tramite `listening_history`

Durante la futura fase di ingestione, la collection `artists` dovrà essere popolata prima della collection `tracks`, poiché ogni traccia contiene un riferimento `artist_id` verso un documento della collection `artists`.

---

## `genres_tags`

La collection `genres_tags` rappresenta la classificazione musicale dei brani.

Nel preprocessing è stato scelto di utilizzare `genre` come label principale del brano, mentre `tags` viene mantenuto come informazione opzionale e aggiuntiva.

Ogni documento rappresenta una combinazione di genere e tag associabile a una o più tracce.

### Struttura del documento

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
| `_id` | ObjectId | Identificativo generato automaticamente da MongoDB |
| `genre` | string | Genere principale associato al brano |
| `tags` | array di stringhe | Lista opzionale di tag musicali associati al brano |

### Esempio

```json
{
  "_id": "ObjectId('...')",
  "genre": "rock",
  "tags": [
    "alternative rock",
    "indie rock",
    "britpop"
  ]
}
```

### Relazioni

```text
genres_tags._id -> tracks.genre_tag_id
```

Ogni documento `tracks` può fare riferimento a un documento della collection `genres_tags`.

### Motivazione progettuale

La collection `genres_tags` permette di separare la classificazione musicale dal documento principale della traccia.

Questa scelta consente di:

- mantenere `tracks` più pulita
- centralizzare le informazioni di classificazione musicale
- supportare filtri per genere e tag
- supportare future aggregazioni sui generi più ascoltati
- mantenere separato il campo `genre` dai `tags`, pur trattandoli come informazioni collegate

Il campo `genre_source` non viene incluso perché rappresenta un campo tecnico del preprocessing e non è necessario per le funzionalità applicative.

---

## `tracks`

La collection `tracks` rappresenta il catalogo dei brani musicali.

Ogni documento corrisponde a una traccia del dataset `music_info_cleaned.csv`.

La collection contiene i dati principali del brano, i riferimenti ad artista e classificazione musicale, e le feature audio incorporate come oggetto embedded.

### Struttura del documento

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

### Campi

| Campo | Tipo | Descrizione |
|---|---|---|
| `_id` | ObjectId | Identificativo generato automaticamente da MongoDB |
| `track_id` | string | Identificativo originale della traccia nel dataset |
| `name` | string | Titolo del brano |
| `artist_id` | ObjectId | Riferimento al documento dell’artista nella collection `artists` |
| `genre_tag_id` | ObjectId | Riferimento al documento nella collection `genres_tags` |
| `spotify_id` | string | Identificativo Spotify del brano |
| `year` | number | Anno associato al brano |
| `duration_ms` | number | Durata del brano in millisecondi |
| `has_audio_features` | boolean | Indica se le feature audio sono disponibili e valide |
| `audio_features` | object | Oggetto embedded contenente le feature audio del brano |

### Audio features

Le feature audio vengono modellate come oggetto embedded all’interno del documento `tracks`.

Campi inclusi in `audio_features`:

- `danceability`
- `energy`
- `key`
- `loudness`
- `mode`
- `speechiness`
- `acousticness`
- `instrumentalness`
- `liveness`
- `valence`
- `tempo`
- `time_signature`

### Esempio

```json
{
  "_id": "ObjectId('...')",
  "track_id": "TRIOREW128F424EAF0",
  "name": "Mr. Brightside",
  "artist_id": "ObjectId('...')",
  "genre_tag_id": "ObjectId('...')",
  "spotify_id": "09ZQ5TmUG8TSL56n0knqrj",
  "year": 2004,
  "duration_ms": 222200,
  "has_audio_features": true,
  "audio_features": {
    "danceability": 0.355,
    "energy": 0.918,
    "key": 1,
    "loudness": -4.36,
    "mode": 1,
    "speechiness": 0.0746,
    "acousticness": 0.00119,
    "instrumentalness": 0.0,
    "liveness": 0.0971,
    "valence": 0.24,
    "tempo": 148.114,
    "time_signature": 4
  }
}
```

### Relazioni

```text
tracks.artist_id -> artists._id
tracks.genre_tag_id -> genres_tags._id
```

La collection `tracks` è inoltre referenziata dalla collection `listening_history`:

```text
listening_history.track_id -> tracks._id
```

### Campi esclusi

I seguenti campi del dataset non vengono salvati direttamente in `tracks`:

| Campo | Motivazione |
|---|---|
| `artist` | Spostato nella collection `artists` e referenziato tramite `artist_id` |
| `genre` | Gestito nella collection `genres_tags` |
| `tags` | Gestiti nella collection `genres_tags` |
| `genre_source` | Campo tecnico del preprocessing, non necessario nello schema applicativo |
| `spotify_preview_url` | Ignorato per ora perché non necessario nelle funzionalità iniziali |

### Motivazione progettuale

La collection `tracks` rappresenta l’entità centrale del catalogo musicale.

È stata scelta una struttura con riferimenti verso `artists` e `genres_tags` per evitare duplicazioni e mantenere separati i concetti principali del dominio.

Le feature audio sono invece embedded perché appartengono direttamente alla traccia e vengono normalmente lette insieme al documento del brano.  
Non è quindi necessario creare una collection separata per le audio features.

---

## `listeners`

La collection `listeners` rappresenta gli utenti/listener presenti nel dataset `listening_history`.

Questi listener non sono utenti registrati alla piattaforma e non prevedono autenticazione, email o password.

Ogni documento rappresenta un listener estratto dai valori unici della colonna `user_id`.

### Struttura del documento

```json
{
  "_id": "ObjectId",
  "original_user_id": "string"
}
```

### Campi

| Campo | Tipo | Descrizione |
|---|---|---|
| `_id` | ObjectId | Identificativo generato automaticamente da MongoDB |
| `original_user_id` | string | Identificativo originale del listener nel dataset |

### Esempio

```json
{
  "_id": "ObjectId('...')",
  "original_user_id": "00000c289a1829a808ac09c00daf10bc3c4e223b"
}
```

### Relazioni

```text
listeners._id -> listening_history.listener_id
```

Ogni listener può essere associato a più record nella collection `listening_history`.

### Motivazione progettuale

La collection `listeners` consente di rappresentare separatamente gli utenti presenti nel dataset senza introdurre un sistema di autenticazione.

Nella web app i listener potranno essere mostrati con un’etichetta generica, ad esempio:

```text
Listener #1
Listener #2
Listener #3
```

senza salvare necessariamente un campo `display_name` nel database.

Questa scelta mantiene il modello semplice e coerente con il dataset originale, evitando la creazione artificiale di account utente.

---

## `listening_history`

La collection `listening_history` rappresenta la cronologia degli ascolti.

Ogni documento collega un listener a una traccia e conserva il numero di ascolti tramite il campo `playcount`.

### Struttura del documento

```json
{
  "_id": "ObjectId",
  "listener_id": "ObjectId",
  "track_id": "ObjectId",
  "playcount": "number"
}
```

### Campi

| Campo | Tipo | Descrizione |
|---|---|---|
| `_id` | ObjectId | Identificativo generato automaticamente da MongoDB |
| `listener_id` | ObjectId | Riferimento al listener nella collection `listeners` |
| `track_id` | ObjectId | Riferimento alla traccia nella collection `tracks` |
| `playcount` | number | Numero di ascolti della traccia da parte del listener |

### Esempio

```json
{
  "_id": "ObjectId('...')",
  "listener_id": "ObjectId('...')",
  "track_id": "ObjectId('...')",
  "playcount": 7
}
```

### Relazioni

```text
listening_history.listener_id -> listeners._id
listening_history.track_id -> tracks._id
```

### Motivazione progettuale

La collection `listening_history` può contenere un numero elevato di documenti.  
Per questo motivo viene modellata tramite referencing, evitando di duplicare all’interno di ogni ascolto informazioni come:

- titolo del brano
- artista
- genere
- tag
- feature audio

Questi dati restano disponibili tramite il riferimento alla collection `tracks`.

Questa scelta consente di supportare query e aggregazioni come:

- brani più ascoltati
- artisti più ascoltati
- generi più ascoltati
- cronologia di un listener
- numero totale di ascolti per listener
- ascolti aggregati per traccia

---

## Relazioni complessive

Le relazioni principali tra le collection sono:

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

---

## Embedding vs Referencing

### Referencing

Viene utilizzato il referencing per collegare:

- `tracks` e `artists`
- `tracks` e `genres_tags`
- `listening_history` e `listeners`
- `listening_history` e `tracks`

Questa scelta è motivata dal fatto che queste entità possono essere condivise da molti documenti.

Ad esempio:

- un artista può avere più tracce
- un genere/tag può essere associato a più tracce
- un listener può avere molti ascolti
- una traccia può comparire in molti record di ascolto

Il referencing evita duplicazioni e rende più semplice mantenere consistenti le informazioni principali.

### Embedding

Viene utilizzato l’embedding per il campo:

```text
tracks.audio_features
```

Le feature audio sono proprietà direttamente associate a una singola traccia e vengono generalmente lette insieme al brano.

Per questo motivo non viene creata una collection separata per le audio features.

---

## Ordine previsto di ingestione

Durante la futura fase di ingestione, le collection dovranno essere popolate seguendo un ordine coerente con le dipendenze tra documenti.

Ordine consigliato:

```text
1. artists
2. genres_tags
3. tracks
4. listeners
5. listening_history
```

Motivazione:

- `tracks` richiede i riferimenti `artist_id` e `genre_tag_id`
- `listening_history` richiede i riferimenti `listener_id` e `track_id`

Quindi, prima di inserire le tracce, devono esistere artisti e generi/tag.  
Prima di inserire la cronologia degli ascolti, devono esistere listener e tracce.

---

## Note progettuali

Lo schema è pensato per supportare le funzionalità principali del progetto **Music Archive NoSQL**:

- esplorazione del catalogo musicale
- ricerca per titolo, artista, genere e tag
- consultazione dei listener del dataset
- analisi della cronologia di ascolto
- aggregazioni su tracce, artisti e generi
- futura integrazione con una web app

La progettazione evita di introdurre autenticazione o registrazione utenti, poiché i listener rappresentano esclusivamente utenti già presenti nel dataset.

Lo schema mantiene inoltre separati i concetti principali del dominio musicale, riducendo duplicazioni e preparando il database alle successive fasi di ingestione, query e benchmark.