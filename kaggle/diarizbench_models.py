"""Shared model loaders + dependency setup for the Diarizbench Kaggle pilot.

Used by smoke_test.py and run_pilot.py. All three systems:
  - pyannote/speaker-diarization-community-1  (modular baseline)
  - nvidia/Nemotron-3-Diarization             (EEND Sortformer, streaming)
  - CIIL/Anuvani-Diarization                  (EEND, Indic-adapted)
"""
import os
import sys
import sysconfig
import subprocess

SP = sysconfig.get_paths()["platlib"]


def audio_dir():
    """Locate the mounted audio dataset, tolerating name/path differences.

    Kaggle mounts datasets under /kaggle/input/<slug>/, but newer layouts can
    nest them under /kaggle/input/datasets/<slug>/. We just find any directory
    under /kaggle/input/ that contains .wav files.
    """
    import glob
    import json
    override = os.environ.get("DIARIZBENCH_AUDIO_DIR")
    if override:
        return override
    hits = glob.glob("/kaggle/input/**/*.wav", recursive=True)
    if hits:
        manifest_path = os.path.join(os.path.dirname(__file__), "..", "harness", "manifest.json")
        expected = set()
        if os.path.isfile(manifest_path):
            with open(manifest_path) as f:
                expected = {r["id"] + ".wav" for r in json.load(f)["recordings"]}
        folders = {os.path.dirname(p) for p in hits}
        return max(sorted(folders), key=lambda p: len(set(os.listdir(p)) & expected))
    return "/kaggle/input/diarizbench-pilot-audio"


def sh(args):
    r = subprocess.run(args, capture_output=True, text=True)
    print(">>>", " ".join(args), "rc", r.returncode, flush=True)
    if r.returncode != 0:
        print((r.stdout or "")[-800:], flush=True)
        print((r.stderr or "")[-800:], flush=True)
    return r


def get_token():
    """HF token from env var, then Kaggle Secrets add-on."""
    tok = os.environ.get("HF_TOKEN")
    if tok:
        return tok
    try:
        from kaggle_secrets import UserSecretsClient
        tok = UserSecretsClient().get_secret("HF_TOKEN")
    except Exception:
        tok = None
    return tok or ""


def install_deps(hf_token=""):
    """One-time environment fix + all dependencies for the three systems."""
    os.environ["HF_TOKEN"] = hf_token
    # purge every trace of the broken base numpy (2.1.3/2.5.4 mix)
    sh(["bash", "-c", f"rm -rf {SP}/numpy {SP}/numpy-*.dist-info {SP}/numpy.libs 2>/dev/null; true"])
    # numpy 2.5 + numba 0.67+ resolved together (numba 0.67 is the first to support numpy 2.5)
    sh([sys.executable, "-m", "pip", "install", "-q", "--ignore-installed",
        "--prefer-binary", "numpy>=2.5,<2.6", "numba>=0.67"])
    sh([sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
        "pyannote.audio>=4.0.1", "torch<2.15", "torchvision<0.27",
        "transformers", "soundfile", "huggingface_hub"])
    from huggingface_hub import hf_hub_download
    wheel = hf_hub_download("CIIL/Anuvani-Diarization",
                            "wheels/anuvani_diar-1.0.0-cp310-abi3-manylinux_2_28_x86_64.whl")
    sh([sys.executable, "-m", "pip", "install", "-q", wheel])
    # safety net: re-assert numpy 2.5.x in case an intermediate install drifted it down
    sh([sys.executable, "-m", "pip", "install", "-q", "--force-reinstall", "--no-deps",
        "numpy>=2.5,<2.6"])
    print("deps installed", flush=True)


