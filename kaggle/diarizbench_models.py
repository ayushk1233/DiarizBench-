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
    hits = glob.glob("/kaggle/input/**/*.wav", recursive=True)
    if hits:
        return os.path.dirname(hits[0])
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
    sh(["rm", "-rf", f"{SP}/numpy", f"{SP}/numpy-2.1.3.dist-info",
        f"{SP}/numpy-2.5.4.dist-info", f"{SP}/numpy.libs"])
    sh([sys.executable, "-m", "pip", "install", "-q", "--ignore-installed",
        "--prefer-binary", "numpy>=2.3", "numba>=0.60"])
    sh([sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
        "pyannote.audio>=4.0.1", "torch<2.15", "torchvision<0.27",
        "transformers", "soundfile", "huggingface_hub"])
    from huggingface_hub import hf_hub_download
    wheel = hf_hub_download("CIIL/Anuvani-Diarization",
                            "wheels/anuvani_diar-1.0.0-cp310-abi3-manylinux_2_28_x86_64.whl")
    sh([sys.executable, "-m", "pip", "install", "-q", wheel])
    print("deps installed", flush=True)


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
