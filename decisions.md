# Decision log — Voice Arena diarization evaluation

Running record of decisions locked during execution. Each entry states the decision, the rationale, and where it came from. Later tasks and the final PDFs reference this file as the source of truth.

---

## T01 — Scope and framing (LOCKED)

### 1. The two labelled scopes

| Scope | What we produce |
|---|---|
| **Proposed production benchmark** | Complete design: data collection, annotation, scoring, fair comparison, statistical analysis, leaderboard publication. |
| **Measured pilot** | Three open systems on 24 recordings (~2 hours). Findings apply to this sample only. |

Model training and a deployed leaderboard are **out of scope**. The submission explains decisions, shows evidence, and acknowledges uncertainty.

### 2. The three questions the leaderboard answers

1. **Accuracy** — does the system correctly identify who spoke when?
2. **Speaker coverage** — does it preserve people who speak briefly, especially in crowded conversations?
3. **Practicality** — how quickly does it return useful results, and under what operating conditions?

### 3. The three audiences and the decision each makes

| Audience | Decision they make | Slices most relevant to them |
|---|---|---|
| **Meeting-product teams** | Which system to integrate for meeting notes / transcription. | Meetings domain; overlap; many-speaker and crowded recordings. |
| **Call-analytics buyers** | Which system to buy for call-center analytics. | Telephone domain; short turns and backchannels; noise; 2-party and multi-party calls. |
| **Multilingual voice-product teams** | Which system handles their target languages well. | Indic languages; code-mixing; accented English; interview/media domain. |

### 4. Indian multilingual — named emphasis (framing locked)

> We give Indian multilingual speech a dedicated, clearly-labelled emphasis **within** a general-purpose leaderboard. We do this because accuracy, speaker coverage, and practicality diverge most sharply from English-only benchmarks exactly where speech is multilingual and code-mixed, and because recent benchmarks (Indic DiarBench, Anuvani-Diarization, DISPLACE) now make a rigorous multilingual comparison feasible.

- It is an **emphasis, not a replacement** for the general-purpose leaderboard — the English and multi-domain core remains intact and equally weighted.
- Every Indic claim is reported as a labelled slice/cell; no Indic result is silently pooled into a headline.

### 5. Constraints (confirmed)

- **5 working days**, ~38 focused hours.
- **Free tools** only; **Kaggle GPU** execution.
- Broad product coverage **with** explicit Indian multilingual analysis (per §4 above).
- Four deliverables: main PDF, one-pager PDF, leaderboard sketch, 2-minute video — plus the four reflection answers.

**ref:** `plan.md §1`, assignment PDF pages 1–3 and 4–6.

---

## T03 — Model catalog and final pilot set (LOCKED)

### Final pilot set (3 systems)

| # | System | Family | Role |
|---|---|---|---|
| 1 | `pyannote/speaker-diarization-community-1` | Modular (VBx clustering) | Open-source baseline |
| 2 | `nvidia/Nemotron-3-Diarization` | EEND (Sortformer), streaming | Practicality / streaming |
| 3 | `CIIL/Anuvani-Diarization` | EEND (DiariZen-derived), Indic-adapted | Indic-multilingual |

This gives **one modular + two EEND (one Indic-adapted)** — covering the architecture axis and the Indic emphasis with a minimal, installable set.

### Rejected candidates (with reasons)

- **DiariZen `md-v2`** — install blocked: Python 3.10 + torch 2.1.1 + vendored pyannote 3.1; Kaggle has no conda/mamba. Its EEND architecture is still represented via Anuvani (its Indic fine-tune).
- **3D-Speaker CAM++ (FunASR)** — installable and runs, but its ASR-coupled diarization collapsed a 6+ speaker conversation to 1 speaker; not worth tuning within budget when 3 systems already cover the axes.

### Live access-check results (97.6s sample)

- community-1 → 9 speakers · Nemotron → 6 · Anuvani → 7. The speaker-count divergence is the "Beyond DER" failure surfaced live, to be reused in the failure analyses (T10).
- Kaggle environment fixes locked: numpy purge + `numpy>=2.3`, pin `torch<2.15 torchvision<0.27`, feed WAV/FLAC (not mp3) to pyannote.

**ref:** `model-catalog.md`.

---

## T04 — Metric contract and fairness rules (LOCKED)

Frozen in `metrics.md` before any inference.

