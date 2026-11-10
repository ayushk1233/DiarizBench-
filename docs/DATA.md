# Dataset sources and local audio preparation

No audio, embedded audio, model weights or downloaded corpus archives are published in this
repository. Saved RTTM annotations/hypotheses, manifests and score JSON provide non-audio evidence.
Source datasets and derived annotations retain their original terms; the repository does not grant
new rights to those corpora.

| Source | Pilot selection | Obtain the data |
|---|---|---|
| Indic DiarBench, Sarvam AI | 12: two each in Hindi, Bengali, Marathi, Tamil, Telugu and Kannada | [Official dataset](https://huggingface.co/datasets/sarvamai/indic-diarbench), CC BY 4.0 |
| AMI Meeting Corpus | Six single distant-microphone meetings; native word-timed reference | [Official corpus](https://groups.inf.ed.ac.uk/ami/corpus/), CC BY 4.0; [official annotations](https://groups.inf.ed.ac.uk/ami/download/) |
| VoxConverse | Six development recordings, prioritizing crowded conversations | [Official project](https://github.com/joonson/voxconverse); consult its current access/usage terms |

`harness/manifest.json` is the source of truth for recording IDs, sample IDs, language, scoring
region and the canonical decoded-PCM checksum. The pilot contains 24 independent conversations,
seven manifest languages and about 205 minutes of scored audio. AMI meetings are scored whole;
other inputs use the manifest's deterministic excerpts. Corpora keep their native annotations,
so aggregate means are exploratory. Public corpus exposure is disclosed in the report.

## Fetch or supply audio locally

```bash
python3.11 -m venv .venv-data
source .venv-data/bin/activate
python -m pip install -r requirements-data.txt
python scripts/extract_audio.py
```

This script downloads public-source recordings to **ignored** `data/audio/`, converts to mono
16 kHz PCM16, clips to scoring regions and computes SHA-256 over the decoded PCM bytes, not the
WAV container. It may download full source files/shards before selecting excerpts. Dataset hosting
paths can change; obtain the matching recordings manually when a mirror becomes unavailable.
The extractor updates the local manifest checksums; review those changes before publishing results.

Alternatively supply permitted canonical WAVs yourself. Names must match manifest IDs:
`HI-01.wav`, `HI-02.wav`, …, `AMI-01.wav`, …, `VC-06.wav`.

## Attach to Kaggle

Create your own **private** Kaggle dataset with those WAVs and attach it as notebook input. The
original author's private audio input is not accessible by default and is not a dependency that a
reviewer can clone. Respect the source dataset's sharing terms when creating an input dataset.
The notebook finds the directory with the most expected recording names; you can explicitly set:

```python
import os
os.environ['DIARIZBENCH_AUDIO_DIR'] = '/kaggle/input/YOUR-AUDIO-DATASET'
```

The full pilot validates that all 24 expected WAV files are present before installing/loading models.
Keep the audio outside Git. `.gitignore` excludes audio extensions and local dataset directories;
`scripts/check_publication.py` also checks staged content for embedded audio or credentials.
