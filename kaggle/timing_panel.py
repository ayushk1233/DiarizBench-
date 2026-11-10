"""Diarizbench timing panel — warm-up + 3 timed reps per system on a fixed
6-recording set, all in one GPU session (same instance for every rep).

Reuses the loaders + env fix from diarizbench_models.py so the timing numbers
are measured on the exact same code path as the scored run.

Writes /kaggle/working/output/timing_<system>.json and zips everything to
/kaggle/working/timing_output.zip.

Run after the full pilot:  import timing_panel; timing_panel.main()
"""
import os
import time
import json
import shutil

from diarizbench_models import get_token, install_deps, LOADERS, audio_dir

SYSTEMS = ["community-1", "nemotron", "anuvani"]
N_REPS = 3
# Fixed 6-recording panel: 2 Indic (near-field + in-the-wild), 2 AMI (short + long), 2 VoxConverse.
TIMING_RIDS = ["HI-01", "TE-02", "AMI-01", "AMI-04", "VC-01", "VC-03"]
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
# audio durations (seconds) for RTF on the timing panel — from the manifest scoring region.
DURATIONS = {
    "HI-01": 196.6, "TE-02": 300.0, "AMI-01": 1049.4, "AMI-04": 1505.6,
    "VC-01": 300.0, "VC-03": 300.0,
}
OUT = "/kaggle/working/output"


def main():
    AUDIO_DIR = audio_dir()
    if not os.path.isdir(AUDIO_DIR):
        print("!! audio dataset not mounted. Add 'ayuwat/diarizbench-pilot-audio' as a data input, SAVE, re-run.")
        return
    os.makedirs(OUT, exist_ok=True)
    tok = get_token()
    install_deps(tok)

    all_summary = {"n_reps": N_REPS, "systems": {}}
    for system in SYSTEMS:
        print(f"\n===== {system} =====", flush=True)
        try:
            t0 = time.time()
            run = LOADERS[system](tok)
            load_s = round(time.time() - t0, 2)
            print(f"[{system}] loaded in {load_s}s; warming up on {TIMING_RIDS[0]} ...", flush=True)
            run(os.path.join(AUDIO_DIR, f"{TIMING_RIDS[0]}.wav"), RECORDINGS[TIMING_RIDS[0]])
            print("warm-up done", flush=True)
        except Exception as e:
            print(f"[{system}] LOAD/WARMUP ERROR {type(e).__name__}: {str(e)[:500]}", flush=True)
            import traceback; traceback.print_exc()
            all_summary["systems"][system] = {"load_s": load_s, "error": str(e)[:500]}
            continue

        summary = {"system": system, "load_s": load_s, "n_reps": N_REPS, "recordings": {}}
        for rid in TIMING_RIDS:
            wav = os.path.join(AUDIO_DIR, f"{rid}.wav")
            fid = RECORDINGS[rid]
            reps = []
            for rep in range(N_REPS):
                t0 = time.time()
                run(wav, fid)
                reps.append(round(time.time() - t0, 3))
            mean_s = round(sum(reps) / len(reps), 3)
            rtf = round(mean_s / DURATIONS[rid], 4)
            summary["recordings"][rid] = {"reps_s": reps, "mean_s": mean_s, "rtf": rtf}
            print(f"TIMED {rid} reps={reps} mean={mean_s}s rtf={rtf}", flush=True)
        with open(os.path.join(OUT, f"timing_{system}.json"), "w") as f:
            json.dump(summary, f, indent=1)
        all_summary["systems"][system] = summary

    with open(os.path.join(OUT, "timing_summary.json"), "w") as f:
        json.dump(all_summary, f, indent=1)
    shutil.make_archive("/kaggle/working/timing_output", "zip", OUT)
    print("\nALL DONE. Download /kaggle/working/timing_output.zip", flush=True)


if __name__ == "__main__":
    main()