### Headline scoring
**DER (primary), zero collar, overlap included, unknown speaker count.** A separate 250 ms collar sensitivity result sits alongside. Overlap-capable outputs preserved (pyannote *regular*, not "exclusive" mode). Speaker counts taken from labels with positive activity inside scoring regions.

### Companion metrics
JER · exact speaker-count accuracy · count MAE + signed bias · overlap-only DER · DER components (missed / false-alarm / confusion) · RTF + speed factor.

### Low-activity-speaker diagnostic (ours, proposed)
Low-activity = **≤5% of reference speaker-time** and **≥0.5 s** of speech; recovered when **≥50%** of their reference speech overlaps the optimally-matched hypothesis speaker. Published with a threshold-sensitivity sweep (activity {3,5,10}% × duration {0.4,0.5,0.75}s). Labelled a proposed diagnostic, not an established metric.

### Fairness rules (frozen)
Identical 16 kHz mono + scoring regions · no reference leakage (transcripts, identities, counts) · frozen defaults with separate dev audio · no reference-driven correction · exposure disclosure (known overlap / declared disjoint / unknown) · offline vs streaming separated · failed/unsupported runs recorded explicitly (incomplete ⇒ coverage only, no full rank).

### Timing rule (hard)
**Self-hosted, cloud-API, and on-device timing never share a single speed ranking.** The three self-hosted pilots share one RTF table; APIs/on-device go in a separate view.

### Aggregation + statistics
Headline = equal-weight average over 8 domain×language cells; conventional global pooling + per-cell also published; cross-corpus aggregates labelled exploratory. Paired bootstrap (10k resamples, fixed seeds, 95% intervals), multiple-comparison adjustment, and a predeclared **≥1 pp DER** threshold for a practically meaningful win.

**ref:** `metrics.md`.

---

## T05 — Production dataset and annotation convention (LOCKED)

Design proposal written to `dataset.md`. The pilot itself is unaffected — it uses pre-existing corpora (T06).

### 60 h composition
- **12 h public dev** (licensed public) + **48 h private eval** (newly collected, consented).
- **Four domains** (meetings, telephone, interviews/media, informal), 15 h each, **equal English/Indic (7.5 h each) per domain**.
- **Six Indic languages**, balanced globally: Hindi, Bengali, Marathi, Tamil, Telugu, Kannada → 5 h each (1 h dev / 4 h eval). Code-mixed conversations tagged as their own slice.

### Quotas + split integrity
- **≥25% of eval recordings (by count) and eval duration** must have **5+ speakers**; low-participation (≤5% speaker-time) speakers flagged in metadata.
- Split by **source conversation and speaker group** (no speaker spans dev+eval); alternate mics of a session kept together.

### Annotation convention (one unified convention)
Pauses excluded · overlap labelled independently (per-speaker tracks) · brief backchannels retained · non-speech vocalizations (laughter/cough/singing) on a separate track. Boundary target ±50 ms after adjudication.

### Quality process
Two independent annotators → agreement measured **before** adjudication (inter-annotator DER, speaker-count agreement, boundary agreement) → adjudication by a senior annotator → handbook checks (boundaries, overlap, identity, count). Agreement reported explicitly, never post-hoc inflated.

### Why this matters to the pilot
The pilot uses native corpus references, so it reports per-corpus first and runs a T10 annotation audit (re-label 6 excerpts under this convention) as a small test of the convention-sensitivity claim.

**ref:** `dataset.md`.

---

## T06 — Pilot manifest (24 recordings, LOCKED)

Frozen in `manifest.md` before any prediction is inspected. All identifiers verified live on 2026-11-10.

### Composition
- **12 Indic DiarBench** (`sarvamai/indic-diarbench`, test split, CC BY 4.0) — 2 per language (Hindi, Bengali, Marathi, Tamil, Telugu, Kannada); per language one crowded **near-field** sample + one crowded **in-the-wild** sample from a *different* meeting (independent speaker groups).
- **6 AMI** single-distant-mic (`SDM`), `only_words` references — EN2002a, ES2004a, IS1009a, TS3003a (test) + ES2011a, IS1008a (validation), six distinct speaker groups.
- **6 VoxConverse** dev, ≥5 speakers — `cjfer`(15), `fkvvo`(9), `aisvi`(8), `eziem`(8), `bdopb`(7), `eapdk`(7).

