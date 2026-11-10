# Voice Arena diarization evaluation: five-day assignment plan

## 1. Goal, scope, and submission strategy

Design a leaderboard that helps product teams answer three questions:

- **Accuracy:** Does the system correctly identify who spoke when?
- **Speaker coverage:** Does it preserve people who speak briefly, particularly in crowded conversations?
- **Practicality:** How quickly does it return useful results, and under what operating conditions?

Complete every requirement in the assignment, supported by a larger reproducible pilot. The [assignment brief](FDE_Take_Home_Assessment_FIRST.pdf) remains the submission contract.

**Agreed constraints:** five working days, approximately 38 focused hours, free tools, Kaggle GPU execution, and broad product coverage with explicit Indian multilingual analysis.

Keep two scopes clearly labelled throughout the submission:

| Scope | What we will produce |
|---|---|
| **Proposed production benchmark** | A complete design for data collection, annotation, scoring, fair comparison, statistical analysis, and leaderboard publication. |
| **Measured pilot** | Four open systems evaluated on 24 recordings, targeting roughly two hours of audio. Findings apply to this sample. |

The submission will explain decisions, show evidence, and acknowledge uncertainty. Model training and a deployed leaderboard are outside this assignment's implementation scope.

## 2. Research and methodology decisions

### Turn the papers into design decisions

Create an evidence table recording each source's protocol, relevant finding, limitation, and the decision it informs.

| Research priority | What to extract | Planned application |
|---|---|---|
| **Beyond DER** | Under-counting and low-activity-speaker failures | Require speaker-count metrics and a low-activity-speaker diagnostic alongside DER. |
| **Indic DiarBench** | Language coverage, recording conditions, annotation process | Design explicit Indic language and code-mixing slices. |
| **SDBench / OpenBench** | Reproducibility, aggregation, accuracy-speed comparison | Standardize inputs and report measured processing speed with accuracy. |
| **DIHARD III** | Scoring regions, overlap, collar, DER/JER definitions | Establish the scoring contract before inference. |
| **Anuvani-Diarization** | Annotation conventions and pause handling | Document reference conventions and run a separate convention audit. |
| **Benchmarking Diarization Models** | Error decomposition and high-speaker-count analysis | Analyze missed speech, false alarms, confusion, and crowded recordings. |
| **DISPLACE and the diarization review** | Multilingual protocols and technical foundations | Explain system families and distinguish speaker changes from language changes. |

These priorities follow the papers' findings: duration-weighted DER can hide dropped low-activity speakers; Indic DiarBench supplies multilingual conversational coverage; SDBench examines accuracy and speed; and Anuvani shows that annotation conventions can materially affect scores. Sources: [Beyond DER](https://arxiv.org/abs/2609.27315), [Indic DiarBench](https://arxiv.org/abs/2607.23808), [SDBench](https://arxiv.org/abs/2507.16136), and [Anuvani-Diarization](https://arxiv.org/abs/2610.20327).

Additional core references:

