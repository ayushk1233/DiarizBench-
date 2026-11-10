# Reviewed findings: failure cases and annotation audit

Reviewed against saved per-recording scores, RTTMs, the manifest, and the final report on
11 November 2026. Reproduce the timestamp extraction with `scripts/t10/analyze.py`.
The comparisons below describe these samples and tested configurations; no listening audit was
completed. The original designation “audio-backed” meant timestamps tied to source recordings,
not human-verified acoustic judgments.

## 1. Brief speaker: BN-01, Bengali near-field

Reference `SPEAKER_05` contributes 12.87 seconds (4.6% of reference speaker-time) across six
interjections, qualifying for the proposed low-activity diagnostic. All three systems fail its
50% recovery threshold after one-to-one matching. This does not mean they emitted no speech
at those times; speech can be missed or assigned to another speaker.

| System | BN-01 DER % | Predicted/reference speakers | Brief speaker recovered |
|---|---:|---:|---:|
| community-1 | 41.2 | 4/8 | 0/1 |
| nemotron | 28.5 | 6/8 | 0/1 |
| anuvani | 22.8 | 6/8 | 0/1 |

The earlier findings accidentally quoted global mean DER values (20.4/21.6/13.8) as if they
were BN-01 scores. The table above uses the correct recording-level values. Alignment suggests
merging with dominant turns, but listening is required to confirm the audible event and identities.
The diagnostic illustrates why duration-weighted DER needs a speaker-coverage companion.

## 2. Overlap: TE-02, Telugu in-the-wild

The reference marks three simultaneous speakers at about 97.2–97.7 seconds. The hypotheses differ
in local labels and boundaries. A matching number of labels alone does not establish correct
speaker identity or good overlap handling.

| System | Whole-recording DER % | Overlap-only DER % |
|---|---:|---:|
| community-1 | 38.6 | 99.8 |
| nemotron | 42.0 | 81.8 |
| anuvani | 38.4 | 91.7 |

These are full-recording scores, not scores on the half-second illustration. Overlap-only DER is
much higher than whole-recording DER here. Anuvani has the lowest overall mean in the pilot but
not the lowest overlap-only mean; community-1, not Anuvani, has the highest overlap-only mean
(68.2% versus 67.7%; Nemotron is 59.9%). Overlap is a diagnostic, not a proven cross-mode rank.

## 3. Multilingual slice: TA-02 versus TE-02

On Tamil TA-02, DER is 29.6/16.8/5.7% for community-1/Nemotron/Anuvani. On Telugu TE-02 it is
38.6/42.0/38.4%. The corpus describes code-mixing in its in-the-wild material, but this pilot has
no language-boundary annotations or listening-based confirmation of individual code switches.
Therefore these cases support multilingual slice analysis, not a causal claim that code-mixing or
Indic fine-tuning explains the gaps. Speaker count, overlap, model family, exposure, and mode are
confounded. Two recordings per language cannot support reliable language-level rankings.

## 4. Six-reference structural audit

HI-01, TE-02, AMI-02, AMI-04, VC-01, and VC-03 were examined for speaker labels, segments,
reference speaker-time, and overlap. No acoustic re-annotation or diagnostic reference corrections
were made; no score was changed by this audit.

- Observed overlap differs across files. Low labelled overlap can reflect conversation content,
  annotation conventions, or both. It does not establish that VoxConverse omitted audible overlap.
- Word-level versus turn-level segmentation differs. Adjacent same-speaker segments can merge
  into the same activity union; segment count alone does not prove greater scoring boundary error.
- Speech density is speaker-time / region duration, not the percentage of time occupied by speech.
  AMI-02 reaches 118.1% because overlapping speakers contribute separately. Values above 100%
  do not imply invalid references, and the earlier “AMI is 68–88% speech” summary was incorrect.
- Per-corpus reporting and exploratory aggregates remain appropriate. Measuring annotation-policy
  effects requires a blinded listening/re-annotation study under one handbook.

## 5. Completion, capacity, and exposure

- All 72 inference units completed with non-empty RTTMs: three systems × 24 distinct source
  recordings. The manifest lists **seven languages**: six Indic languages plus English.
- Nemotron's eight-speaker capacity is exceeded by **HI-01 (9 in-region speakers)** and
  **VC-01 (13)**. VC-02 has eight in-region speakers and is not over capacity. All remain scored;
  capacity limits are not inference failures and are not grounds for exclusion.
- Nemotron ran streaming; community-1 and Anuvani ran offline. Common-mode ranks are separate.
- Anuvani has Indic DiarBench corpus exposure; its DiariZen parent also lists AMI/VoxConverse.
  community-1 has AMI/VoxConverse corpus exposure. Exact session overlap has not been audited;
  Nemotron's exposure is unknown. Existing saved flags are historical metadata, not proof of no exposure.
- DiariZen was environment-blocked; CAM++ integration was not validated after a poor smoke result.
  Neither is a measured pilot competitor, and neither can be called inferior from this evidence.

## 6. Limits and next evaluation

The pilot has three public corpora, a small sample, native references, one GPU type, no human listening
pass, and no matched offline/streaming rerun. Non-significance is not equivalence; coverage gaps were
not tested for superiority. Published external scores cannot measure or bound a mode penalty here.

With more time, add **cpWER/tcpWER** in a separate speaker-attributed transcription track, plus
WER/CER, recognition-versus-attribution diagnostics, VAD/overlap F1, and latency. These require
human-checked words, timings, fixed ASR/normalization, and a pinned MeetEval protocol; none was run.
Expand to DIHARD III, ICSI, CALLHOME, DISPLACE, AliMeeting, and CHiME-8 after access, reference,
split, and training-exposure checks. See `docs/main.md` §12 and final reflection §14.4.