### Rules + targets
- **Excerpt rule:** every file truncated to first 300 s; scoring region = that window; references clipped to it. Files ≤300 s use whole length.
- **Crowded (≥5 spk):** 18 of 24 (all Indic + all VoxConverse) ≫ target 6. Overlap target ≥6 expected met (Indic avg 12.8%; VoxConverse overlap-selected), verified against references at T08.
- **Checksums** computed at download (T08) and written back; cannot precede audio fetch.
- **Fallback 12** predefined and balanced (6 Indic near-field, 3 AMI, 3 VoxConverse).

### Exposure flags recorded
Anuvani = known overlap on Indic DiarBench; community-1 = known overlap on AMI + VoxConverse; the rest unknown.

**ref:** `manifest.md` (full Indic metadata in `scripts/indic_metadata.json`; extraction via `.venv-meta` pyarrow/fsspec).

---

## T07 — Scoring harness and validation (LOCKED)

Built in `harness/` (Python 3.11 venv `.venv-harness`). **25/25 tests pass.**

### Stack
- **Primary scorer:** `pyannote.metrics 4.2.0` (`DiarizationErrorRate`, `JaccardErrorRate`) under locked settings (collar 0, `skip_overlap=False`, unknown count).
- **Cross-check:** `nryant/dscore` (DIHARD reference scorer) vendored at `third_party/dscore` — the same tool Indic DiarBench cites (`e02f949`).

### What it computes
DER (primary) · JER · DER components (missed / false-alarm / confusion) · overlap-only DER · speaker counts · exact-count accuracy / MAE / signed bias · low-activity-speaker recall (≤5% & ≥0.5 s; ≥50% overlap recovery) · 250 ms collar sensitivity.

### Validation (plan.md §5 fixtures) — all hand-computed, all pass
perfect (0/0) · permuted labels (0/0) · missing brief speaker (DER 2.44%, JER 50%, count −1, low-activity recall 0) · merged speakers (50% conf) · split speaker (50% conf) · overlap-perfect (0) · silence false-alarm (50%) · empty hypothesis (100%) · invalid timestamps rejected (ValueError).

### Cross-check result
`pyannote.metrics` and `nryant/dscore` agree on DER (≤2%) and JER (≤3%) for every fixture. **Key finding:** nryant reports DER/JER in *percent* (0–100), pyannote in *fractions* (0–1) — `crosscheck.py` normalizes by ÷100.

### Interface (T09-ready)
`pipeline.run_manifest(manifest, ref_loader, hyp_loader)` → per-recording + aggregate; `manifest.json` is the machine-readable 24-row manifest. Zero-collar-vs-250 ms collar sensitivity demonstrated (50 ms boundary shift scored at 0 collar, forgiven at 250 ms).

**ref:** `harness/` (`README.md`), `metrics.md` (contract).

---

## T08 — Smoke tests + first pilot subset (LOCKED)

### References extracted + validated (24/24)
- **Indic (12):** `annotated_transcript` → RTTM (`scripts/extract_indic_references.py`). Found + fixed a bug: in-the-wild samples label speakers as `"Speaker A"`, `"New speaker A"` — spaces broke RTTM's whitespace fields and collapsed 8 speakers to 2. Sanitized (`_`.join) → all 12 now match the dataset's `num_speakers` exactly.
- **AMI (6):** official BUTSpeechFIT `only_words` RTTM (canonical reference, no account needed).
- **VoxConverse (6):** official `dev/*.rttm`; speaker counts 7–15 match manifest.

### Reference audit (T06 targets verified against real references)
- **Crowded (≥5 spk): 18/24** · **substantial overlap (≥5%): 15/24** · total speech 249 min.
- Excerpt `[0,300]` retains most speakers; only TA-02 drops 6→3 in-window (honest note).

