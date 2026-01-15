# Sistema di Generazione Narrativa con Apprendimento dagli Errori

Sistema di generazione automatica di storie con feedback loop per ridurre anacronismi e incoerenze storiche.

## 🎯 Obiettivo

Confrontare due approcci di generazione narrativa:
- **Method A**: Con apprendimento dagli errori (feedback esplicito su anacronismi)
- **Method B**: Baseline senza feedback (solo generazione)

## 📊 Risultati Principali

| Metrica | Method A | Method B | Improvement |
|---------|----------|----------|-------------|
| **Incoerenze totali** | 1.2/storia | 3.4/storia | **-64.7%** |
| **Incoerenze ripetute** | 0.1/storia | 3.7/storia | **-97.3%** |
| **Rate errori/turno** | 0.12 | 0.34 | **-64.7%** |
| **Fatti estratti** | 63.6/storia | 50.0/storia | +27.2% |
| **Lunghezza turni** | 325 parole | 238 parole | +36.5% |

**Conclusione**: Method A riduce gli errori del 65% e quasi non ripete mai lo stesso errore (97% meno ripetizioni).

## 🏗️ Architettura Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    Method A (Learning)                   │
├─────────────────────────────────────────────────────────┤
│ 1. Genera storia (Gemini 1.5 Flash)                    │
│    + Cached context (mondo, personaggi, plot)          │
│    + Plot guidance basato su fase narrativa             │
│    + Feedback su errori precedenti ⚠️                   │
│    + Lista banned objects 🚫                            │
│                                                         │
│ 2. Estrazione (Gemini, temp=0.2)                       │
│    - Fatti narrativi                                    │
│    - Oggetti menzionati                                 │
│    - VIOLAZIONI (solo anacronismi storici)             │
│                                                         │
│ 3. Update State                                         │
│    - Accumula fatti e oggetti                           │
│    - Registra inconsistencies                           │
│    - Prepara feedback per turno successivo              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   Method B (Baseline)                    │
├─────────────────────────────────────────────────────────┤
│ 1. Genera storia (Gemini 1.5 Flash)                    │
│    + State attuale (fatti, oggetti)                     │
│    ❌ NESSUN feedback su errori                         │
│                                                         │
│ 2. Estrazione (identica a Method A)                    │
│    - Rileva errori MA non li passa al modello           │
│                                                         │
│ 3. Update State (solo tracking, no learning)           │
└─────────────────────────────────────────────────────────┘
```

## 🔧 Componenti Principali

### `CLasses.py` (592 righe)
- `generate_story_step_method_A()`: Generazione con apprendimento
- `generate_story_step_method_B()`: Baseline senza feedback
- `update_state_from_output()`: Estrazione fatti e rilevamento errori
- `create_cacheable_context()`: Context caching per ridurre costi

### `main.py` (122 righe)
- Entry point per generazione singola storia
- Carica configurazione da `story_config.json`
- Supporta modalità interattiva (`--interactive`) e rapida (`--quick`)

### `compare_methods.py` (231 righe)
- Esegue esperimento comparativo N×M storie
- Salva metriche dettagliate per ogni run
- Genera statistiche aggregate

### `analyze_metrics.py` (294 righe)
- Carica risultati JSON
- Genera 5 grafici comparativi
- Produce report testuale

## 🚀 Come Usare

### Setup
```powershell
# Attiva ambiente virtuale
.\Story\Scripts\Activate.ps1

# Installa dipendenze
pip install google-generativeai matplotlib numpy
```

### Generazione Singola Storia
```powershell
# Storia completa 10 turni
python main.py

# Storia rapida 3 turni
python main.py --quick

# Modalità interattiva
python main.py --interactive
```

### Esperimento Comparativo
```powershell
# 10 storie per metodo, 10 turni ciascuna (~40 minuti)
python compare_methods.py --runs 10 --turns 10 --output final_results

# Test rapido (1 storia per metodo, 3 turni)
python compare_methods.py --runs 1 --turns 3 --output test_run
```

### Analisi Risultati
```powershell
# Genera grafici e report
python analyze_metrics.py --input final_results/ --output analysis_graphs
```

## 📁 Struttura Output

```
final_results/
├── comparison_results.json           # Metriche aggregate (leggero)
├── comparison_results_full.json      # Con testi storie (pesante ~2MB)
├── method_A_run_1.json               # Dettagli singola storia Method A
├── method_A_run_2.json
├── ...
├── method_B_run_1.json               # Dettagli singola storia Method B
└── ...

