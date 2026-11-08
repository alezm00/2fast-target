# 2Fast Target

Matrice 5×5 di bersagli luminosi a pressione, controllata da un ESP32‑S3 (MicroPython).
Il master crea una **rete WiFi propria** e serve una **pagina web** (telefono o PC) per giocare,
vedere i tempi, configurare e tarare i bersagli. La partita si sceglie e si configura dalla pagina,
poi si avvia dalla pagina oppure dal **tasto START** collegato al master.

```
 telefono / PC ──WiFi──► master ESP32‑S3 ◄── tasto START
                          │  matrice tasti 5×5 (lettura)
                          └─ matrice LED 5×5 (uscita)
```

## Struttura

| Cartella | Contenuto |
|---|---|
| `master/` | firmware del master: scansione bersagli, LED, giochi, server web, tasto START |
| `master/web/index.html` | interfaccia web (un solo file, nessuna dipendenza da internet) |
| `tests/` | test su PC (50) e simulatore del master |
| `firmware/` | MicroPython 1.29.0 per ESP32 e ESP32‑S3 |

## Installazione

Serve MicroPython **1.29** o successivo (vedi `firmware/`; il codice funziona anche con le versioni precedenti). Con [`mpremote`](https://docs.micropython.org/en/latest/reference/mpremote.html):

```bash
# master (ESP32-S3): copia i file .py e la cartella web/
cd master
mpremote fs mkdir :web
mpremote cp web/index.html :web/index.html
mpremote cp config.py settings.py scoreboard.py keypad.py leds.py games.py session.py app.py net.py buttons.py webserver.py main.py :
mpremote reset
```

Collega il telefono alla rete **`2FastTarget`** (password iniziale **`2fasttarget`**, da cambiare in
Impostazioni → WiFi) e apri **http://192.168.4.1**.

I pin sono in `master/config.py` (invariati rispetto alla versione precedente: tastiera
colonne 14,13,12,11,10 / righe 18,8,3,46,9; LED colonne 1,2,42,41,40 / righe 39,38,37,36,35;
LED di stato GPIO48). Tasto START: GPIO4 verso GND (pull‑up interno), configurabile in `BTN_START_PIN`.

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
La partita **selezionata** e i suoi parametri si impostano nella pagina *Gioca* (o in *Impostazioni*) e
si salvano subito sul dispositivo: AVVIA e tasto START avviano sempre quella.

## Avvio partita

Si sceglie la partita e se ne regolano i parametri dalla pagina; poi:

* **AVVIA** nella pagina (diventa **STOP** durante la partita);
* oppure il **tasto START** sul master (GPIO4): avvia la partita selezionata con gli stessi parametri.
  Il tasto non ferma mai una partita in corso (si ferma dalla pagina), così una pressione accidentale
  durante il gioco è innocua; è ignorato in modalità test.

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
domestica opzionale). Le modifiche WiFi richiedono il riavvio.

Con una **rete domestica** configurata il master si collega anche a quella (resta sempre disponibile
il proprio access point).

## Affidabilità

* watchdog hardware (riavvio se il loop principale si blocca), ogni servizio è in un task che riparte
  da solo dopo un errore; errore fatale → `error.log` e riavvio (5 s per fermarsi con Ctrl‑C);
* un errore in un singolo ciclo di scansione non ferma il gioco;
* il server web limita connessioni, dimensione richieste e durata; richieste malformate non lo bloccano;
* l'interfaccia mostra se il dispositivo è raggiungibile (pallino verde/rosso).

## API HTTP (JSON)

`GET /api/state` · `GET /api/result` · `GET /api/info` · `GET|POST /api/config` · `POST /api/config/reset` ·
`POST /api/start {}` (avvia la partita selezionata) · `POST /api/stop` · `POST /api/appmode {mode: play|test}` ·
`POST /api/test/led {i,on | mask | pattern}` · `POST /api/test/learn {action: start|skip|back|cancel}` ·
`POST /api/test/reset` · `GET /api/results` · `POST /api/results/clear` · `POST /api/reboot`

La rete è protetta dalla password WiFi, ma l'API non ha un'ulteriore autenticazione.

## Sviluppo e test su PC

```bash
python3 -m unittest discover -s tests     # 51 test: tastiera (fantasmi, rimbalzi, bloccati), LED, giochi, sessioni, impostazioni, API web
python3 tests/sim.py                      # master simulato: apri http://localhost:8080
```

I test usano un modello elettrico della matrice (compresi i tasti fantasma) al posto dei pin.
Non sostituiscono la prova sull'hardware: lo sketch non è stato ancora provato su una scheda reale.

## Flash del firmware MicroPython

L'immagine per il master è `firmware/ESP32-S3` (la cartella `firmware/ESP32` non serve più a questo progetto). Con [`esptool`](https://docs.espressif.com/projects/esptool/):

```bash
# ESP32‑S3 (master): indirizzo 0
esptool.py erase_flash
esptool.py --baud 460800 write_flash 0 firmware/ESP32-S3/ESP32_GENERIC_S3-20260824-v1.29.0.bin
```

`erase_flash` cancella anche impostazioni e risultati salvati. Dalla 1.29 l'API di rete usa
`network.WLAN.IF_STA`/`IF_AP`, `key=` e `security=`: il codice usa quella nuova e, se manca, la vecchia.