### AMI source settled (no account needed)
`diarizers-community/ami` mirror = **same AMI** (verified: `Array1-01` SDM, `only_words` refs, same 16-meeting partition, matching speaker IDs). **Audio** served publicly at `groups.inf.ed.ac.uk/ami/AMICorpusMirror/.../{M}.Array1-01.wav`. **References** = official GitHub RTTM (not the mirror's possibly-transformed segments).

### Audio-source map (for T09)
AMI = direct public URL · VoxConverse = KAIST `voxconverse_dev_wav.zip` · Indic = embedded in parquet (extract locally or on Kaggle).

### Pins (→ `pins.md`)
community-1 = `pyannote.audio>=4.0.1` + `torch<2.15` + `numpy>=2.3`; Nemotron = `transformers` (logits → RTTM post-processing needed); Anuvani = `anuvani_diar` wheel 1.0.0. Shared Kaggle fixes (numpy purge, torch pin, WAV-not-mp3).

### Smoke test (full loop proven)
`run_community1.py` (reusable template: download audio → run → write RTTM + timing) on **ES2004a** (17.5 min, GPU): load 4.5 s, infer 71.4 s (RTF ≈ 0.07), **DER 25.23% / JER 30.17%**, 4/4 speakers, overlap-DER 83.4%. Checksum `97d1ac3b…235bfd`. Result saved at `data/hypotheses/community-1/AMI-01.rttm`.

**ref:** `pins.md`, `scripts/extract_indic_references.py`, `scripts/audit_references.py`, `kaggle/pilot-runs/run_community1.py`.

---

## T09 — Full pilot runs + scoring (LOCKED)

### Execution
- All **72 units** (3 systems × 24 recordings) completed on Kaggle (T4 ×2) via the
  notebook `ayuwat/notebookb62243b3c5` → `run_pilot.main()`, **0 errors**. Raw output
  merged from `diarizbench_output.zip` into `data/hypotheses/<system>/` +
  `data/runs/timing/<system>/` by `scripts/t09/merge_output.py` (same done-rule as
  the orchestrator: `status=="ok"` + non-empty RTTM).
- **Env fix final:** `numpy>=2.5,<2.6` + `numba>=0.67` resolved together (numba 0.67 is
  the first to accept numpy 2.5) + end-of-install `--force-reinstall --no-deps numpy`
  safety net. Earlier attempts (`numpy<2.3`, `numba>=0.60`) both backfired — the first
  produced a broken `numpy.ufunc` state, the second let pip downgrade numpy back to the
  broken 2.1.3. Anuvani's wheel is self-contained (survived every breakage).
- **Nemotron run streaming/chunked** (`max_position_embeddings=5000` ≈ 50 s makes
  single-forward unsafe on long AMI meetings); 8-speaker hard cap confirmed live.

### Timing (wall-clock inference, 16 kHz mono, T4 ×2)
| System | load (s) | total infer (s) | RTF |
|---|---|---|---|
| community-1 | 0.52 | 886.3 | 0.072 |
| nemotron | 0.64 | 978.7 | 0.080 |
| anuvani | 13.29 | 644.8 | **0.052** |

RTF per corpus: anuvani 0.052/0.053/0.049 (Indic/AMI/VC) — consistently ~1.5× faster
than community-1 and ~1.9× faster than Nemotron.

### Timing panel (warm-up + 3 reps × 6 recordings, same GPU instance) — DONE
| System | load (s) | weighted RTF | per-file RTF range |
|---|---|---|---|
| community-1 | 0.57 | **0.072** | 0.064 (5-min clips) → 0.077 (25-min AMI) |
| nemotron | 0.73 | **0.079** | flat 0.078–0.079 everywhere |
| **anuvani** | 12.98 | **0.053** | 0.051–0.054 everywhere |

- Reps were extremely stable (≤±1%) on every file — the single-run `infer_s` from the
  full pilot matches the panel means within ~1 s, validating those numbers.
- **Structural finding:** Nemotron (streaming, chunked) has a *flat* RTF across file
  lengths; community-1 (modular) degrades from 0.064 → 0.077 as meetings lengthen.
  Anuvani (EEND) is both fastest and flat. → one line in the report: streaming/EEND
  systems hold constant RTF; modular pipelines do not.
- Anuvani's 13 s load is the DiariZen model load + two-GPU self-test (excluded from RTF).
- Panel data: `data/runs/timing/<system>/panel.json`, `panel_summary.json`.

### Scoring (pyannote.metrics, locked settings: zero collar, overlap scored, unknown count)
| System | DER | JER | count-acc | low-activity recall (n=38) | DER @250 ms |
|---|---|---|---|---|---|
| community-1 | 20.4% | 38.6% | 38% | 45% | 16.7% |
| nemotron | 21.6% | 32.5% | **58%** | **61%** | 18.8% |
| **anuvani** | **13.8%** | **29.9%** | 33% | 47% | **10.3%** |

### DER per corpus (equal-weight over recordings)
| System | Indic (12) | AMI-SDM (6) | VoxConverse (6) |
|---|---|---|---|
| community-1 | 26.1 | 22.7 | 6.8 |
| nemotron | 25.1 | 29.6 | 6.5 |
| anuvani | **16.5** | **17.5** | **4.9** |

### Speaker-count behaviour (hyp vs ref, in-region counts)
| System | exact | MAE | bias | Indic MAE | AMI MAE | VC MAE |
|---|---|---|---|---|---|---|
| community-1 | 9/24 | 1.17 | −1.17 | 1.83 | 0.50 | 0.50 |
| nemotron | **14/24** | 0.92 | −0.92 | 1.42 | **0.00** | 0.83 |
| anuvani | 8/24 | **0.83** | **−0.58** | **1.08** | 0.67 | 0.50 |

Counts follow `metrics.md §3`: a speaker counts only with positive activity inside the
scoring region. Six files have reference speakers outside the excerpt (declared →
in-region: KN-02 8→7, TA-02 6→3, VC-01 15→13, VC-02 9→8, VC-05 7→6, VC-06 7→6); an
earlier version of this table used the full-recording declared counts (MAE 1.54/1.29/1.21)
and was corrected at T11 to the contract definition.

### Headline findings (for T10/T11)
1. **Anuvani wins DER decisively** (13.8 vs 20.4/21.6) and is fastest — the Indic
   specialist also leads AMI-SDM and VoxConverse here.
2. **Harness validation:** anuvani's Indic DER **16.5%** matches its published card
   (16.78) almost exactly; community-1's 26.1 is in the ballpark of its 21.22 (excerpt
   selection + equal-weight vs duration-weight). Confirms the scoring contract.
