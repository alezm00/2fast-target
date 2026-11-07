# 2Fast Target

Matrice 5×5 di bersagli luminosi a pressione, controllata da un ESP32‑S3 (MicroPython).
Il master crea una **rete WiFi propria** e serve una **pagina web** (telefono o PC) per giocare,
vedere i tempi, configurare e tarare i bersagli. La partita si può avviare dalla pagina, da un
pulsante sul master o da un **telecomando radio** (un piccolo ESP32 con un pulsante).

```
 telefono / PC ──WiFi──► master ESP32‑S3 ◄──ESP‑NOW── telecomando ESP32 (pulsante)
                          │  matrice tasti 5×5 (lettura)
                          └─ matrice LED 5×5 (uscita)
```

## Struttura

| Cartella | Contenuto |
|---|---|
| `master/` | firmware del master: scansione bersagli, LED, giochi, server web, telecomando |
| `master/web/index.html` | interfaccia web (un solo file, nessuna dipendenza da internet) |
| `remote/` | firmware del telecomando radio (ESP32 qualsiasi) |
| `tests/` | test su PC (47) e simulatore del master |
| `firmware/` | MicroPython 1.27 per ESP32 e ESP32‑S3 |

## Installazione

Serve MicroPython (vedi `firmware/`). Con [`mpremote`](https://docs.micropython.org/en/latest/reference/mpremote.html):

```bash
# master (ESP32-S3): copia i file .py e la cartella web/
cd master
mpremote fs mkdir :web
mpremote cp web/index.html :web/index.html
mpremote cp config.py settings.py scoreboard.py keypad.py leds.py games.py session.py app.py net.py buttons.py webserver.py main.py :
mpremote reset
```

```bash
# telecomando (qualsiasi ESP32)
cd remote
mpremote cp config.py main.py :
```

Collega il telefono alla rete **`2FastTarget`** (password iniziale **`2fasttarget`**, da cambiare in
Impostazioni → WiFi) e apri **http://192.168.4.1**.

I pin sono in `master/config.py` (invariati rispetto alla versione precedente: tastiera
colonne 14,13,12,11,10 / righe 18,8,3,46,9; LED colonne 1,2,42,41,40 / righe 39,38,37,36,35;
LED di stato GPIO48). Pulsanti locali opzionali: start/stop GPIO4, stop GPIO5.

## Modalità di gioco

Il tempo è sempre misurato e mostrato nella pagina (cronometro fluido, tempo di ogni bersaglio,
medio/migliore/peggiore, penalità). Prima della partita c'è il semaforo (righe che si accendono
e attesa casuale), disattivabile.

| Modalità | Descrizione | Risultato |
|---|---|---|
| **Sequenza** | tutti i bersagli, ordine casuale, uno alla volta (il gioco originale). Timeout per bersaglio, penalità opzionali per errore/mancato | tempo totale (più basso = meglio) |
| **Riflessi** | N round: dopo un'attesa casuale si accende un bersaglio, va colpito il prima possibile; i colpi anticipati sono errori | tempo di reazione medio |
| **A tempo** | più bersagli possibile entro X secondi | numero di colpi |
| **Multi‑bersaglio** | K bersagli accesi insieme, in qualsiasi ordine, finché sono tutti colpiti | tempo totale |
| **Demo** | sequenza infinita senza punteggio | – |

Record e ultime 15 partite sono salvati in flash (`results.json`) e visibili in *Risultati*.
Ogni parametro si può cambiare per la singola partita (sotto le modalità) o in modo permanente in *Impostazioni*.

## Avvio partita

* dalla pagina (pulsante **AVVIA / STOP**);
* dal **pulsante sul master** (GPIO4: avvia/ferma, GPIO5: ferma);
* dal **telecomando radio**: pulsante start (avvia/ferma) e opzionale stop. Il telecomando trasmette
  frame ESP‑NOW broadcast `2FT|codice|id|comando`, ripetuti 3 volte; il master scarta i duplicati.
  Non serve conoscere il MAC: bastano **stesso canale** (`CHANNEL` in `remote/config.py` = canale WiFi
  del master) e **stesso codice** (`SECRET` = "Codice di abbinamento"). Il codice non è una cifratura:
  serve solo a evitare comandi involontari da altri telecomandi vicini.

