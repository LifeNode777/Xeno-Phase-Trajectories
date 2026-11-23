# XPT — diagnostyczne sprawdzenie baseline'ów

**Protocol:** `XPT-BASELINE-REPAIR-1.1`
**Status wykonania:** COMPLETED

**XPT detector: NOT_EVALUATED.**
To nie jest walidacja XPT ani nowa konfirmacja Gate 1.

Progi wybierane tylko na diagnostyce (N=120, seed=20261108).
Dalsze zbiory są sprawdzane bez ponownego strojenia.

Czysty canary sprawdza ograniczony zakres plików i środowiska; nie dowodzi pełnej izolacji OS.

## Zamrożone konfiguracje

| Układ | Metoda | h | Korekta czasu (próbki) |
|---|---|---:|---:|
| NLSE_A | cusum_lv | 500 | -4 |
| NLSE_A | spectral | 3 | -39 |
| NLSE_P | cusum_lv | 300 | -2 |
| NLSE_P | spectral | 3 | -41 |
| DUFFING | cusum_lv | 800 | 50 |
| DUFFING | spectral | 3 | -43 |
| VDP | cusum_lv | 800 | 40 |
| VDP | spectral | 3 | -61 |
| ROSSLER | cusum_lv | 1500 | -5 |
| ROSSLER | spectral | 3 | 0 |

## exploratory_recheck

| Warunek | Metoda | Werdykt | Hit | Mediana błędu T_c | FA | N kwal./wszystkie |
|---|---|---|---:|---:|---:|---:|
| NLSE_A|0.05 | cusum_lv | PARTIAL | 0.900 | 0.062 | 0.000 | 150/150 |
| NLSE_A|0.05 | spectral | STABLE | 1.000 | 0.094 | 0.000 | 150/150 |
| NLSE_A|0.2 | cusum_lv | PARTIAL | 0.698 | 0.125 | 0.007 | 149/150 |
| NLSE_A|0.2 | spectral | STABLE | 1.000 | 0.125 | 0.000 | 149/150 |
| NLSE_P|0.05 | cusum_lv | INVISIBLE | 0.460 | 0.125 | 0.013 | 150/150 |
| NLSE_P|0.05 | spectral | STABLE | 1.000 | 0.031 | 0.000 | 150/150 |
| NLSE_P|0.2 | cusum_lv | INVISIBLE | 0.353 | 0.250 | 0.020 | 150/150 |
| NLSE_P|0.2 | spectral | STABLE | 1.000 | 0.031 | 0.000 | 150/150 |
| DUFFING|0.05 | cusum_lv | INVISIBLE | 0.140 | 1.719 | 0.007 | 150/150 |
| DUFFING|0.05 | spectral | STABLE | 0.967 | 0.188 | 0.000 | 150/150 |
| DUFFING|0.2 | cusum_lv | INVISIBLE | 0.113 | 1.875 | 0.007 | 150/150 |
| DUFFING|0.2 | spectral | STABLE | 0.967 | 0.188 | 0.000 | 150/150 |
| VDP|0.05 | cusum_lv | INVISIBLE | 0.180 | 1.406 | 0.013 | 150/150 |
| VDP|0.05 | spectral | STABLE | 1.000 | 0.125 | 0.000 | 150/150 |
| VDP|0.2 | cusum_lv | INVISIBLE | 0.113 | 1.641 | 0.007 | 150/150 |
| VDP|0.2 | spectral | STABLE | 1.000 | 0.125 | 0.000 | 150/150 |
| ROSSLER|0.05 | cusum_lv | PARTIAL | 0.753 | 0.375 | 0.027 | 150/150 |
| ROSSLER|0.05 | spectral | INVISIBLE | 0.000 | nan | 0.000 | 150/150 |
| ROSSLER|0.2 | cusum_lv | PARTIAL | 0.567 | 0.906 | 0.007 | 150/150 |
| ROSSLER|0.2 | spectral | INVISIBLE | 0.000 | nan | 0.000 | 150/150 |

## diagnostic_verification

| Warunek | Metoda | Werdykt | Hit | Mediana błędu T_c | FA | N kwal./wszystkie |
|---|---|---|---:|---:|---:|---:|
| NLSE_A|0.05 | cusum_lv | PARTIAL | 0.875 | 0.094 | 0.000 | 200/200 |
| NLSE_A|0.05 | spectral | STABLE | 1.000 | 0.094 | 0.000 | 200/200 |
| NLSE_A|0.2 | cusum_lv | PARTIAL | 0.714 | 0.125 | 0.010 | 199/200 |
| NLSE_A|0.2 | spectral | STABLE | 1.000 | 0.094 | 0.000 | 199/200 |
| NLSE_P|0.05 | cusum_lv | INVISIBLE | 0.475 | 0.125 | 0.000 | 200/200 |
| NLSE_P|0.05 | spectral | STABLE | 1.000 | 0.031 | 0.000 | 200/200 |
| NLSE_P|0.2 | cusum_lv | INVISIBLE | 0.330 | 0.312 | 0.015 | 200/200 |
| NLSE_P|0.2 | spectral | STABLE | 1.000 | 0.031 | 0.000 | 200/200 |
| DUFFING|0.05 | cusum_lv | INVISIBLE | 0.165 | 1.750 | 0.005 | 200/200 |
| DUFFING|0.05 | spectral | STABLE | 0.965 | 0.188 | 0.000 | 200/200 |
| DUFFING|0.2 | cusum_lv | INVISIBLE | 0.180 | 1.844 | 0.000 | 200/200 |
| DUFFING|0.2 | spectral | STABLE | 0.965 | 0.188 | 0.000 | 200/200 |
| VDP|0.05 | cusum_lv | INVISIBLE | 0.180 | 1.578 | 0.005 | 200/200 |
| VDP|0.05 | spectral | STABLE | 1.000 | 0.156 | 0.000 | 200/200 |
| VDP|0.2 | cusum_lv | INVISIBLE | 0.200 | 1.625 | 0.010 | 200/200 |
| VDP|0.2 | spectral | STABLE | 1.000 | 0.156 | 0.000 | 200/200 |
| ROSSLER|0.05 | cusum_lv | PARTIAL | 0.720 | 0.469 | 0.025 | 200/200 |
| ROSSLER|0.05 | spectral | INVISIBLE | 0.000 | nan | 0.000 | 200/200 |
| ROSSLER|0.2 | cusum_lv | PARTIAL | 0.575 | 0.797 | 0.000 | 200/200 |
| ROSSLER|0.2 | spectral | INVISIBLE | 0.000 | nan | 0.000 | 200/200 |

## Jak czytać

- COMPLETED: procedura wykonana; wynik naukowy znajduje się w tabeli, nie w kolorze workflow.
- STABLE / PARTIAL / INVISIBLE: zdolność lokalizacji onsetu danego baseline'u w danym warunku.
- FALSE_POSITIVE_CANDIDATE: przekroczony budżet alarmów na kontrolach bez przejścia.
- INCONCLUSIVE: za mało kwalifikujących się prób lub zbyt dużo NO_VERDICT.
- Hit liczony na próbach z t_det >= 0; NO_VERDICT w tej grupie liczy się jako nietrafienie.
- T_c to charakterystyczny okres układu, nie uniwersalna sekunda.
- Nie zmieniaj progów po obejrzeniu weryfikacji. Zachowaj ten raport przed kolejną wersją.

Artefakty: `capability_matrix.json`, `metrics.csv`, `frozen_configs.json`, `SHA256SUMS.json`.
