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
- la progettazione delle collezioni
- le query e analisi successive

## Requisiti
- Python 3.12
- MongoDB 8.0