3. **Nemotron's 8-speaker ceiling is now measured**: on VC-01 (13 speakers inside the
   excerpt; 15 across the full recording) it emits 8 while community-1/anuvani reach 13 —
   a −5 count error, the worst single counting miss of the whole run. It does hold the
   best exact-count hit rate (14/24, mostly on 4-speaker AMI), so the cap coexists with
   many small wins.
4. **community-1 systematically under-counts Indic** (MAE 1.83, bias −1.83) — the
   "beyond DER" signal the evaluation was built to surface.
5. **Count trade-off (corrected at T11):** Anuvani makes the smallest-magnitude count
   errors (MAE 0.83, bias −0.58) but is exactly right least often (8/24) — a scattering
   of ±1 misses; Nemotron hits exact most often (14/24) yet carries the worst single
   error (−5 on VC-01). Overlap-only DER is high for all three on the crowded files
   (VC-01: 34.2/27.7/40.8; TE-02: 99.8/81.8/91.7 for c1/nemo/anu) and does not track the
   headline DER ranking — systems that under-generate in overlap can look better there
   while missing more elsewhere; an honest caveat for T12 rather than a clean story.

### Caveats recorded
- Per-language Indic DER is noisy (2 recordings/language; Telugu is a single hard file).
- Scorer = `pyannote.metrics` (anuvani's card notes it reads ~0.20 higher than NIST
  md-eval on Indic DiarBench) — note in the write-up, do not fudge.

**ref:** `scripts/t09/{merge_output,score,summarize}.py`, `data/runs/results/*.json`,
`data/runs/summary.json`, `data/runs/diarizbench_output.zip`.

---

## T10 — Failure analyses + annotation audit (LOCKED)

Full detail in `t10_findings.md`; reproducible via `scripts/t10/analyze.py`.

### Three audio-backed failure cases
1. **Brief speaker (`BN-01`)** — ref speaker `SPEAKER_05` (12.87 s, 4.6 % of speech,
   6 interjections) is **dropped by all three systems** (low-activity recall 0/1). Each
   burst is co-located with a dominant speaker, so it's *absorbed* rather than silenced.
   The "beyond DER" point made concrete: DER barely moves, a whole participant vanishes.
2. **Overlap (`TE-02`)** — 3-way overlap at `[97.2–97.7]`; overlap-only DER 100 % / 82 % /
   92 % (c1/nemo/anu). c1 fragments into 0.1–0.3 s slivers; anuvani closest. Overlap is
   where the systems actually separate.
3. **Multilingual/code-mixed (`TA-02` Tamil vs `TE-02` Telugu)** — Tamil itw: c1 29.6
   (confusion 22.1, collapses 3→2) vs anuvani **5.7** — the specialist-vs-generalist
   argument in one number. Telugu (20.4 % overlap, highest): everyone fails (38.6/42.0/38.4)
   — the honest "hard slice" data point.

