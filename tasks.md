# Voice Arena diarization evaluation — task sheet

This sheet breaks [`plan.md`](plan.md) into sequential tasks. Work top to bottom, one task at a time. Each task states its main aim, what the work actually is, and where in `plan.md` to find the full detail.

**Convention:** `ref: plan.md §N` points to the numbered section of `plan.md`. Where useful, a sub-label in parentheses (e.g. `§4 (Systems)`) narrows it further.

**Pre-verified before starting:** all three pilot model IDs and the catalog additions in `plan.md §2`/`§4` were checked against Hugging Face and vendor docs. They are all real; carry the recorded licensing/speaker-cap notes into the catalog (see T03). Two candidates (DiariZen, CAM++) were evaluated and rejected — see `model-catalog.md`.

---

## Task index

| # | Task | Aim | Phase (Day) |
|---|---|---|---|
| T01 | Lock scope and framing | Fix the two-scope framing and position the Indic emphasis | 1 |
| T02 | Research evidence table | Turn every key paper into a concrete design decision | 1 |
| T03 | 12-entry model catalog + access checks | Verify and document each system; confirm the three pilots run | 1 |
| T04 | Freeze metric contract and fairness rules | Lock scoring, settings, and fairness before any inference | 1 |
| T05 | Production dataset and annotation convention | Specify the 60h collection and reference-quality process | 2 |
| T06 | Pilot manifest (24 recordings) | Fix the exact audio, references, and scoring regions | 2 |
| T07 | Scoring harness and validation fixtures | Build the RTTM→score pipeline and prove it correct | 2 |
| T08 | Smoke tests + first pilot subset | Get all systems producing RTTM on real audio | 2 |
| T09 | Full pilot runs and timing panel | Run everything reproducibly and measure speed | 3 |
| T10 | Failure analyses and annotation audit | Produce the three audio-backed failure cases + convention audit | 3 |
| T11 | Statistics, figures, and experiment freeze | Compute intervals and plots; stop changing things | 3 |
| T12 | Main document + reflections | Write the submission PDF end to end | 4 |
| T13 | Leaderboard sketch + governance | Design the product view and its operating rules | 4 |
| T14 | One-pager, video, QA, submission | Package and verify every deliverable | 5 |

---

## Day 1 — Foundations

### T01 — Lock scope and framing
**Aim:** fix the exact shape of the submission before any other work.
- Re-read the assignment PDF and `plan.md §1`. Confirm the two labelled scopes: **proposed production benchmark** vs **measured pilot**.
- Confirm the three audiences and the three questions the leaderboard answers (accuracy, speaker coverage, practicality).
- Position Indian multilingual as a **named product emphasis** alongside the general-purpose leaderboard — one framing sentence, not a scope rewrite. Record the emphasis and its rationale in the main document's purpose section.
- Confirm the agreed constraints: 5 days, ~38 hours, free tools, Kaggle GPU.

**ref:** `plan.md §1`, assignment PDF pages 1–3.

### T02 — Research evidence table
**Aim:** turn each source into a design decision, not just a citation.
- Build the table from `plan.md §2 (Turn the papers into design decisions)`: for each paper record **protocol → relevant finding → limitation → decision it informs**.
- Ensure these seven are covered: Beyond DER, Indic DiarBench, SDBench/OpenBench, DIHARD III, Anuvani-Diarization, Benchmarking Diarization Models, and DISPLACE + the diarization review.
- Capture the three headline findings explicitly: (1) duration-weighted DER hides dropped low-activity speakers, (2) annotation conventions can move DER by several points, (3) accuracy and speed must be reported together.

**ref:** `plan.md §2` (research priorities and "Additional core references").

