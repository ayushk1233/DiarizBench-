"""Package major deliverables and reviewer links, excluding internal working notes.

  python scripts/t14/archive_submission.py --video-url https://www.loom.com/share/VIDEO_ID

The local ZIP and listening HTML stay ignored by Git. The public repository uses
its audio-free design; the submission HTML includes attributed listening excerpts.
"""
from pathlib import Path
import argparse
import hashlib
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SUB = ROOT / "submission"
REPO = "https://github.com/ayushk1233/DiarizBench-"
FILES = [
    "README_FIRST.txt",
    "Ayush_Kumar_Q1_Main.pdf",
    "Ayush_Kumar_Q1_OnePager.pdf",
    "Ayush_Kumar_Q1_Leaderboard.pdf",
    "Ayush_Kumar_Q1_Leaderboard.html",
    "VIDEO_LINK.txt",
    "GITHUB_LINK.txt",
    "AUDIO_SOURCES.txt",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--video-url", help="Shareable walkthrough URL; otherwise use VIDEO_LINK.txt")
    args = ap.parse_args()
    link_file = SUB / "VIDEO_LINK.txt"
    video = args.video_url or link_file.read_text().strip().splitlines()[0]
    if not re.fullmatch(r"https://www\.loom\.com/share/[A-Za-z0-9]+", video):
        raise SystemExit("Provide a real Loom share URL with --video-url.")
    link_file.write_text(video + "\n")
    (SUB / "GITHUB_LINK.txt").write_text(REPO + "\n")
    (SUB / "AUDIO_SOURCES.txt").write_text((SUB / "AUDIO_SOURCES.md").read_text())
    guide = f"""VOICE ARENA Q1 - DIARIZBENCH
Ayush Kumar

START HERE

1. Ayush_Kumar_Q1_OnePager.pdf
   One-page overview of purpose, core setup, design choices, measured results,
   limitations and future work. Includes DER collar sensitivity and JER.

2. Ayush_Kumar_Q1_Main.pdf
   Full methodology: audience, model catalog, data/reference design, metrics,
   fairness, evaluation process, measured pilot, uncertainty, limitations,
   references, reproducibility evidence and the four final reflections.

3. Ayush_Kumar_Q1_Leaderboard.pdf
   Four-page product sketch: leaderboard, model detail, governance and audio room.

4. Ayush_Kumar_Q1_Leaderboard.html
   Extract the ZIP, then open this file in Chrome or another modern browser.
   Interactive prototype with saved pilot results, filters, comparisons,
   evaluation-run inspection, protocol/limitations and the research roadmap.
   The audio inspector includes three attributed listening excerpts (47 seconds
   total). No installation or backend is needed. Playback uses the source mixture,
   not separated voices; local-file playback is unscored. See AUDIO_SOURCES.txt.

VIDEO WALKTHROUGH
{video}
Also provided in VIDEO_LINK.txt.

GITHUB - CODE, SAVED RESULTS AND GPU WORKFLOW
{REPO}
Also provided in GITHUB_LINK.txt. The repository README explains local scoring,
dataset sources, Kaggle GPU execution and the product design. The public GitHub
version excludes all audio, including embedded audio in its HTML design.

READING THE RESULTS
Three systems, 24 source recordings, seven languages, 72 completed inference units.
DER, JER, speaker counting, low-activity recall and timing were measured. Offline
and streaming configurations are labelled separately. cpWER/tcpWER, additional
datasets, separation, similarity, clustering and VAD/SAD tracks are future work.

This archive contains the major deliverables and reviewer links. Working notes,
scripts for recording the video, intermediate renders, full corpora, credentials,
and model weights are excluded. Source/evidence files are available on GitHub.
"""
    (SUB / "README_FIRST.txt").write_text(guide)
    (SUB / "README.md").write_text(guide)
    token = re.compile(rb"hf_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{24,}")
    contents = {}
    for name in FILES:
        content = (SUB / name).read_bytes()
        if token.search(content):
            raise RuntimeError(f"Credential-like content; refusing to package {name}")
        if name.endswith(".pdf") and not content.startswith(b"%PDF"):
            raise RuntimeError(f"Invalid PDF: {name}")
        contents[name] = content
    target = SUB / "Ayush_Kumar_Q1_Submission.zip"
    temporary = target.with_suffix(".zip.tmp")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in contents.items():
            z.writestr(name, content)
    with zipfile.ZipFile(temporary) as z:
        assert z.testzip() is None
        assert z.namelist() == FILES
        assert all(z.read(name) == content for name, content in contents.items())
    temporary.replace(target)
    print(f"Submission archive: {len(FILES)} files; {target.stat().st_size / 1048576:.2f} MiB")
    print(f"SHA256: {hashlib.sha256(target.read_bytes()).hexdigest()}")
    print(f"Video: {video}")
    print(f"GitHub: {REPO}")


if __name__ == "__main__":
    main()