### Annotation audit (6 excerpts, structural — no audio re-listen)
Three convention gaps that can move DER by points: (1) **overlap labelling** — Indic
16–28 %, AMI word-level 4–20 %, VoxConverse 0.0–8.8 %; (2) **segment granularity** — AMI
word-timed (223 sub-0.5 s segs on AMI-02) vs VoxConverse turn-timed (0–5); (3) **pause
handling** — AMI 68–88 % speech vs Indic ≥100 %. → Confirms per-corpus reporting is
mandatory and the equal-weight aggregate is exploratory. No single reference is defective;
the correction is to the *comparison*, not to any score.

### Failed / unsupported runs
- **Failed:** 0/72. **Missing:** none. Coverage 24/24 × 3 systems.
- **Cap-limited (not a failure):** Nemotron's 8-speaker cap on VC-01 (15) and VC-02 (9).
- Exposure flags disclosed per score (c1 = known overlap on AMI+VC; anuvani = known
  overlap on Indic; nemotron = unknown).

**ref:** `t10_findings.md`, `scripts/t10/analyze.py`.

---

## T11 — Statistics, figures, experiment freeze (LOCKED)

Reproducible via `scripts/t11/{statistics,figures}.py`; data in
`data/runs/results/statistics.json` + `data/runs/figures/`.

### Pooling (DER %, equal-weight)
| System | global (24) | corpus-equal (3 cells) | Indic | AMI-SDM | VoxConverse |
|---|---|---|---|---|---|
| community-1 | 20.4 | 18.5 | 26.1 | 22.7 | 6.8 |
| nemotron | 21.6 | 20.4 | 25.1 | 29.6 | 6.5 |
| anuvani | **13.8** | **12.9** | **16.5** | **17.5** | **4.9** |

Production uses **8 domain×language cells** (4 domains × English/Indic); the pilot
approximates with **3 corpus cells** (Indic / AMI-SDM / VoxConverse) plus 6 language
slices. Cross-corpus aggregate stays labelled exploratory (T10 audit).

### Paired bootstrap (10,000 resamples, seed 20261111, over 24 independent recordings)
| System | global DER | 95% CI |
|---|---|---|
| community-1 | 20.4 | [15.5, 25.3] |
| nemotron | 21.6 | [15.7, 27.6] |
| anuvani | 13.8 | [10.0, 17.9] |

### Pairwise DER (A vs B; negative = A lower/better)
| Pair | mean Δ (pp) | 95% CI | Bonferroni | ≥1 pp? | verdict |
|---|---|---|---|---|---|
| community-1 vs nemotron | −1.2 | [−4.2, +2.0] | n.s. | yes | **tie** |
| community-1 vs anuvani | +6.6 | [+4.4, +9.1] | sig | yes | **anuvani wins** |
| nemotron vs anuvani | +7.8 | [+4.6, +11.1] | sig | yes | **anuvani wins** |

**Headline:** Anuvani beats both rivals significantly (Bonferroni-corrected) *and* by
more than the predeclared 1 pp threshold (+6.6 and +7.8 pp). community-1 vs Nemotron is a
statistical tie (1.2 pp apart, CI spans zero) — so the only robust claim is
**Anuvani first, then {community-1, Nemotron} indistinguishable**.

### Figures
- `der_components.png` — stacked missed/FA/confusion per system (shows c1+Nemotron
  dominated by missed speech, Anuvani low across all three).
- `count_bias.png` — signed count bias + MAE (all under-count; c1 −1.17 worst,
  anuvani smallest at −0.58).
- `accuracy_speed.png` — DER vs RTF scatter (Anuvani bottom-left = best on both).

### Experiment freeze
Scoring contract, manifest, references, hypotheses, timing, and bootstrap settings are
**frozen** as of this task. No further changes to numbers, settings, or data — the only
remaining work is writing (T12) and packaging (T13/T14).

**ref:** `scripts/t11/{statistics,figures}.py`, `data/runs/results/statistics.json`,
`data/runs/figures/*.png`.

---

## T12 — Main document (LOCKED)

Source `docs/main.md`, renderer `scripts/t12/build_main.py`, output
`submission/Q1_Main.pdf`. **21 pages: title, contents, 16 pages of body (3–18),
then references + 3 appendices (19–21).** Numbers verified by
`scripts/t12/verify_numbers.py`: **65/65 claims match the saved artefacts.**

