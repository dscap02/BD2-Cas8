## Operazioni CRUD MongoDB

Il progetto include uno script dedicato alla verifica delle principali operazioni CRUD sulle collection MongoDB principali:

- `tracks`
- `artists`
- `listeners`
- `genres_tags`

La collection `listening_history` viene gestita in modo non distruttivo, poiché rappresenta dati storici di ascolto.

Lo script utilizza esclusivamente documenti di test riconoscibili tramite il campo:

```python
test_marker = "crud_test"
```
In questo modo le operazioni di creazione, aggiornamento e cancellazione non alterano i dati reali provenienti dai dataset preprocessati.
Per eseguire lo script:

```bash
python scripts/crud_operations.py
```
Lo script esegue:
- lettura di documenti esistenti;
- inserimento controllato di documenti di test;
- aggiornamento dei documenti di test;
- cancellazione dei documenti di test;
- verifica finale dell’assenza di documenti di test residui.
