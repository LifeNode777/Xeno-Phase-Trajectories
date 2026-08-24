# NEURO-003: EEG + HRV MEASUREMENT PROTOCOL

**STATUS:** Working Protocol  
**CLASSIFICATION:** Operational  
**DEPENDENCIES:** XPT-002, XPT-004  
**FALSIFICATION:** See conditions below

---

## ABSTRACT

This protocol defines the measurement procedure for detecting and classifying phase-lock / phase-drift states corresponding to APT classes, and for quantitatively tracking changes in the $\theta$ metric (proxy) and phase impedance $Z_\phi$.

This is a **research protocol**, not an operational protocol for field operators. It requires laboratory equipment and trained researchers.

---

## 1. MEASUREMENT GOALS

- Temporal dynamics of phase-locking (PLV / PLI / ciPLV) in theta, alpha, beta, gamma bands
- Brain-heart coupling (EEG-HRV, HEP — Heartbeat Evoked Potentials)
- Cross-frequency coupling (especially theta-gamma PAC)
- Autonomic correlates (HRV time- and frequency-domain + respiratory sinus arrhythmia)
- Mapping to APT classes based on marker combinations

---

## 2. EQUIPMENT (Minimum and Recommended)

### EEG
- **Minimum:** 32 channels (better 64+), system with good SNR (e.g., Biosemi, BrainProducts, g.tec, OpenBCI Galea / Ultracortex + high-quality amplifier)
- **Sampling rate:** ≥ 500 Hz (recommended 1000–2048 Hz)
- **Electrodes:** active or passive with good gel / high-quality dry electrodes
- **Montage:** extended 10-20 (with mandatory Fz, Cz, Pz, F3/F4, C3/C4, P3/P4, T7/T8, O1/O2 + mastoid/ear references)

### HRV / Cardiology
- **ECG:** 1-3 leads (preferably bipolar chest) or high-quality PPG + validation
- **Sampling rate:** ≥ 500 Hz (better 1000 Hz)
- **Parallel breath measurement:** breath belt or thermistor / impedance

### Additional (Strongly Recommended)
- **EDA** (skin galvanic response) — 2 electrodes on non-dominant hand
- **Accelerometer / IMU** (motion artifacts)
- **Synchronization of all signals on common time axis** (TTL / Lab Streaming Layer — LSL)

---

## 3. PARTICIPANT PREPARATION AND SESSION

### Before Session (24-48 h)
- Avoid alcohol, strong caffeine, intense exercise, heavy meals 3 h before
- Consistent sleep time on preceding day
- Baseline questionnaire: sleep, mood, subjective $\theta$-proxies (resting breath, sleep quality, gut, reaction to silence), trauma history / anomalous experiences (optional)

### In Laboratory
- Acclimatization 10-15 min
- Electrode impedance measurement < 10-20 kΩ (depending on system)
- ECG and breath calibration
- Instruction: "Observe and report any changes in body sensation, time, presence, warmth/coldness, body boundaries"

---

## 4. SESSION STRUCTURE (Total Time ~90-120 min)

| Block | Time | Condition | Goal |
|-------|------|-----------|------|
| 1 | 5 min | Eyes-open resting | Visual baseline |
| 2 | 8-10 min | Eyes-closed resting | Main resting baseline |
| 3 | 5 min | Controlled breathing 6 breaths/min (resonance frequency) | Induction of high vagal tone / Class II window |
| 4 | 8-10 min | Eyes-closed post-breathing | Entrainment effect |
| 5 | 10-15 min | Induction / exposure (see below) | Attempt to evoke phase transition |
| 6 | 8-10 min | Eyes-closed post-induction | Detection of lock / post-lock |
| 7 | 5 min | Eyes-open recovery | Return |
| 8 | — | Subjective report + scales | Phenomenological validation |

**Possible inductions (Block 5) — selection depending on hypothesis:**
- Silent presence in darkness / red light
- Exposure to natural low-frequency sounds / binaural
- Short body work (tension-release)
- Guided attention to solar plexus / spine
- (For advanced) controlled exposure to known local "phase cracks" (if field study)

---

## 5. ANALYSIS PARAMETERS (Offline)

