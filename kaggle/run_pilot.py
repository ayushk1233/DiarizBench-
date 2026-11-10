"""Diarizbench pilot — run all 3 systems on the 24 recordings in one GPU session.

Run after smoke_test.py passes. Writes per-recording RTTM + timing JSON to
/kaggle/working/output/, zips to /kaggle/working/diarizbench_output.zip.

Resumable: finished (system, recording) pairs are skipped, so a session restart
only re-runs what's missing.
"""
import os
import time
import json
import glob
import shutil
import traceback

from diarizbench_models import get_token, install_deps, LOADERS, audio_dir

SYSTEMS = ["community-1", "nemotron", "anuvani"]
RECORDINGS = {  # audio filename id -> RTTM file_id (manifest recording_id)
    "HI-01": "hindi_nf_001", "HI-02": "hindi_itw_004",
    "BN-01": "bengali_nf_001", "BN-02": "bengali_itw_008",
    "MR-01": "marathi_nf_002", "MR-02": "marathi_itw_008",
    "TA-01": "tamil_nf_001", "TA-02": "tamil_itw_018",
    "TE-01": "telugu_nf_001", "TE-02": "telugu_itw_004",
    "KN-01": "kannada_nf_001", "KN-02": "kannada_itw_012",
    "AMI-01": "ES2004a", "AMI-02": "EN2002a", "AMI-03": "IS1009a",
    "AMI-04": "TS3003a", "AMI-05": "ES2011a", "AMI-06": "IS1008a",
    "VC-01": "cjfer", "VC-02": "fkvvo", "VC-03": "aisvi",
    "VC-04": "eziem", "VC-05": "bdopb", "VC-06": "eapdk",
}
OUT = "/kaggle/working/output"


def main():
    AUDIO_DIR = audio_dir()
    if not os.path.isdir(AUDIO_DIR):
        print(f"!! audio dataset not mounted. Add 'ayuwat/diarizbench-pilot-audio' as a data input, SAVE the notebook, then re-run.")
        return
    os.makedirs(OUT, exist_ok=True)
    tok = get_token()
    install_deps(tok)

    summary = {}
    for system in SYSTEMS:
        sys_out = os.path.join(OUT, system)
        os.makedirs(sys_out, exist_ok=True)
        done = {os.path.basename(f)[:-5] for f in glob.glob(f"{sys_out}/*.rttm")}
        todo = [rid for rid in RECORDINGS if rid not in done]
        print(f"\n===== {system}: {len(done)} done, {len(todo)} to run =====", flush=True)
        if not todo:
            continue
        try:
            t0 = time.time()
            run = LOADERS[system](tok)
            summary[system] = {"load_s": round(time.time() - t0, 2), "jobs": {}}
            print(f"[{system}] loaded in {summary[system]['load_s']}s", flush=True)
        except Exception as e:
            summary[system] = {"error": f"{type(e).__name__}: {str(e)[:500]}"}
            print(f"[{system}] LOAD ERROR {summary[system]['error']}", flush=True)
            traceback.print_exc()
            continue

        for rid in todo:
            fid = RECORDINGS[rid]
            wav = os.path.join(AUDIO_DIR, f"{rid}.wav")
            rec = {"rid": rid, "file_id": fid}
            print(f"RUN {system}/{rid} ...", flush=True)
            try:
                t0 = time.time()
                lines, nspk = run(wav, fid)
                infer_s = round(time.time() - t0, 2)
                with open(f"{sys_out}/{rid}.rttm", "w") as f:
                    f.write("\n".join(lines) + ("\n" if lines else ""))
                rec.update({"status": "ok", "infer_s": infer_s, "turns": len(lines), "num_speakers": nspk})
                with open(f"{sys_out}/{rid}.json", "w") as f:
                    json.dump(rec, f)
                print(f"DONE {system}/{rid} infer={infer_s}s spk={nspk}", flush=True)
            except Exception as e:
                rec.update({"status": "error", "error": f"{type(e).__name__}: {str(e)[:400]}"})
                with open(f"{sys_out}/{rid}.json", "w") as f:
                    json.dump(rec, f)
                print(f"ERROR {system}/{rid} {rec['error']}", flush=True)
                traceback.print_exc()
            summary[system]["jobs"][rid] = rec

    with open(os.path.join(OUT, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    shutil.make_archive("/kaggle/working/diarizbench_output", "zip", OUT)
    print("\nALL DONE. Download /kaggle/working/diarizbench_output.zip", flush=True)


if __name__ == "__main__":
    main()
