"""Redraw report figures from frozen evidence, without new inference or rescoring."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/runs/figures"
RES = ROOT / "data/runs/results"
SYSTEMS = ["community-1", "nemotron", "anuvani"]
LABEL = {"community-1": "community-1 · offline", "nemotron": "Nemotron-3 · streaming",
         "anuvani": "Anuvani · offline"}
COLORS = {"community-1": "#547696", "nemotron": "#bc8753", "anuvani": "#25847c"}
INK = "#193448"
MUTED = "#687b8b"
BG = "#f5f8fb"


def style():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.labelcolor": MUTED, "text.color": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.spines.left": False, "axes.spines.bottom": False,
                         "axes.edgecolor": "#dce5ec", "figure.facecolor": "white",
                         "savefig.facecolor": "white", "axes.facecolor": "white"})


def canvas(title, subtitle, ncols=1, width=10.5, height=4.8):
    fig, axes = plt.subplots(1, ncols, figsize=(width, height), squeeze=False)
    fig.subplots_adjust(top=.75, bottom=.20, left=.25 if ncols == 1 else .24, right=.96, wspace=.28)
    fig.text(.035, .94, title, fontsize=17, fontweight="bold", va="top")
    fig.text(.035, .855, subtitle, color=MUTED, fontsize=9.4, va="top")
    fig.text(.035, .045, "DIARIZBENCH / MEASURED PILOT", color=MUTED, fontsize=7.5, weight="bold")
    return fig, axes[0]


def save(fig, name):
    fig.savefig(OUT / name, dpi=240)
    plt.close(fig)


def grid(ax, axis="x"):
    ax.set_axisbelow(True)
    ax.grid(axis=axis, color="#e9eff4", lw=.8)
    ax.tick_params(length=0, pad=8)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    style()
    stats = json.loads((RES / "statistics.json").read_text())
    unc = json.loads((RES / "uncertainty.json").read_text())
    records = {s: json.loads((RES / f"{s}.json").read_text())["per_recording"] for s in SYSTEMS}
    panel = json.loads((ROOT / "data/runs/timing/panel_summary.json").read_text())["systems"]
    durations = {r["id"]: r["scoring_region"][1] - r["scoring_region"][0]
                 for r in json.loads((ROOT / "harness/manifest.json").read_text())["recordings"]}
    der = {s: np.mean([r["der"] for r in records[s]]) * 100 for s in SYSTEMS}

    # Per-corpus small multiples: one common scale, no common-mode ranking.
    fig, axes = canvas("Performance changes with the corpus", "Recording-mean DER (%) · native references · lower is better", 3, height=4.5)
    for ax, corpus, title in zip(axes, ["indic-diarbench", "ami", "voxconverse"], ["Indic DiarBench · n=12", "AMI-SDM · n=6", "VoxConverse · n=6"]):
        for i, s in enumerate(SYSTEMS):
            v = stats["pooling"][s]["per_corpus"][corpus]
            ax.hlines(i, 0, v, color=COLORS[s], lw=3, alpha=.22)
            ax.scatter(v, i, s=90, color=COLORS[s], zorder=3)
            ax.text(v+.8, i, f"{v:.1f}", va="center", fontsize=10, weight="bold")
        ax.set_xlim(0, 36); ax.set_ylim(2.5, -.6); ax.set_xticks([0, 10, 20, 30])
        ax.set_yticks(range(3), [LABEL[s] for s in SYSTEMS] if ax == axes[0] else [])
        ax.set_title(title, loc="left", fontsize=10.2, weight="bold", pad=15); grid(ax)
    save(fig, "per_corpus_der.png")

    # Consistent sequential heatmap rather than a red/green win/loss encoding.
    langs = ["Hindi", "Bengali", "Marathi", "Tamil", "Telugu", "Kannada"]
    matrix = np.array([[stats["pooling"][s]["per_language"][l] for s in SYSTEMS] for l in langs])
    fig, axes = canvas("Indic language slices reveal different failure patterns", "Two recordings per language · descriptive only, not language-level rankings", height=5.5)
    ax = axes[0]; cmap = LinearSegmentedColormap.from_list("ocean", ["#eef6f6", "#a5ccc9", "#487e96", "#24475e"])
    ax.imshow(matrix, cmap=cmap, vmin=0, vmax=55, aspect="auto")
    ax.set_xticks(range(3), [LABEL[s].replace(" · ", "\n") for s in SYSTEMS]); ax.set_yticks(range(6), langs)
    ax.tick_params(length=0, pad=9)
    for y in range(6):
        for x in range(3):
            ax.text(x, y, f"{matrix[y,x]:.1f}%", ha="center", va="center", weight="bold",
                    color="white" if matrix[y,x] > 30 else INK, fontsize=11)
    ax.set_xticks(np.arange(-.5, 3, 1), minor=True); ax.set_yticks(np.arange(-.5, 6, 1), minor=True)
    ax.grid(which="minor", color="white", lw=4); ax.tick_params(which="minor", length=0)
    save(fig, "indic_language.png")

    # Stacked horizontal bars with numerical labels inside every component.
    fig, axes = canvas("Missed speech dominates two tested configurations", "DER components, percentage points · recording mean across 24 sources", height=4.8)
    ax = axes[0]; parts = [("missed", "Missed speech", "#6387a5"), ("false_alarm", "False alarm", "#d1a46d"), ("confusion", "Speaker confusion", "#76aaa5")]
    left = np.zeros(3)
    for key, label, color in parts:
        values = np.array([np.mean([r["components"][key] for r in records[s]])*100 for s in SYSTEMS])
        ax.barh(range(3), values, left=left, height=.46, color=color, label=label)
        for i,v in enumerate(values): ax.text(left[i]+v/2, i, f"{v:.1f}", ha="center", va="center", fontsize=9, color=INK)
        left += values
    for i,v in enumerate(left): ax.text(v+.55, i, f"{v:.1f}%", va="center", weight="bold")
    ax.set_yticks(range(3), [LABEL[s] for s in SYSTEMS]); ax.set_ylim(2.6,-.9); ax.set_xlim(0,26)
    ax.legend(ncol=3, frameon=False, fontsize=8.5, loc="lower left", bbox_to_anchor=(-.01,1.00));grid(ax)
    save(fig,"der_components.png")

    fig, axes = canvas("Every tested system under-counts on average", "Signed count error: predicted minus reference · zero is unbiased", height=4.6)
    ax=axes[0]
    for i,s in enumerate(SYSTEMS):
        errors=np.array([r["hyp_speaker_count"]-r["ref_speaker_count"] for r in records[s]])
        bias=errors.mean(); mae=np.abs(errors).mean()
        ax.hlines(i,bias,0,color=COLORS[s],lw=5,alpha=.28);ax.scatter(bias,i,s=120,color=COLORS[s],zorder=3)
        ax.text(bias-.06,i,f"{bias:+.2f}",ha="right",va="center",weight="bold")
        ax.text(.10,i,f"MAE {mae:.2f}",va="center",color=MUTED,fontsize=10)
    ax.axvline(0,color="#95a9b8",lw=1);ax.set_yticks(range(3),[LABEL[s] for s in SYSTEMS]);ax.set_ylim(2.6,-.6);ax.set_xlim(-1.65,.65);grid(ax)
    ax.set_xlabel("Average speaker-count error");save(fig,"count_bias.png")

    fig, axes=canvas("Accuracy and measured throughput answer different questions", "Vertical bars: 95% DER intervals · timed callable scopes differ · not live latency",height=5.0)
    fig.subplots_adjust(left=.10,right=.96,bottom=.21,top=.74)
    ax=axes[0]
    for s in SYSTEMS:
        rtf=sum(r["mean_s"] for r in panel[s]["recordings"].values())/sum(durations[r] for r in panel[s]["recordings"])
        lo,hi=stats["intervals"][s]["der_global_95ci"]
        ax.errorbar(rtf,der[s],yerr=[[der[s]-lo],[hi-der[s]]],fmt="D" if s=="nemotron" else "o",ms=10,color=COLORS[s],capsize=5,lw=2,zorder=3)
        ax.annotate(LABEL[s],(rtf,der[s]),xytext=(-8,11) if s=="nemotron" else (10,-17),textcoords="offset points",ha="right" if s=="nemotron" else "left",fontsize=9,weight="bold")
    ax.set_xlim(.046,.092);ax.set_ylim(6,31);ax.set_xlabel("Real-time factor ↓  (panel processing time / audio time)");ax.set_ylabel("Recording-mean DER (%) ↓");grid(ax,"both")
    save(fig,"accuracy_speed.png")

    fig, axes=canvas("Speaker coverage remains uncertain even when DER improves", "95% intervals · Wilson for count accuracy; recording-cluster bootstrap for low-activity recall",2,height=4.8)
    for ax,key,title in zip(axes,["count_accuracy","low_activity_recall"],["Exact speaker-count accuracy ↑","Low-activity-speaker recall ↑"]):
        for i,s in enumerate(SYSTEMS):
            d=unc[key][s];v=d["pct"];lo,hi=d["wilson95" if key=="count_accuracy" else "clustered_bootstrap95"]
            ax.hlines(i,lo,hi,color=COLORS[s],lw=3,alpha=.55);ax.scatter(v,i,s=100,color=COLORS[s],zorder=3)
            ax.text(v,i-.19,f"{v:.0f}%",ha="center",weight="bold",fontsize=9)
        ax.set_xlim(0,100);ax.set_ylim(2.6,-.7);ax.set_xticks([0,25,50,75,100]);ax.set_yticks(range(3),[LABEL[s] for s in SYSTEMS] if ax==axes[0] else []);ax.set_title(title,fontsize=10,loc="left",pad=15,weight="bold");grid(ax)
    save(fig,"speaker_coverage.png")

    fig, axes=canvas("Paired differences are more informative than sorted means", "DER difference, percentage points · Bonferroni-adjusted bootstrap intervals",height=4.8)
    ax=axes[0]; fig.subplots_adjust(left=.34)
    pairs=list(stats["pairwise"].items())
    for i,(key,p) in enumerate(pairs):
        lo,hi=p["ci_bonferroni"];v=p["mean_diff_pp"];color="#25847c" if key=="community-1__vs__anuvani" else "#8a9aa7"
        ax.hlines(i,lo,hi,color=color,lw=3);ax.scatter(v,i,s=90,color=color,zorder=3)
        ax.text(hi+.4,i,f"{v:+.1f} pp",va="center",fontsize=9,weight="bold")
    ax.axvspan(-1,1,color=BG);ax.axvline(0,color="#748b9d",lw=1,ls="--");ax.set_ylim(2.5,-.6);ax.set_xlim(-7,16)
    ax.set_yticks(range(3),["community-1 − Nemotron\nmode-confounded","community-1 − Anuvani\noffline comparison","Nemotron − Anuvani\nmode-confounded"])
    ax.set_xlabel("Negative: first has lower DER     |     Positive: second has lower DER");grid(ax)
    save(fig,"paired_differences.png")
    print("Redrew five existing figures; added speaker_coverage.png and paired_differences.png.")


if __name__=="__main__": main()