### Structure (maps 1:1 to the assignment checklist)
| § | Covers |
|---|---|
| Exec summary | result, the one supported claim, what the headline hides, 3 decisions, biggest limitation |
| 1 | purpose, primary/secondary audience, what the doc is *not* |
| 2 | two scopes (designed vs measured), research→decision table, 6 frozen fairness rules |
| 3 | 24 recordings, scoring regions/excerpt policy, reference conventions + the RTTM speaker-field bug |
| 4 | metric definitions in plain words, frozen settings table, 9 fixtures / 25 tests |
| 5 | 3 systems with exact repo IDs, 2 rejected systems, **Nemotron streaming deviation** |
| 6 | resumable pipeline, 3 environment failures, timing protocol |
| 7 | main table, per-corpus, Indic languages, components, counting, low-activity, overlap, collar, speed |
| 8 | paired bootstrap + Bonferroni + 1 pp threshold → what a "win" means |
| 9–10 | 3 failure analyses; 6-excerpt annotation audit |
| 11–13 | hypotheses vs observations, threats to validity, pilot→production leaderboard |
| 14 | the four required reflections |
| A–C | reproducibility map, all 72 units, number provenance + freeze statement |

### Uncertainty added post-freeze (disclosed, no headline changed)
`scripts/t12/uncertainty.py` → `data/runs/results/uncertainty.json`: Wilson CIs for
count accuracy, **recording-clustered** bootstrap for low-activity recall (speakers nested
in recordings, so Wilson would be too narrow), the contract-mandated 3×3 low-activity
threshold grid, and JER intervals + Bonferroni CIs. `metrics.md` required all of these and
T11 published none of them; adding them changes no point estimate.

### Verification (`scripts/t12/verify_numbers.py`)
Recomputes each headline from `<system>.json` + manifest + timing panel, asserts agreement
with `statistics.json`/`uncertainty.json`, then asserts the formatted string appears in the
rendered PDF text. 6/6 recomputations agree; 65/65 claims found. It caught two real defects:
- The 5-minute wall-clock and speed-factor figures had been derived from the *rounded* RTF,
  so a reader recomputing from the saved data got a different last digit. Corrected to full
  precision (22.1 / 24.3 / 29.0 s; 18.8×), not the other way round.
- Table 1's count-accuracy cell mixed `9/24` and `38% [21, 57]`; now split so both are
  independently checkable.

### Renderer decisions
Markdown → reportlab (no LaTeX/browser dependency; reproducible on any machine with Python).
Georgia for prose, Helvetica for headings/tables. Directives: `[[toc]]`, `[[fig:…|caption]]`,
`[[widths:…]]`, `[[kpi:…]]`, `[[space:mm]]`, `^ caption`. Tables and figures are wrapped in
`KeepTogether` with their captions; `CondPageBreak` stops orphaned headings; `allowWidows=0`
kills the one-line widow seen in draft 1. `multiBuild` resolves the TOC page numbers.

**ref:** `docs/main.md`, `scripts/t12/{build_main,uncertainty,figures_doc,verify_numbers}.py`,
`submission/Q1_Main.pdf`, `data/runs/results/uncertainty.json`.

---

## T13 — Leaderboard sketch + governance (LOCKED)

`scripts/t13/build_sketch.py` → `docs/leaderboard.html` → `submission/Q1_Leaderboard.pdf`,
**3 pages**. Every measured value is injected from the saved result files; nothing is typed
by hand. `verify_numbers.py` checks **34/34** rendered claims.

### Page 1 — overview (the product surface)
- Filter row: domain, language, speaker count, overlap, view, and an offline/streaming
  segmented control. Default view = all modes, rows labelled.
- Ranked table: rank, model + exact ID, mode chip, **DER with 95% CI and a bar whose whiskers
  are the CI**, JER + CI, exact count, RTF, completion coverage, exposure chip.
- **The tie is rendered as `2=`**, not as an arbitrary 2 and 3. The table refuses to order
  two systems that the statistics call indistinguishable; this is the single most important
  thing the sketch does that a sorted table usually gets wrong.
- Two illustrative rows (cloud API, on-device SDK) with **synthetic values, dashed styling,
  an `ILLUSTRATIVE` chip and no rank**. Deliberate choice: inventing numbers for a *named*
  vendor would be defamatory even when labelled, so the placeholders are generic. The note
  says API wall-clock includes network latency and on-device timing is CPU-only, so neither
  is comparable to self-hosted RTF.
- "Balanced cells" table (3 corpora + corpus-equal, best-in-column marked) so the filter's
  other setting is visible rather than hidden behind a dropdown.