- [The Third DIHARD Diarization Challenge](https://arxiv.org/abs/2012.01477)
- [A Review of Speaker Diarization](https://arxiv.org/abs/2101.09624)
- [Benchmarking Diarization Models](https://arxiv.org/abs/2509.26177)
- [The Second DISPLACE Challenge](https://arxiv.org/abs/2406.09494)
- [DISPLACE 2024 evaluation plan](https://displace2024.github.io/docs/DISPLACE2024_Evaluation_Plan_v2.pdf)
- [Argmax OpenBench](https://github.com/argmaxinc/OpenBench)

### Define users and system coverage

Address three audiences: meeting-product teams, call-analytics buyers, and multilingual voice-product teams. Explain the decision each makes and the slices most relevant to it.

Build a **12-entry model/service catalog**, exceeding the required minimum of 10. Research the four pilot systems plus pyannoteAI Precision-2, Deepgram, AssemblyAI, Amazon Transcribe, Google Cloud Speech-to-Text, Speechmatics, Picovoice Falcon, and SpeakerKit.

For every entry, verify official documentation and record:

- Organization, exact published model/service identifier, version or access date.
- Self-hosted/API delivery, offline/streaming operation, and language support.
- Speaker limits, overlap support, licensing, and execution requirements.
- Whether diarization requires an accompanying transcription workload.

Where an API does not expose its underlying model version, state that explicitly and record its configuration and evaluation date.

### Design the production dataset

Propose **60 hours**, comprising 12 public development hours and 48 private evaluation hours.

- Four equally represented domains: meetings, telephone conversations, interviews/media, and informal conversations.
- Within each domain, equal English and Indic duration.
- Indic coverage: Hindi, Bengali, Marathi, Tamil, Telugu, and Kannada, balanced across the overall collection.
- Record speaker counts, overlap, turn lengths, microphone conditions, noise, accents, and code-mixing.
- Reserve at least one-quarter of evaluation recordings for **five or more speakers**; separately identify low-participation speakers.
- Split by source conversation and speaker group; keep alternate microphone recordings of the same session together.
- Use licensed public material for development and newly collected, consented conversations for the private evaluation set.

Specify an **acoustic speech annotation convention**: pauses excluded, simultaneous speakers labelled independently, brief verbal responses retained, and non-speech vocalizations documented separately.

The production annotation process will use two independent annotators, adjudication, a written handbook, and checks for boundaries, overlap, speaker identity, and speaker counts. Report agreement before adjudication.

## 3. Scoring, fairness, and leaderboard behavior

### Lock the metric contract

| Metric | Role |
|---|---|
| **DER** | Primary accuracy metric: missed speech, false alarms, and speaker confusion divided by reference speaker-time. |
| **JER** | Mandatory companion metric that gives reference speakers equal weight. |
| **Exact speaker-count accuracy** | Fraction of recordings with the correct number of speakers. |
| **Speaker-count MAE and signed bias** | Magnitude of counting errors and tendency to under-count or over-count. |
| **Low-activity-speaker recall** | Proposed diagnostic for speakers contributing little speech. |
| **Overlap-only DER and DER components** | Explain where errors occur. |
| **Real-time factor and speed factor** | Processing time/audio duration and its reciprocal. |

For the proposed low-activity diagnostic, define a low-activity speaker as contributing **at most 5% of reference speaker-time**, with at least 0.5 seconds of speech. After one-to-one matching that maximizes reference/hypothesis intersection, count the speaker as recovered when at least 50% of their reference speech overlaps their matched hypothesis. Label this as our diagnostic and include a threshold-sensitivity check.

Use **zero collar, overlap included, and unknown speaker count** for headline accuracy. This follows the strict scoring approach documented by DIHARD III. Add a separate 250 ms collar sensitivity result. Source: [DIHARD III evaluation plan](https://dihardchallenge.github.io/dihard3/docs/third_dihard_eval_plan_v1.2.pdf).

Count predicted speakers from labels with positive activity inside scoring regions. Preserve overlap-capable outputs, including pyannote's regular diarization output rather than its exclusive output.

### Keep comparisons fair

- Supply identical 16 kHz mono waveforms and scoring regions.
- Supply no reference transcripts, speaker identities, or true speaker counts.
- Freeze documented default inference settings before evaluation; use separate development recordings for setup.
- Apply no reference-driven gap filling or system-specific annotation correction.
- Record training-data exposure as **known overlap, declared disjoint, or unknown**.
- Keep offline and streaming results in separate views. Native streaming latency needs its own live-input protocol.
- Record failed, unsupported, and missing runs explicitly. Incomplete systems receive coverage information and no complete overall rank.

For production, average pooled DER across the eight domain x language-group cells with equal weights. Also publish conventional globally pooled DER and every cell's result.

Use paired bootstrap resampling over independent source conversations, with 10,000 resamples and fixed seeds. Publish 95% intervals; adjust pairwise winner claims for multiple comparisons. Require both statistical evidence and a predeclared **one percentage-point DER improvement** for a practically meaningful win.

The pilot's intervals remain exploratory, especially for small language slices.

### Design the leaderboard sketch

Show model/version, DER with uncertainty, JER, count accuracy, speed, and completion coverage in the main table. Add filters for domain, language, speaker count, overlap, and operating mode.

A model detail view will expose error components, counting bias, low-activity-speaker recall, hardware, settings, exposure disclosures, and example failures. Include an accuracy-speed scatterplot and a clear protocol/version label.

Use measured pilot values where available. Label illustrative production rows explicitly.

## 4. Larger pilot and reproducible execution

### Systems

Target these four self-hosted systems:

1. `pyannote/speaker-diarization-community-1`
2. `BUT-FIT/diarizen-wavlm-large-s80-md-v2`
3. `CIIL/Anuvani-Diarization`
4. `nvidia/Nemotron-3-Diarization`

This provides a general baseline, a parent/adapted Indic comparison, and an end-to-end system. Pin checkpoint revisions and dependencies. Verify that each runs on the available Kaggle GPU before scaling.

Community-1 requires accepting its access conditions. Nemotron supports offline and streaming inference with an eight-speaker capacity; use its documented offline configuration for this comparison. Sources: [Community-1 model card](https://huggingface.co/pyannote/speaker-diarization-community-1) and [Nemotron model card](https://huggingface.co/nvidia/Nemotron-3-Diarization).

### Recordings

Select **24 independent source recordings** before inspecting predictions:

- **12 Indic DiarBench:** two per selected Indic language.
- **6 AMI:** single distant-microphone meeting audio.
- **6 VoxConverse:** prioritize recordings containing at least five speakers.

Use one deterministic excerpt of up to five minutes per source. Define counts and activity using that excerpt's reference. Target at least six crowded recordings and six excerpts with substantial overlap; publish any unmet coverage target.

Use native corpus references for the pilot and report corpus results separately. Any equal-corpus aggregate is exploratory because annotation conventions differ. The proposed production collection uses the unified convention described above.

### Execution and evidence

Prepare code locally and run isolated Kaggle environments when dependencies conflict. Use a portable interface:

**manifest -> model inference -> hypothesis RTTM -> scoring -> tables and figures**

The manifest must identify source, split, timestamps, language, reference, scoring regions, and audio checksum. Each run must preserve configuration, checkpoint revision, raw output, normalized RTTM, timing, status, and logs.

Checkpoint after each recording and resume completed work without rerunning it. Collect results locally for analysis.

Measure ordinary inference timing on all recordings. On a fixed six-recording panel, perform one warm-up and three timed repetitions on the same GPU. Report model loading separately; state exactly what timed execution includes. Use RTF rather than claiming streaming responsiveness from offline throughput.

Produce:

- Per-corpus and exploratory aggregate results.
- DER component, counting-error, and accuracy-speed plots.
- Three audio-backed failure analyses: brief speaker, overlap, and multilingual/code-mixed conversation.
- An annotation audit of six short reference excerpts, with diagnostic corrections reported separately.
- An honest account of whether the observed results support each research-inspired hypothesis.

### Time limits and fallback

Allow at most one hour of troubleshooting per model and a 12 GPU-hour pilot budget. If necessary, reduce to three working systems on the same 24 recordings. If data access or quota prevents that, retain a predefined balanced 12-recording subset.

Freeze experimentation at the end of Day 3. Disclose every reduction and preserve the four required deliverables.

## 5. Schedule, validation, and final package

| Day | Hours | Completion checkpoint |
|---|---:|---|
| **1** | 7 | Evidence table, audience decisions, model catalog, access checks, frozen protocol. |
| **2** | 8 | Dataset manifest, scoring checks, model smoke tests, first complete pilot subset. |
| **3** | 9 | Remaining runs, timing panel, failure analysis, figures; experiment freeze. |
| **4** | 8 | Main document, production methodology, leaderboard sketch, final reflections. |
| **5** | 6 | One-page report, video script and recording, PDF inspection, submission checks. |

Validate scoring with small, meaningful fixtures: perfect output, permuted labels, missing brief speaker, merged/split speakers, overlap, silence false alarms, empty hypotheses, and invalid timestamps. Cross-check selected DER/JER results using dscore and pyannote.metrics under matching settings.

Before submission, verify that every published number traces to saved results, every system has an exact identifier or an explicit version limitation, and no proposed experiment is presented as completed.

Deliver:

1. **`Firstname_Lastname_Q1_Main.pdf`** - target 12-16 readable pages plus references/appendix; cover all assignment requirements and end with the four reflection answers.
2. **`Firstname_Lastname_Q1_OnePager.pdf`** - exactly one page covering purpose, setup, three key decisions, principal finding, and limitation.
3. **Leaderboard sketch PDF** - overview and model-detail views, with readable filters and score explanations.
4. **Video link** - target 110 seconds: problem, design, three decisions, measured takeaway, and limitation.

The main document must end with short answers to these four reflection questions:

1. Which design choice are you least sure about, and why?
2. Which benchmark you read influenced you most, and how?
3. What could make your leaderboard misleading, and how did you guard against it?
4. What would you improve with more time?

Keep code, manifests, environment locks, and result files as supporting reproducibility material. The video must be recorded and uploaded through the user's chosen account; verify playback, duration, and reviewer access before submission.