### T03 — 12-entry model catalog + access checks
**Aim:** a verified, comparable record of every system.
- Fill the catalog from `plan.md §2 (Define users and system coverage)`: the three pilots plus Precision-2, Deepgram, AssemblyAI, Amazon Transcribe, Google Cloud STT, Speechmatics, Picovoice Falcon, and SpeakerKit.
- For each entry record: organization, exact published identifier, version/access date, delivery mode, offline/streaming, languages, speaker limits, overlap support, licensing, and whether diarization requires a transcription workload.
- Add the three review columns: **licensing** (e.g. DiariZen weights are CC BY-NC 4.0), **speaker/overlap caps** (Nemotron = 8 speakers; DiariZen = 4 simultaneous), and **delivery-mode taxonomy** (self-hosted vs cloud API vs cloud STT vs on-device SDK).
- State explicitly where an API hides its model version.
- **Access checks:** confirm each of the three pilots can be loaded and run on the available Kaggle GPU — tokens and gated conditions for `pyannote/speaker-diarization-community-1` in particular.

**ref:** `plan.md §2`, `plan.md §4 (Systems)`.

### T04 — Freeze metric contract and fairness rules
**Aim:** lock scoring and fairness before any inference runs.
- Write out the metric table from `plan.md §3 (Lock the metric contract)`: DER (primary), JER, exact speaker-count accuracy, count MAE + signed bias, low-activity-speaker recall, overlap-only DER + DER components, and RTF/speed factor.
- Fix the low-activity definition: ≤5% of reference speaker-time, ≥0.5s of speech, recovered if ≥50% of their speech overlaps the matched hypothesis; include a threshold-sensitivity check.
- Lock scoring settings: **zero collar, overlap included, unknown speaker count** for the headline; a 250 ms collar sensitivity result alongside.
- Write the fairness rules (`plan.md §3 (Keep comparisons fair)`): identical 16 kHz mono + scoring regions, no reference leakage, frozen defaults, no reference-driven correction, exposure disclosure, offline/streaming separation, explicit recording of failed/unsupported runs.
- Add the explicit rule that **self-hosted, cloud-API, and on-device timing never share a single speed ranking**.

**ref:** `plan.md §3`.

---

## Day 2 — Data and scaffolding

### T05 — Production dataset and annotation convention
**Aim:** specify the 60-hour benchmark design and its reference process.
- Document the 60h split (12h public dev / 48h private eval), four domains, equal English/Indic duration, and the six Indic languages from `plan.md §2 (Design the production dataset)`.
- Record speaker counts, overlap, turn lengths, microphone conditions, noise, accents, and code-mixing; reserve ≥¼ of eval recordings for 5+ speakers and separately flag low-participation speakers.
- Define the acoustic annotation convention (pauses excluded, overlap labelled independently, brief backchannels retained, non-speech vocalizations documented separately) and the two-annotator + adjudication quality process with agreement reporting.

**ref:** `plan.md §2`.

### T06 — Pilot manifest (24 recordings)
**Aim:** fix exactly what audio will be scored, before any prediction is inspected.
- Select 24 independent source recordings per `plan.md §4 (Recordings)`: 12 Indic DiarBench (2 × 6 languages), 6 AMI single distant mic, 6 VoxConverse (prefer ≥5 speakers).
- Use one deterministic excerpt ≤5 minutes per source; define counts and activity against that excerpt's reference.
- Target ≥6 crowded and ≥6 substantial-overlap excerpts; publish any unmet target.
- Build the manifest with: source, split, timestamps, language, reference, scoring regions, and audio checksum. **Predefine the balanced 12-recording fallback subset now.**

**ref:** `plan.md §4 (Recordings)`.

### T07 — Scoring harness and validation fixtures
**Aim:** a correct, reproducible RTTM→score pipeline.
- Implement the `manifest → model inference → hypothesis RTTM → scoring → tables/figures` interface from `plan.md §4 (Execution and evidence)`.
- Use `dscore` and `pyannote.metrics` under matching settings and cross-check selected DER/JER values.
- Validate against the fixture list in `plan.md §5`: perfect output, permuted labels, missing brief speaker, merged/split speakers, overlap, silence false alarms, empty hypotheses, invalid timestamps.

**ref:** `plan.md §4`, `plan.md §5 (validation)`.

### T08 — Smoke tests + first pilot subset
**Aim:** get every system producing RTTM on real audio.
- Pin checkpoint revisions and dependencies for the three pilots; resolve environment conflicts with isolated Kaggle environments.
- Run each system on a small subset and confirm RTTM output, timing capture, and log/status recording.
- Checkpoint after each recording so completed work never needs rerunning.