- KPI strip: 24 recordings · 9 languages · 3 systems · 72/72 units · 196 min speech · 0 errors.

### Page 2 — model detail (one row, opened)
Identity + exact repo ID, run conditions (family, mode, hardware, settings, count policy,
licence, exposure), error decomposition stack, speaker coverage with clustered CI and the
3%/10% sensitivity, per-corpus mini-table, speed panel (RTF, ×real-time, load, 5-min
end-to-end, 11-min break-even), a comparison strip against the other two systems, and two
example failures — including the one where **Anuvani also drops the brief speaker**.

### Page 3 — governance
- **Curated vs bring-your-own.** Curated = pinned checkpoint, documented defaults, exposure
  declaration, complete run, independent reproduction. BYO = separate unranked track,
  self-reported until reproduced, and it *moves* track rather than merging.
- Six-step lifecycle: submit › triage › run › score › review › publish.
- **Re-scoring rule:** version the reference (never edit), full re-score of every system,
  publish old/new/delta, bump the protocol version only when a *setting* changes.
- Versioning/archival: every row carries protocol version, reference version, pinned
  revision, run date, hardware, artefact hash; old boards archived read-only; never a
  silent re-rank. Cadence: quarterly full refresh, monthly intake, out-of-cycle on
  reference correction.
- Example change log (3 rows) so the rules are concrete, and an explicit out-of-scope list
  (SA-WER, language diarization, live streaming latency).

**ref:** `scripts/t13/build_sketch.py`, `docs/leaderboard.html`, `submission/Q1_Leaderboard.pdf`.

---

## T14 — One-pager, video script, QA, packaging (LOCKED)

### One-pager
`scripts/t14/build_onepager.py` → `docs/onepager.html` → `Ayush_Kumar_Q1_OnePager.pdf`,
**exactly one page**. Same palette and typography as the main report (Georgia body,
Helvetica headings) so the two read as one artefact. Contents in order: purpose, setup,
principal finding with the three-row table, the claim box, three decisions, limitation,
"what would change my mind", deliverable footer. Numbers injected from the same JSON as
everything else. The rank column shows `1`, `2=`, `2=` — the tie is never silently ordered.

### Video script
`docs/video_script.md`: 8 shots, 110 seconds, 268 words of narration at ~145 wpm, with the
exact PDF page to show for each beat. Recording is the user's step; the link goes in
`submission/VIDEO_LINK.txt`.

### Packaging
`scripts/t14/package.py --name "First Last"` rebuilds the main report and one-pager with that
name in the header and title page and copies the sketch, so the filenames match the required
`Firstname_Lastname_Q1_*` convention. Generic working copies are removed so there is exactly
one file per deliverable.

### Final QA (`scripts/t14/qa.py`) — 44 passed, 0 failed, 1 expected warning
- Files exist, open, and yield extractable text (not scanned images).
- Page budgets: main 21 (16 body + references/appendix), one-pager exactly 1, sketch 3.
- Main covers all 18 required beats: purpose, models, test data, metrics, process, how a win
  is declared, results, threats, production plan, the four reflections, references, and the
  three appendices.
- All three exact repository IDs appear; the `72/72` completion claim is present; the
  streaming deviation is disclosed in §5.3.
- One-pager covers purpose / setup / finding / decisions / limitation.
- Sketch covers the overview table, model detail, governance, curated-vs-BYO, re-scoring,
  versioning, and the illustrative-row label.
- Number provenance delegated to `scripts/t12/verify_numbers.py` (65 main + 34 sketch claims).
- The one warning is the missing video URL, which only the user can supply.

**ref:** `scripts/t14/{build_onepager,qa,package}.py`, `docs/{onepager.html,video_script.md}`,
`submission/`.

### Final layout fix
The one-pager footer wrapped onto a second line once the real filenames
(`Ayush_Kumar_Q1_Main.pdf`, `Ayush_Kumar_Q1_Leaderboard.pdf`) replaced the working
names. Shortened the left string and fixed the right string with `white-space:nowrap`,
so both sides sit on one line and the page stays exactly one page.

### Final state
`submission/` holds exactly three PDFs plus `README.md` and `VIDEO_LINK.txt`. Generic
`Q1_*.pdf` working copies removed. `scripts/t14/qa.py`: **44 passed, 0 failed, 1 expected
warning** (video URL). `scripts/t12/verify_numbers.py`: **65/65 main + 34/34 sketch**.
