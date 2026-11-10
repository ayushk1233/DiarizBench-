import sys, sysconfig, subprocess, os, time, json, traceback

# Timing-panel kernel: for ONE system, load the model, warm up once, then run
# 3 timed reps on each recording in JOBS (all on this same GPU instance).
# Writes /kaggle/working/output/timing.json with per-rep wall-clock times and
# RTF (rep_time / audio_duration).

SYSTEM = "__SYSTEM__"
HF_TOKEN = __HF_TOKEN__
JOBS = __JOBS__            # list of {"rid": "...", "file_id": "..."}
N_REPS = 3
AUDIO_DIR = "/kaggle/input/diarizbench-pilot-audio"

sp = sysconfig.get_paths()["platlib"]

def sh(args):
    r = subprocess.run(args, capture_output=True, text=True)
    print(">>>", " ".join(args), "rc", r.returncode, flush=True)
    if r.returncode != 0:
        print(r.stdout[-800:], flush=True); print(r.stderr[-800:], flush=True)
    return r

sh(["rm", "-rf", f"{sp}/numpy", f"{sp}/numpy-2.1.3.dist-info",
    f"{sp}/numpy-2.5.4.dist-info", f"{sp}/numpy.libs"])
sh([sys.executable, "-m", "pip", "install", "-q", "--ignore-installed",
    "--prefer-binary", "numpy>=2.3"])

os.makedirs("/kaggle/working/output", exist_ok=True)
summary = {"system": SYSTEM, "n_reps": N_REPS, "recordings": {}}


def load_community1():
    sh([sys.executable, "-m", "pip", "install", "-q", "--prefer-binary",
        "pyannote.audio>=4.0.1", "torch<2.15", "torchvision<0.27"])
    import torch
    from pyannote.audio import Pipeline
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1", token=HF_TOKEN)
    pipeline.to(device)
    return lambda wav: pipeline(wav)


def load_nemotron():
    sh([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers", "soundfile"])
    import torch
    from transformers import AutoModelForAudioFrameClassification, AutoProcessor
    from transformers.audio_utils import load_audio
    model_id = "nvidia/Nemotron-3-Diarization"
    processor = AutoProcessor.from_pretrained(model_id, token=HF_TOKEN)
    model = AutoModelForAudioFrameClassification.from_pretrained(model_id, token=HF_TOKEN, device_map="auto")
    processor.set_streaming_mode("low_latency")
    sr = processor.feature_extractor.sampling_rate

    def _run(wav):
        audio = load_audio(wav, sampling_rate=sr)
        def gen():
            yield processor(audio[: processor.num_samples_first_audio_chunk],
                            sampling_rate=sr, is_streaming=True, is_first_audio_chunk=True)
            mel_idx = processor.num_mel_frames_per_step
            start = processor.audio_chunk_start(mel_idx)
            while (end := start + processor.num_samples_per_audio_chunk) <= audio.shape[0]:
                yield processor(audio[start:end], sampling_rate=sr, is_streaming=True, is_first_audio_chunk=False)
                mel_idx += processor.num_mel_frames_per_step
                start = processor.audio_chunk_start(mel_idx)
            yield processor(audio[start:], sampling_rate=sr, is_streaming=True,
                            is_first_audio_chunk=False, is_last_audio_chunk=True)
        cache, logits = None, []
        with torch.inference_mode():
            for inputs in gen():
                inputs = inputs.to(model.device, dtype=model.dtype)
                out = model(**inputs, speaker_cache=cache)
                logits.append(out.logits)
                cache = out.speaker_cache
        return torch.cat(logits, dim=1)
    return _run


def load_anuvani():
    sh([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub"])
    os.environ["HF_TOKEN"] = HF_TOKEN
    from huggingface_hub import hf_hub_download
    wheel = hf_hub_download("CIIL/Anuvani-Diarization",
                            "wheels/anuvani_diar-1.0.0-cp310-abi3-manylinux_2_28_x86_64.whl")
    sh([sys.executable, "-m", "pip", "install", "-q", wheel])
    from anuvani_diar import Diarizer
    diarize = Diarizer()
    return lambda wav: diarize(wav)


LOADERS = {"community-1": load_community1, "nemotron": load_nemotron, "anuvani": load_anuvani}

try:
    t0 = time.time()
    infer = LOADERS[SYSTEM]()
    summary["load_s"] = round(time.time() - t0, 2)
    print(f"[{SYSTEM}] loaded in {summary['load_s']}s; warming up on {JOBS[0]['rid']}", flush=True)

    # warm-up (excluded from timing)
    infer(os.path.join(AUDIO_DIR, f"{JOBS[0]['rid']}.wav"))
    print("warm-up done", flush=True)

    for job in JOBS:
        rid = job["rid"]
        wav = os.path.join(AUDIO_DIR, f"{rid}.wav")
        reps = []
        for rep in range(N_REPS):
            t0 = time.time()
            infer(wav)
            reps.append(round(time.time() - t0, 3))
        summary["recordings"][rid] = {"reps_s": reps, "mean_s": round(sum(reps) / len(reps), 3)}
        print(f"TIMED {rid} reps={reps} mean={summary['recordings'][rid]['mean_s']}s", flush=True)

    with open("/kaggle/working/output/timing.json", "w") as f:
        json.dump(summary, f, indent=1)
except Exception as e:
    summary["error"] = f"{type(e).__name__}: {str(e)[:800]}"
    print("FATAL", summary["error"], flush=True)
    print("\n".join(traceback.format_exc().splitlines()[-20:]), flush=True)

print("RESULTS_JSON", json.dumps(summary), flush=True)