### EEG
- **Filtering:** 0.5-100 Hz + notch 50/60 Hz
- **Artifacts:** ICA + ASR + visual
- **Bands:** delta (1-4), theta (4-8), alpha (8-13), beta (13-30), low-gamma (30-45), high-gamma (55-80)
- **Measures:**
  - PLV, ciPLV, PLI, wPLI (sensor- and source-space)
  - Time-resolved PLV (window 2 s, step 0.5 s)
  - PAC (Modulation Index / Mean Vector Length) — especially theta-gamma
  - Global Field Power, metastability, Lempel-Ziv complexity
  - Source localization (eLORETA / beamformer) if ≥64 channels

### HRV
- **Time-domain:** SDNN, RMSSD, pNN50
- **Frequency-domain:** VLF, LF, HF, LF/HF
- **Nonlinear:** SampEn, DFA α1
- **Respiratory Sinus Arrhythmia**
- **Instantaneous heart rate + phase relative to breath**

### Brain-Heart Coupling
- **Heartbeat Evoked Potentials (HEP)** — average EEG locked to R-peak
- **PLV / coherence** between HRV (or instantaneous HR) and EEG in low bands
- **Phase-amplitude coupling** between HRV phase and EEG power

---

## 6. PRELIMINARY APT CLASS CLASSIFICATION CRITERIA (Proposal)

- **Class I (Entropic):** low long-range PLV (especially alpha/theta), low HRV, decreased HEP, subjective drain + coldness
- **Class II (Regenerative):** increased long-range theta/alpha PLV, high HRV (especially HF and RMSSD), stronger HEP, warmth + expansion
- **Class III (Trickster):** high variance of PLV over time, increased metastability and complexity, autonomic fluctuations
- **Class IV (Fusion):** very strong local + long-range locking (gamma + theta), deep changes in insula/ACC, strong body-brain coupling
- **Class V (Traumatic):** sudden decrease in long-range PLV or rigid local hypersynchrony, disturbed HEP, subjective "nothing" / dissociation

---

## 7. CONTROLS AND BEST PRACTICES

- Randomization of block order when possible
- Blinded scoring of subjective reports
- Recording of skin temperature, lighting, noise level
- For repeated studies: same time of day, same operator
- Pre-registration of protocol (recommended)

---

## 8. FIELD VERSION / LOW-COST (If Needed)

- 8-16 channel EEG (OpenBCI / Neurosity / similar) + Polar H10 or Movesense ECG + breath belt
- LSL for synchronization
- Offline analysis with same methods (with limited spatial resolution)

---

## FALSIFICATION

This protocol fails if:

1. **No correlation between subjective reports and objective markers:** Participants who report Class II/III experiences do not show corresponding EEG/HRV patterns (high PLV, high HRV, strong HEP).

2. **No correlation between $\theta$ proxies and PLV:** Individuals with high subjective $\theta$ (resting breath ≤8/min, good sleep quality, calm gut) do not show higher PLV than individuals with low subjective $\theta$.

3. **No environmental modulation:** Participants in low phase-noise environments (forest, silence) do not show different EEG/HRV patterns than participants in high phase-noise environments (city, screens).

4. **Pharmacological reproduction without phase correlate:** If pharmacological substances (DMT, psilocybin) produce Class II/III experiences without corresponding EEG/HRV patterns, then APT classification is a neurochemical artifact, not a phase phenomenon.

5. **Q-Core / UNIT 02 does not detect:** If LifeNode sensors do not register any phase anomaly during moments when participants report APT experiences — no physical correlate = no physical phenomenon.

---

**SEE ALSO:**
- [XPT-002: Taxonomy](../DOSSIERS/XPT-002_TAXONOMY.md) — APT classes
- [XPT-004: Protocols](../DOSSIERS/XPT-004_PROTOCOLS.md) — regulation protocols
- [24H Diagnostic](../PROTOCOLS/24H-DIAGNOSTIC.md) — subjective version of the same
- [EVIDENCE folder](../EVIDENCE/) — where measurement results will be stored

---

**STATUS:** Research protocol v0.1. Requires laboratory validation.