analysis_graphs/
├── inconsistencies_comparison.png    # Barre: incoerenze A vs B
├── facts_objects_comparison.png      # Barre: fatti e oggetti
├── turn_length_distribution.png      # Boxplot: lunghezza turni
├── facts_accumulation.png            # Linee: accumulazione fatti
├── inconsistencies_by_turn.png       # Istogrammi: quando compaiono errori
└── analysis_report.txt               # Report testuale riassuntivo
```

## 🎮 Configurazione Storia

`story_config.json` contiene:
- **World**: Ambientazione (Monastero Yunshan, Cina 1380, dinastia Ming)
- **Characters**: 8 personaggi con traits, backstory, abilities
- **Plot**: Struttura narrativa (inciting incident, complications, climax, resolution)
- **Narrative config**: Parametri (max_turns, etc.)

### Esempio Regole Mondo
```json
"rules": [
  "L'anno è il 1380, dinastia Ming, non esistono tecnologie moderne",
  "I monaci usano poteri elementali attraverso il chi e la meditazione",
  "Solo i monaci del monastero conoscono la vera natura degli artefatti elementali"
]
```

## 🧠 Sistema di Apprendimento (Method A)

### Feedback Loop
1. **Rilevamento**: Prompt specializzato rileva SOLO anacronismi storici
2. **Feedback**: Turno successivo riceve:
   ```
   ⚠️ ERRORI CRITICI DA NON RIPETERE MAI:
   ❌ Turn 2 (anacronismo): Cannocchiale d'ottone...
   
   🚫 OGGETTI VIETATI: cannocchiale/telescopio
   NON menzionare questi oggetti in NESSUN modo.
   ```
3. **Prevenzione**: Modello evita oggetti bannati nei turni successivi

### Plot Guidance
Temperature dinamica basata su fase narrativa:
- **Fase iniziale (0-30%)**: Setup → temp 0.7
- **Fase centrale (30-60%)**: Complications → temp 0.7
- **Fase climax (60-85%)**: Tensione crescente → temp 0.7
- **Fase finale (85-100%)**: Risoluzione → **temp 0.5** (maggiore aderenza)

### Prompt Finale Imperativo
```
🔴 TURNO FINALE - CONCLUDI LA STORIA ORA!
OBBLIGATORIO: Questo è l'ultimo turno disponibile. Devi:
1. Risolvere il conflitto principale (recupero artefatto)
2. Concludere l'arco di Zhang Hao (scelta finale)
3. Chiudere con un epilogo definitivo (pace ristabilita o conseguenze)
NON lasciare la storia aperta o incompleta. Scrivi una CONCLUSIONE.
```

## 🔍 Rilevamento Anacronismi

### Cosa Viene Rilevato
✅ **ANACRONISMI**: Oggetti/tecnologie inesistenti nell'epoca
- Esempio: Cannocchiale nel 1380 (invenzione 1600)
- Esempio: Pistole, orologi da polso, stampa in Cina prima XV secolo

✅ **IMPOSSIBILITÀ STORICHE**: Eventi impossibili per l'epoca
- Esempio: America prima del 1492
- Esempio: Mongolfiere prima dei fratelli Montgolfier

✅ **CONTRADDIZIONI**: Fatti che contraddicono storia precedente

### Cosa NON Viene Rilevato
❌ Comportamenti dei personaggi
❌ Decisioni tattiche
❌ Violazioni di protocolli/regole interne
❌ Oggetti plausibili per l'epoca (cristalli, strumenti rudimentali)

## 💰 Costi Stimati

**Modello**: Gemini 1.5 Flash (`models/gemini-flash-lite-latest`)
- Input: $0.075 per 1M tokens
- Output: $0.30 per 1M tokens

**Per storia (10 turni)**:
- 2 chiamate/turno × 10 turni = 20 chiamate
- ~1000 tokens input + ~500 tokens output per chiamata
- Costo: ~$0.005 per storia

**Esperimento completo (20 storie)**: ~$0.10

## ⚙️ Ottimizzazioni Implementate

1. **Caching**: Context fisso (mondo, personaggi) prepended per 70% sconto token
2. **API Call Reduction**: 3→2 chiamate per turno (generazione + estrazione unificata)
3. **Rate Limiting**: 12s delay tra chiamate per rispettare limiti gratuiti
4. **Temperature Dinamica**: 0.7 creative → 0.5 finale per aderenza istruzioni

## 📈 Metriche Tracciate

Per ogni storia:
- `total_facts`: Numero fatti narrativi estratti
- `total_objects`: Numero oggetti menzionati
- `total_inconsistencies`: Numero anacronismi rilevati
- `repeated_inconsistencies`: Errori dello stesso tipo ripetuti
- `inconsistency_rate`: Errori per turno
- `avg_turn_length_words`: Lunghezza media turno in parole
- `turn_lengths`: Lista lunghezze per ogni turno
- `inconsistencies_by_type`: Distribuzione per categoria (anacronismo, contraddizione, etc.)

## 🐛 Troubleshooting

### Errore: API quota exceeded
- Sistema gratuito: 3 richieste/minuto
- Delay di 12s tra chiamate è sufficiente per rispettare limite
- Se errore persiste: aumenta delay in `call_gemini()`

### Errore: Response blocked
- Gemini ha filtri di sicurezza
- Modifica prompt per evitare contenuti sensibili
- Gestito in `call_gemini()` con fallback

### Grafici non generati
- Verifica installazione: `pip install matplotlib numpy`
- Usa file `_full.json` per grafici avanzati (contiene story_state)

## 📚 Riferimenti

- **Google Gemini API**: https://ai.google.dev/gemini-api/docs
- **Prompt Engineering**: Feedback esplicito con emoji e banned lists
- **Temperature Tuning**: Dinamica basata su fase narrativa

## 📝 Licenza

Progetto accademico per corso Natural Language Processing, Università [Nome].

## 👥 Autori

[Nome Studente] - [email]

---

**Data ultimo aggiornamento**: 6 Gennaio 2026
