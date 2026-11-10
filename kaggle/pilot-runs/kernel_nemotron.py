import sys, sysconfig, subprocess, os, time, json, traceback

# Nemotron-3 Diarization kernel. Uses the documented STREAMING (chunked) path
# because the offline single-forward is bounded by max_position_embeddings
# (~50 s) while our recordings run 3-17 minutes. Writes one RTTM + one timing
# JSON per recording under /kaggle/working/output/ for crash-safe checkpointing.

HF_TOKEN = __HF_TOKEN__
JOBS = __JOBS__            # list of {"rid": "...", "file_id": "..."}
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
sh([sys.executable, "-m", "pip", "install", "-q", "-U", "transformers", "soundfile"])

import torch
os.makedirs("/kaggle/working/output", exist_ok=True)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), flush=True)

summary = {"system": "nemotron", "device": str(device), "jobs": {}}


def run_streaming(processor, model, audio, sampling_rate):
    """Chunked streaming inference -> concatenated frame logits (README path)."""
    def inputs_generator():
        yield processor(audio[: processor.num_samples_first_audio_chunk],
                        sampling_rate=sampling_rate, is_streaming=True,
                        is_first_audio_chunk=True)
        mel_frame_idx = processor.num_mel_frames_per_step
        start_idx = processor.audio_chunk_start(mel_frame_idx)
        while (end_idx := start_idx + processor.num_samples_per_audio_chunk) <= audio.shape[0]:
            yield processor(audio[start_idx:end_idx], sampling_rate=sampling_rate,
                            is_streaming=True, is_first_audio_chunk=False)
            mel_frame_idx += processor.num_mel_frames_per_step
            start_idx = processor.audio_chunk_start(mel_frame_idx)
        yield processor(audio[start_idx:], sampling_rate=sampling_rate,
                        is_streaming=True, is_first_audio_chunk=False,
                        is_last_audio_chunk=True)

    speaker_cache, logits = None, []
    with torch.inference_mode():
        for inputs in inputs_generator():
            inputs = inputs.to(model.device, dtype=model.dtype)
            outputs = model(**inputs, speaker_cache=speaker_cache)
            logits.append(outputs.logits)
            speaker_cache = outputs.speaker_cache
    return torch.cat(logits, dim=1)


try:
    from transformers import AutoModelForAudioFrameClassification, AutoProcessor
    from transformers.audio_utils import load_audio

    model_id = "nvidia/Nemotron-3-Diarization"
    t0 = time.time()
    processor = AutoProcessor.from_pretrained(model_id, token=HF_TOKEN)
    model = AutoModelForAudioFrameClassification.from_pretrained(model_id, token=HF_TOKEN, device_map="auto")
    processor.set_streaming_mode("low_latency")
    summary["load_s"] = round(time.time() - t0, 2)
    sampling_rate = processor.feature_extractor.sampling_rate
    summary["sampling_rate"] = sampling_rate
    print("loaded in", summary["load_s"], "s; sr", sampling_rate, flush=True)

    for job in JOBS:
        rid, fid = job["rid"], job["file_id"]
        wav = os.path.join(AUDIO_DIR, f"{rid}.wav")
        rec = {"rid": rid, "file_id": fid}
        try:
            t0 = time.time()
            audio = load_audio(wav, sampling_rate=sampling_rate)
            logits = run_streaming(processor, model, audio, sampling_rate)
            infer_s = time.time() - t0
            segments = processor.extract_speaker_dict(logits)[0]
            speakers = sorted({s["Speaker"] for s in segments})
            lines = []
            for s in segments:
                start = float(s["Start"]); end = float(s["End"])
                if end <= start:
                    continue
                lines.append(f"SPEAKER {fid} 1 {start:.3f} {end - start:.3f} <NA> <NA> "
                             f"S{s['Speaker']} <NA> <NA>")
            with open(f"/kaggle/working/output/{rid}.rttm", "w") as f:
                f.write("\n".join(lines) + "\n")
            rec.update({"status": "ok", "infer_s": round(infer_s, 2),
                        "turns": len(lines), "num_speakers": len(speakers),
                        "logits_frames": int(logits.shape[1])})
            with open(f"/kaggle/working/output/{rid}.json", "w") as f:
                json.dump(rec, f)
            print(f"DONE {rid} infer={infer_s:.1f}s spk={len(speakers)} frames={logits.shape[1]}", flush=True)
        except Exception as e:
            rec.update({"status": "error", "error": f"{type(e).__name__}: {str(e)[:500]}"})
            with open(f"/kaggle/working/output/{rid}.json", "w") as f:
                json.dump(rec, f)
            print(f"ERROR {rid} {rec['error']}", flush=True)
            print("\n".join(traceback.format_exc().splitlines()[-12:]), flush=True)
        summary["jobs"][rid] = rec
except Exception as e:
    summary["error"] = f"{type(e).__name__}: {str(e)[:800]}"
    print("FATAL", summary["error"], flush=True)
    print("\n".join(traceback.format_exc().splitlines()[-20:]), flush=True)

print("RESULTS_JSON", json.dumps(summary), flush=True)
