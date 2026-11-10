import sys, sysconfig, subprocess, os, time, json, traceback

# Anuvani (CIIL/Anuvani-Diarization) kernel. Installs the prebuilt wheel, runs
# the Diarizer on a batch of recordings, and writes one RTTM + one timing JSON
# per recording under /kaggle/working/output/ for crash-safe checkpointing.
# The RTTM file_id is rewritten to the manifest recording_id.

HF_TOKEN = __HF_TOKEN__
JOBS = __JOBS__            # list of {"rid": "...", "file_id": "..."}
AUDIO_DIR = "/kaggle/input/diarizbench-pilot-audio"

os.environ["HF_TOKEN"] = HF_TOKEN
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
sh([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub", "soundfile"])

import torch
os.makedirs("/kaggle/working/output", exist_ok=True)
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), flush=True)

summary = {"system": "anuvani", "device": ("cuda" if torch.cuda.is_available() else "cpu"), "jobs": {}}


def rewrite_rttm_fileid(src, dst, fid):
    """Read an RTTM, replace field[1] (file id) with fid, write out."""
    lines = []
    with open(src, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.split()
            if fields[0] != "SPEAKER" or len(fields) < 9:
                continue
            fields[1] = fid
            lines.append(" ".join(fields))
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    return lines


try:
    from huggingface_hub import hf_hub_download
    t0 = time.time()
    wheel = hf_hub_download("CIIL/Anuvani-Diarization",
                            "wheels/anuvani_diar-1.0.0-cp310-abi3-manylinux_2_28_x86_64.whl")
    r = sh([sys.executable, "-m", "pip", "install", "-q", wheel])
    if r.returncode != 0:
        raise RuntimeError("wheel install failed")

    from anuvani_diar import Diarizer
    t0 = time.time()
    diarize = Diarizer()  # downloads model/ on first run, runs GPU self-check
    summary["load_s"] = round(time.time() - t0, 2)
    print("Diarizer loaded in", summary["load_s"], "s", flush=True)

    for job in JOBS:
        rid, fid = job["rid"], job["file_id"]
        wav = os.path.join(AUDIO_DIR, f"{rid}.wav")
        rec = {"rid": rid, "file_id": fid}
        try:
            t0 = time.time()
            result = diarize(wav)
            infer_s = time.time() - t0
            tmp = f"/kaggle/working/output/{rid}.raw.rttm"
            result.save_rttm(tmp)
            lines = rewrite_rttm_fileid(tmp, f"/kaggle/working/output/{rid}.rttm", fid)
            speakers = sorted({ln.split()[7] for ln in lines}) if lines else []
            rec.update({"status": "ok", "infer_s": round(infer_s, 2),
                        "turns": len(lines), "num_speakers": len(speakers)})
            with open(f"/kaggle/working/output/{rid}.json", "w") as f:
                json.dump(rec, f)
            print(f"DONE {rid} infer={infer_s:.1f}s spk={len(speakers)}", flush=True)
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
