"""Smoke test: run each system on 1-2 recordings to validate the whole stack.

Run after install_deps(). Verifies audio is mounted, each model loads, and each
produces a non-empty RTTM. Prints timing + speaker counts.
"""
import os
import time
import json
import traceback

from diarizbench_models import get_token, install_deps, LOADERS

AUDIO_DIR = "/kaggle/input/diarizbench-pilot-audio"
OUT = "/kaggle/working/smoke"
os.makedirs(OUT, exist_ok=True)

# (audio filename id, RTTM file_id) — HI-01 is short (196s); VC-01 is crowded (15 spk)
SMOKE = {"HI-01": "hindi_nf_001", "VC-01": "cjfer"}
SYSTEMS = ["community-1", "nemotron", "anuvani"]


def main():
    if not os.path.isdir(AUDIO_DIR):
        print(f"!! audio dataset not mounted at {AUDIO_DIR}. Add 'ayuwat/diarizbench-pilot-audio' as a data input.")
        return
    print("audio files present:", sorted(os.listdir(AUDIO_DIR))[:5], "...", flush=True)

    tok = get_token()
    print("HF token:", ("set (%s...)" % tok[:6]) if tok else "NOT SET (community-1 will fail)", flush=True)

    install_deps(tok)

    results = {}
    for system in SYSTEMS:
        print(f"\n===== {system} =====", flush=True)
        try:
            t0 = time.time()
            run = LOADERS[system](tok)
            load_s = round(time.time() - t0, 2)
            results[system] = {"load_s": load_s, "recordings": {}}
            print(f"loaded in {load_s}s", flush=True)
        except Exception as e:
            results[system] = {"error": f"{type(e).__name__}: {str(e)[:500]}"}
            print(f"LOAD ERROR: {results[system]['error']}", flush=True)
            traceback.print_exc()
            continue

        for rid, fid in SMOKE.items():
            wav = os.path.join(AUDIO_DIR, f"{rid}.wav")
            if not os.path.exists(wav):
                print(f"  !! {rid}.wav missing", flush=True)
                continue
            print(f"  RUN {rid} ...", flush=True)
            try:
                t0 = time.time()
                lines, nspk = run(wav, fid)
                infer_s = round(time.time() - t0, 2)
                with open(f"{OUT}/{system}_{rid}.rttm", "w") as f:
                    f.write("\n".join(lines) + ("\n" if lines else ""))
                results[system]["recordings"][rid] = {"infer_s": infer_s, "turns": len(lines), "num_speakers": nspk}
                print(f"  DONE {rid}: {len(lines)} turns, {nspk} speakers, {infer_s}s", flush=True)
            except Exception as e:
                results[system]["recordings"][rid] = {"error": f"{type(e).__name__}: {str(e)[:400]}"}
                print(f"  ERROR {rid}: {results[system]['recordings'][rid]['error']}", flush=True)
                traceback.print_exc()

    with open(os.path.join(OUT, "smoke_results.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("\nSMOKE DONE", json.dumps(results), flush=True)


if __name__ == "__main__":
    main()