**ref:** `plan.md §4 (Execution and evidence)`, `plan.md §4 (Time limits and fallback)`.

---

## Day 3 — Execution and analysis

### T09 — Full pilot runs and timing panel
**Aim:** complete, reproducible inference with honest speed numbers.
- Run all systems on the full manifest, preserving config, checkpoint revision, raw output, normalized RTTM, timing, status, and logs per run.
- Run the timing panel: one warm-up + three timed repetitions on a fixed six-recording panel, same GPU; report model loading separately and state exactly what the timed execution includes.
- Report RTF (not "streaming responsiveness" from offline throughput); apply the 1h/model and 12 GPU-hour budgets and the fallbacks if needed.

**ref:** `plan.md §4 (Execution and evidence)`, `plan.md §4 (Time limits and fallback)`.

### T10 — Failure analyses and annotation audit
**Aim:** expose failure cases, not just aggregate scores.
- Produce the three audio-backed failure analyses: brief speaker, overlap, and multilingual/code-mixed conversation.
- Run the annotation audit on six short reference excerpts and report diagnostic corrections separately.
- Record, per `plan.md §3`, failed/unsupported/missing runs explicitly (incomplete systems get coverage info, no full rank).

**ref:** `plan.md §4 (Execution and evidence)`.

### T11 — Statistics, figures, and experiment freeze
**Aim:** turn results into trustworthy claims, then stop changing things.
- Compute pooled DER per the eight domain × language-group cells with equal weights, plus conventional global pooling and per-cell results.
- Run paired bootstrap resampling (10,000 resamples, fixed seeds) over independent source conversations; publish 95% intervals and adjust pairwise winner claims for multiple comparisons.
- Apply the predeclared 1 percentage-point DER improvement for a practically meaningful win.
- Generate DER-component, counting-error, and accuracy-speed plots. **Freeze experimentation at the end of Day 3.**

**ref:** `plan.md §3 (Keep comparisons fair)`, `plan.md §4 (Execution and evidence)`.

---

## Day 4 — Writing

### T12 — Main document + reflections
**Aim:** the submission PDF that covers every assignment requirement.
- Write `Firstname_Lastname_Q1_Main.pdf` covering purpose, models, test data, metrics, and evaluation process (target 12–16 pages plus references/appendix).
- End with the four reflection answers from `plan.md §5`: least-sure design choice, most influential benchmark, misleading-leaderboard risks and guards, and what you'd improve with more time.
- Verify no proposed experiment is presented as completed, and every published number traces to a saved result.

**ref:** `plan.md §5 (Deliver and validation)`, assignment PDF pages 4–6.

### T13 — Leaderboard sketch + governance
**Aim:** the product view plus its operating rules.
- Build the main table (model/version, DER with uncertainty, JER, count accuracy, speed, completion coverage) with filters for domain, language, speaker count, overlap, and operating mode.
- Add the model-detail view (error components, counting bias, low-activity recall, hardware, settings, exposure, example failures) and the accuracy-speed scatterplot.
- Add the governance/operations subsection: how new systems are added (curated vs bring-your-own), how re-scoring works when references are corrected, and versioning/archival + update cadence. Label illustrative production rows explicitly.

**ref:** `plan.md §3 (Design the leaderboard sketch)`.

---

## Day 5 — Packaging

### T14 — One-pager, video, QA, submission
**Aim:** package and verify all four deliverables.
- Write `Firstname_Lastname_Q1_OnePager.pdf` (exactly one page: purpose, setup, three key decisions, principal finding, limitation).
- Record the video (~110s / ≤2 min: problem, design, three decisions, measured takeaway, limitation); verify playback, duration, and reviewer access.
- Final QA: verify every number traces to saved results, every system has an exact identifier or an explicit version limitation, and all four deliverables exist and open correctly.
- Keep code, manifests, environment locks, and result files as supporting reproducibility material.

**ref:** `plan.md §5 (Schedule, validation, and final package)`.
