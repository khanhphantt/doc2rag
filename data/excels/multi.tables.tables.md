# Excel — detected tables

Detected **6** table(s) across **1** sheet(s).

## Sheet: `Enterprise - LLM` — 6 table(s)

### Table 1 `[B6:G7]` — Updated on 8 May 2026 Source: https://docs.google.com/document/d/1FybSxB3lXJ5NOyA-EVsAm-Cz9Wpv0YydrmSn8SeefRo/edit?usp=sharing

| #Messages | 50000000 | ⇒ | RATE (3 responses, in use) | 368072.5 | 59771477.31125 |
|---|---|---|---|---|---|
| #Messages | 50000000 | ⇒ | RATE (1 response, Hypothesis) | 180312.50000000003 | 29281037.03125 |

### Table 2 `[E12:J18]` — 73580193.2976445 43089753.0176445

> 🧮 **Avg input cost** = Avg input tokens * C / 1000000  (`=G13*$C$13/1000000`)

> 🧮 **Avg output cost** = Avg ouput tokens * C / 1000000  (`=I13*C14/1000000`)

| Step | Model | Avg input tokens | Avg input cost | Avg ouput tokens | Avg output cost |
|---|---|---|---|---|---|
| Summarize Conversation | gpt-4o-mini | 21850000000 | 3277.5 | 1300000000 | 780 |
| Summarize Conversation | gpt-4o-mini | 21850000000 | 3277.5 | 1300000000 | 780 |
| Execute Workflow | gpt-4.1-mini (3 responses) | 612500000000 | 245000 | 22900000000 | 36640 |
| Execute Workflow | gpt-4.1-mini (1 response) | 204166666666.66666 | 81666.66666666667 | 7633333333.333333 | 12213.333333333334 |
| Execute Workflow | gpt-4o-mini | 178000000000 | 26700 | 2750000000 | 1650 |
| Execute Workflow | gemini-2.5-flash | 5000000000 | 53400 | 250000000 | 625 |

### Table 3 `[B13:C18]` — STANDARD COST Model Rates (per 1M tokens)

| gpt-4o-mini input | 0.15 |
|---|---|
| gpt-4o-mini output | 0.6 |
| gpt-4.1-mini input | 0.4 |
| gpt-4.1-mini output | 1.6 |
| gemini-2.5-flash input | 0.3 |
| gemini-2.5-flash output | 2.5 |

### Table 4 `[A22:D27]` — EXECUTE WORKFLOW:

| # | Tasks | Model | Notes |
|---|---|---|---|
| 1 | Language Detection | gemini-2.5-flash |  |
| 2 | Query Rewrite | gpt-4o-mini |  |
| 3 | Parallel Response | gpt-4.1-mini | (parallel response) |
| 4 | Generation | gpt-4o-mini |  |
| 5 | Evaluation (optional) | gpt-4o-mini |  |

### Table 5 `[E31:J34]` — 73580193.2976445 43089753.0176445

> 🧮 **Estimated cost 90348.63945578232** = C * (50 / 7.84) * (C / 60)  (`=$C$6 * (50 / 7.84) * (C33/60)`)

| Estimated cost 90348.63945578232 | Estimated cost 14671760.7355442 | Calculation Logic #message * (avg_input_syllables / avg_syllables_speed) * (Rate/ 60 secs) | Calculation Logic #message * (avg_input_syllables / avg_syllables_speed) * (Rate/ 60 secs)_2 | Calculation Logic #message * (avg_input_syllables / avg_syllables_speed) * (Rate/ 60 secs)_3 | Calculation Logic #message * (avg_input_syllables / avg_syllables_speed) * (Rate/ 60 secs)_4 |
|---|---|---|---|---|---|
| 85034.01360544217 | 13808715.9863945 | #message * (avg_input_syllables / avg_syllables_speed) * (Rate/ 60 secs) | #message * (avg_input_syllables / avg_syllables_speed) * (Rate/ 60 secs) | #message * (avg_input_syllables / avg_syllables_speed) * (Rate/ 60 secs) | #message * (avg_input_syllables / avg_syllables_speed) * (Rate/ 60 secs) |
| 127551.02040816327 | 20713073.9795918 | #message * (avg_input_syllables / avg_syllables_speed) * (Rate/ 60 secs) | #message * (avg_input_syllables / avg_syllables_speed) * (Rate/ 60 secs) | #message * (avg_input_syllables / avg_syllables_speed) * (Rate/ 60 secs) | #message * (avg_input_syllables / avg_syllables_speed) * (Rate/ 60 secs) |

### Table 6 `[B32:C34]` — [OPTION] VOICE INPUT S2T Model Rates (per minutes)

| GPT-Realtime-Whisper | 0.017 |
|---|---|
| Google Speech-to-Text | 0.016 |
| Amzon Transcribe | 0.024 |
