"""Package reviewed deliverables and credential-free reproducibility evidence."""
from pathlib import Path
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
SUB = ROOT / "submission"


def main():
    selected = set()
    for name in ["plan.md", "tasks.md", "metrics.md", "dataset.md", "manifest.md", "pins.md",
                 "model-catalog.md", "evidence-table.md", "t10_findings.md", "docs/main.md",
                 "docs/video_script.md", "docs/frontend-template.html", "docs/product-sections.html",
                 "docs/product.js", "docs/product.css", "docs/final_reflections.md"]:
        selected.add(ROOT / name)
    for folder in ["harness", "scripts/t10", "scripts/t11", "scripts/t12", "scripts/t13", "scripts/t14"]:
        selected.update(p for p in (ROOT / folder).rglob("*")
                        if p.is_file() and p.suffix in {".py", ".json", ".md", ".cjs"})
    for p in (ROOT / "third_party/dscore").rglob("*"):
        if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts:
            selected.add(p)
    for name in ["kernel_community1.py", "kernel_nemotron.py", "kernel_anuvani.py", "kernel_timing.py"]:
        selected.add(ROOT / "kaggle/pilot-runs" / name)
    for name in ["score.py", "merge_output.py", "summarize.py"]:
        selected.add(ROOT / "scripts/t09" / name)
    for folder in ["data/hypotheses", "data/runs/results", "data/runs/timing", "data/runs/figures"]:
        selected.update(p for p in (ROOT / folder).rglob("*")
                        if p.is_file() and p.suffix in {".rttm", ".json", ".png"})
    manifest = json.loads((ROOT / "harness/manifest.json").read_text())["recordings"]
    for r in manifest:
        folder = "indic" if r["corpus"] == "indic-diarbench" else r["corpus"]
        name = r["id"] if folder == "indic" else r["recording_id"]
        selected.add(ROOT / f"data/references/{folder}/{name}.rttm")
    selected.update(ROOT / "data/runs" / name for name in ["state.json", "summary.json"])

    checksums = []
    with zipfile.ZipFile(SUB / "reproducibility.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(selected):
            content = p.read_bytes()
            # Execution wrappers and logs are deliberately excluded. Templates contain placeholders.
            if re.search(rb"hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{24,}", content):
                raise RuntimeError(f"Credential-like content found; refusing to package {p.relative_to(ROOT)}")
            name = str(p.relative_to(ROOT))
            z.writestr(name, content)
            checksums.append(hashlib.sha256(content).hexdigest() + "  " + name)
        z.writestr("SHA256SUMS.txt", "\n".join(checksums) + "\n")
    target = SUB / "Ayush_Kumar_Q1_Submission.zip"
    files = [p for p in SUB.iterdir() if p.is_file() and p != target and p.suffix in
             {".pdf", ".html", ".md", ".txt", ".zip"}]
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(files):
            z.write(p, p.name)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
    print(f"Reproducibility: {len(selected)} source/evidence files plus checksums; no audio or weights.")
    print(f"Submission archive: {len(files)} files; {target.stat().st_size / 1048576:.2f} MiB.")
    print("Video remains pending until the author supplies a real link.")


if __name__ == "__main__":
    main()