La pagina indica da dove è partito l'ultimo comando.

## Lettura affidabile della matrice

La scansione (`master/keypad.py`) è pensata per sopportare i guasti tipici di una matrice a pressione:

* **antirimbalzo ad integratore**: un contatto isolato di una scansione non diventa mai un colpo;
* **tempo del primo contatto**: il tempo di reazione parte dal primo istante di contatto, non da quando
  l'antirimbalzo conferma, quindi l'antirimbalzo non falsa i tempi;
* **tasti fantasma**: se tre tasti formano l'angolo di un rettangolo, il quarto (fantasma) e gli ambigui
  non vengono accettati (disattivabile);
* **bersaglio bloccato** (premuto oltre `stuck_ms`, linea in corto): viene escluso finché non si rilascia;
* **rumore**: se troppi tasti risultano premuti insieme la scansione viene ignorata;
* colonne **open‑drain** (rilasciate, mai pilotate alte) e tempo di assestamento regolabile.

I LED sono pilotati in multiplexing solo quando serve (più bersagli accesi), altrimenti in modo statico.

## Modalità test e taratura

*Test → Entra in modalità test* (durante il test non si gioca):

* **matrice in tempo reale**: LED acceso, bersaglio premuto, contatto grezzo (non ancora confermato),
  ambiguo, bloccato, disattivato, contatore di pressioni per bersaglio, frequenza di scansione;
* **controllo singolo dei LED**: tocca un bersaglio per accendere/spegnere il suo LED; pulsanti
  *tutti accesi/spenti*, *scorrimento*, *righe*, *colonne*;
* **attiva/disattiva bersaglio**: un bersaglio rotto viene escluso da tutti i giochi;
* **associazione bersagli ↔ tasti** (procedura guidata): accende i LED uno alla volta e impara quale
  tasto risponde; i bersagli assenti si saltano. La corrispondenza è salvata e usata nei giochi.

## Impostazioni

Tutto è modificabile da *Impostazioni* e salvato in `settings.json` (validato, scrittura atomica;
un file corrotto o un valore non valido ricade sui predefiniti): parametri dei giochi, semaforo,
antirimbalzo/assestamento/filtro fantasmi/soglia bloccato, WiFi (nome, password, canale, rete
domestica opzionale) e codice del telecomando. Le modifiche WiFi richiedono il riavvio.

Con una **rete domestica** configurata il master si collega anche a quella (resta sempre disponibile
il proprio access point). In quel caso il canale radio segue quello del router: imposta lo stesso
`CHANNEL` nel telecomando.

## Affidabilità

* watchdog hardware (riavvio se il loop principale si blocca), ogni servizio è in un task che riparte
  da solo dopo un errore; errore fatale → `error.log` e riavvio (5 s per fermarsi con Ctrl‑C);
* un errore in un singolo ciclo di scansione non ferma il gioco;
* il server web limita connessioni, dimensione richieste e durata; richieste malformate non lo bloccano;
* l'interfaccia mostra se il dispositivo è raggiungibile (pallino verde/rosso).

## API HTTP (JSON)

`GET /api/state` · `GET /api/result` · `GET /api/info` · `GET|POST /api/config` · `POST /api/config/reset` ·
`POST /api/start {mode, params}` · `POST /api/stop` · `POST /api/appmode {mode: play|test}` ·
`POST /api/test/led {i,on | mask | pattern}` · `POST /api/test/learn {action: start|skip|back|cancel}` ·
`POST /api/test/reset` · `GET /api/results` · `POST /api/results/clear` · `POST /api/reboot`

La rete è protetta dalla password WiFi, ma l'API non ha un'ulteriore autenticazione.

## Sviluppo e test su PC

```bash
python3 -m unittest discover -s tests     # 47 test: tastiera (fantasmi, rimbalzi, bloccati), LED, giochi, sessioni, impostazioni, API web
python3 tests/sim.py                      # master simulato: apri http://localhost:8080
```

I test usano un modello elettrico della matrice (compresi i tasti fantasma) al posto dei pin.
Non sostituiscono la prova sull'hardware: lo sketch non è stato ancora provato su una scheda reale.