def report_versions():
    """Print the versions of the key installed dependencies (for debugging)."""
    import importlib
    print("=== environment ===", flush=True)
    print("python", sys.version.split()[0], flush=True)
    try:
        import torch
        print("torch", torch.__version__, "| cuda available:", torch.cuda.is_available(), flush=True)
    except Exception as e:
        print("torch NOT IMPORTABLE:", e, flush=True)
    for pkg in ["numpy", "numba", "transformers", "soundfile", "librosa",
                "torchvision", "huggingface_hub", "pyannote.audio", "anuvani_diar"]:
        try:
            m = importlib.import_module(pkg)
            print(f"{pkg:>16} {getattr(m, '__version__', 'unknown')}", flush=True)
        except Exception as e:
            print(f"{pkg:>16} NOT INSTALLED ({type(e).__name__})", flush=True)
    print("=== /environment ===", flush=True)


def _gpu_device():
    import torch
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_community1(hf_token):
    import torch
    from pyannote.audio import Pipeline
    pipe = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1", token=hf_token)
    pipe.to(_gpu_device())

    def run(wav, fid):
        out = pipe(wav)
        turns = list(out.speaker_diarization.itertracks(yield_label=True))
        speakers = sorted({s for _, _, s in turns})
        lines = [f"SPEAKER {fid} 1 {seg.start:.3f} {seg.duration:.3f} <NA> <NA> {spk} <NA> <NA>"
                 for seg, _, spk in turns]
        return lines, len(speakers)
    return run


def load_nemotron(hf_token):
    import torch
    from transformers import AutoModelForAudioFrameClassification, AutoProcessor
    from transformers.audio_utils import load_audio
    model_id = "nvidia/Nemotron-3-Diarization"
    proc = AutoProcessor.from_pretrained(model_id, token=hf_token)
    model = AutoModelForAudioFrameClassification.from_pretrained(model_id, token=hf_token, device_map="auto")
    proc.set_streaming_mode("low_latency")
    sr = proc.feature_extractor.sampling_rate

    def run(wav, fid):
        audio = load_audio(wav, sampling_rate=sr)

        def gen():
            yield proc(audio[: proc.num_samples_first_audio_chunk],
                       sampling_rate=sr, is_streaming=True, is_first_audio_chunk=True)
            mel_idx = proc.num_mel_frames_per_step
            start = proc.audio_chunk_start(mel_idx)
            while (end := start + proc.num_samples_per_audio_chunk) <= audio.shape[0]:
                yield proc(audio[start:end], sampling_rate=sr, is_streaming=True, is_first_audio_chunk=False)
                mel_idx += proc.num_mel_frames_per_step
                start = proc.audio_chunk_start(mel_idx)
            yield proc(audio[start:], sampling_rate=sr, is_streaming=True,
                       is_first_audio_chunk=False, is_last_audio_chunk=True)

        cache, logits = None, []
        with torch.inference_mode():
            for inputs in gen():
                inputs = inputs.to(model.device, dtype=model.dtype)
                out = model(**inputs, speaker_cache=cache)
                logits.append(out.logits)
                cache = out.speaker_cache
        logits = torch.cat(logits, dim=1)
        segments = proc.extract_speaker_dict(logits)[0]
        speakers = sorted({s["Speaker"] for s in segments})
        lines = []
        for s in segments:
            st, en = float(s["Start"]), float(s["End"])
            if en > st:
                lines.append(f"SPEAKER {fid} 1 {st:.3f} {en - st:.3f} <NA> <NA> S{s['Speaker']} <NA> <NA>")
        return lines, len(speakers)
    return run


def load_anuvani(hf_token):
    from anuvani_diar import Diarizer
    diarize = Diarizer()

    def run(wav, fid):
        result = diarize(wav)
        tmp = "/kaggle/working/_tmp_anuvani.rttm"
        result.save_rttm(tmp)
        lines = []
        for raw in open(tmp, encoding="utf-8"):
            line = raw.rstrip("\n")
            f = line.split()
            if f and f[0] == "SPEAKER" and len(f) >= 9:
                f[1] = fid
                lines.append(" ".join(f))
        if os.path.exists(tmp):
            os.remove(tmp)
        speakers = sorted({ln.split()[7] for ln in lines}) if lines else []
        return lines, len(speakers)
    return run


LOADERS = {"community-1": load_community1, "nemotron": load_nemotron, "anuvani": load_anuvani}
