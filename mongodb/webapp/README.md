# Music Archive Web App

Questa cartella contiene la web app Flask del progetto **Music Archive NoSQL**.

La web app permette di esplorare il database MongoDB `music_archive` tramite interfaccia grafica e include:

- dashboard utente;
- ricerca e filtro delle tracce;
- pagine dettaglio per tracce e artisti;
- dashboard amministratore;
- operazioni CRUD controllate;
- registrazione di nuovi ascolti;
- integrazione opzionale con Spotify.

## Struttura

```text
mongodb/webapp/
├── admin_service.py
├── app.py
├── data/
│   └── dashboard_cache.json
├── requirements.txt
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── admin.js
└── templates/
    ├── admin.html
    ├── admin_listening.html
    ├── admin_track_form.html
    ├── artist_detail.html
    ├── artists.html
    ├── base.html
    ├── index.html
    ├── track_detail.html
    └── tracks.html
```

## Dashboard utente

La dashboard principale è disponibile su:

```text
/
```

Permette di visualizzare:

- conteggi delle collection principali;
- tracce più ascoltate;
- artisti più ascoltati;
- generi più ascoltati;
- listener più attivi.

Le statistiche principali vengono lette da una cache pre-calcolata:

```text
mongodb/webapp/data/dashboard_cache.json
```

La cache viene generata tramite:

```bash
python mongodb/scripts/generate_dashboard_cache.py
```

## Ricerca tracce

La pagina tracce è disponibile su:

```text
/tracks
```

Permette di:

- cercare tracce per titolo;
- filtrare per genere;
- filtrare per anno;
- filtrare per tag;
- combinare più filtri;
- aprire il dettaglio di una traccia.

## Dettaglio traccia

La pagina di dettaglio traccia mostra:

- titolo;
- artista;
- genere;
- tag;
- anno;
- durata;
- audio features;
- player Spotify embedded, se disponibile;
- link a Spotify Web o all’app Spotify;
- pulsante di modifica per la dashboard amministratore.

Quando la traccia ha uno Spotify ID, la pagina può adattare dinamicamente il colore della navbar usando la copertina recuperata tramite Spotify oEmbed.

## Ricerca artisti

La pagina artisti è disponibile su:

```text
/artists
```

Permette di:

- cercare artisti per nome;
- visualizzare il numero di tracce associate;
- aprire il dettaglio artista.

## Dettaglio artista

La pagina dettaglio artista mostra:

- nome artista;
- numero di tracce associate;
- elenco paginato delle tracce dell’artista;
- link al dettaglio delle singole tracce.

## Dashboard amministratore

La dashboard amministratore è disponibile su:

```text
/admin
```

Permette di:

- visualizzare un riepilogo dei dati principali;
- creare nuove tracce;
- modificare tracce esistenti;
- eliminare tracce in modo sicuro;
- registrare nuovi ascolti;
- selezionare tracce e listener tramite suggerimenti;
- evitare l’inserimento manuale di ObjectId nell’interfaccia.

## CRUD amministrative

La dashboard amministratore implementa CRUD controllate sulla collection `tracks`.

### Create

È possibile creare una nuova traccia tramite form.

Durante la creazione:

- se l’artista esiste già, viene riutilizzato;
- se l’artista non esiste, viene creato;
- se la combinazione genere/tag esiste già, viene riutilizzata;
- se non esiste, viene creata;
- la traccia viene collegata tramite `artist_id` e `genre_tag_id`.

### Read

La lettura avviene tramite:

- dashboard amministratore;
- elenco tracce recenti;
- dettaglio traccia;
- ricerca tracce;
- autocomplete.

### Update

È possibile modificare una traccia esistente tramite form.

I campi modificabili includono:

- titolo;
- artista;
- album;
- genere;
- tag;
- anno;
- durata;
- Spotify ID;
- audio features opzionali.

Durante la modifica vengono mantenuti coerenti i riferimenti verso `artists` e `genres_tags`.

### Delete

È possibile eliminare una traccia solo se non esistono ascolti collegati nella collection `listening_history`.

Se una traccia è già presente nella cronologia degli ascolti, la cancellazione viene bloccata per evitare riferimenti non validi e perdita di dati storici.

## Registrazione ascolti

La dashboard amministratore permette di registrare un nuovo ascolto collegando:

- una traccia esistente;
- un listener esistente.

La selezione avviene tramite campi di ricerca con suggerimenti.

L’interfaccia non richiede l’inserimento manuale di ObjectId.

Il sistema impedisce l’inserimento di duplicati sulla stessa coppia:

```text
listener_id + track_id
```

## Integrazione Spotify

Il form di creazione/modifica traccia supporta l’inserimento assistito tramite link Spotify.

Il sistema prova a estrarre lo Spotify track ID da:

- link traccia Spotify;
- URI Spotify;
- link album con traccia evidenziata;
- ID Spotify diretto.

Esempi supportati:

```text
https://open.spotify.com/track/3JjyzXQ07ODREBhJknQgLS
spotify:track:3JjyzXQ07ODREBhJknQgLS
https://open.spotify.com/intl-it/album/...?...highlight=spotify:track:3JjyzXQ07ODREBhJknQgLS
```

## Spotify Web API opzionale

Se sono configurate credenziali valide:

```env
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
```

la web app prova a usare la Spotify Web API per recuperare metadati più completi:

- titolo;
- artista;
- album;
- anno;
- durata;
- immagine album.

Se le credenziali non sono configurate o la Web API non è disponibile, il sistema usa un fallback tramite Spotify oEmbed.

In ogni caso, l’amministratore può completare manualmente i campi mancanti.

## Configurazione ambiente

La web app legge la configurazione da variabili d’ambiente.

Creare un file `.env` nella root del progetto partendo da:

```bash
cp .env.example .env
```

Variabili principali:

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

Il file `.env` non deve essere committato.

## Installazione manuale

Dalla root del progetto:

```bash
pip install -r mongodb/webapp/requirements.txt
```

## Avvio manuale

Assicurarsi che MongoDB sia attivo e che il database sia popolato.

Generare la cache dashboard:

```bash
python mongodb/scripts/generate_dashboard_cache.py
```

Avviare la web app:

```bash
python mongodb/webapp/app.py
```

La web app sarà disponibile su:

```text
http://127.0.0.1:5000
```

Dashboard amministratore:

```text
http://127.0.0.1:5000/admin
```

## Avvio con Docker

Se il progetto viene avviato tramite Docker Compose:

```bash
docker compose up --build -d
```

La web app sarà disponibile su:

```text
http://127.0.0.1:5050
```

Dashboard amministratore:

```text
http://127.0.0.1:5050/admin
```

## Esecuzione cache con Docker

```bash
docker compose exec web python mongodb/scripts/generate_dashboard_cache.py
```

## Dipendenze

Le dipendenze della web app sono definite in:

```text
mongodb/webapp/requirements.txt
```

Dipendenze principali:

- Flask;
- PyMongo;
- Requests;
- Pillow;
- python-dotenv.

## Note

- La dashboard utente esegue principalmente operazioni di lettura.
- La dashboard amministratore esegue operazioni controllate.
- La cancellazione delle tracce è protetta.
- Le credenziali Spotify sono opzionali.
- L’applicazione resta utilizzabile anche senza Spotify Web API.
- La cache della dashboard deve essere rigenerata dopo modifiche rilevanti ai dati.
