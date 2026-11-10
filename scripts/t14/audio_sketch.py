"""Static companion to the functional HTML listening room; no PDF playback claim."""
import html
from build_frontend import audio_examples


def page_audio(manifest):
    clip = audio_examples(manifest)[1]
    bars = "".join(f'<rect x="{i*600/260:.1f}" y="{40-max(1,v*65)/2:.1f}" '
                   f'width="1.6" height="{max(1,v*65):.1f}" rx=".8" fill="#799cb7"/>'
                   for i,v in enumerate(clip["waveform"]))

    def lanes(title, turns):
        ids = sorted({t["speaker"] for t in turns})
        colors = ["#bcd3e8", "#b7d9d0", "#e5c8a3", "#cfc4e5", "#e1b8c0"]
        rows = ""
        for i, speaker in enumerate(ids):
            segments = "".join(f'<i style="position:absolute;left:{t["start"]/clip["duration"]*100:.2f}%;'
                               f'width:{(t["end"]-t["start"])/clip["duration"]*100:.2f}%;'
                               f'top:1mm;height:4.5mm;background:{colors[i%len(colors)]};border-radius:.5mm"></i>'
                               for t in turns if t["speaker"] == speaker)
            rows += f'<div style="display:flex;gap:3mm;align-items:center;margin:1.2mm 0"><span style="width:27mm;font-size:6.7pt">{html.escape(speaker)}</span><div style="height:6.5mm;position:relative;flex:1;background:#f3f6f9">{segments}</div></div>'
        return f'<h4 style="margin:4mm 0 2mm">{title}</h4>{rows}'

    return f'''<div class="page">
    <div class="top"><div class="brand">Audio inspector<span>hear the evidence</span></div>
    <div class="meta"><span class="tag">REAL PILOT EXCERPT</span><br>Functional playback in companion HTML</div></div>
    <h3 style="margin-top:5mm">TE-02 · Telugu · reference overlap example</h3>
    <p>Original source interval 92–104 s. Three reference speakers overlap at 97.2–97.7 s.
    Inspect the saved turns and listen before interpreting an aggregate score.</p>
    <div class="filters" style="margin-bottom:4mm"><div class="filter">Example <b>TE-02 · Telugu</b> ▾</div>
    <div class="filter">System <b>Anuvani · offline</b> ▾</div><div class="filter">Speed <b>1×</b> ▾</div>
    <div class="filter">＋ Open local audio</div></div>
    <div class="card"><div style="display:flex;justify-content:space-between;font-size:9pt"><b>▷ Original mixture</b><span>0:00 / 0:12</span></div>
    <svg viewBox="0 0 600 80" style="width:100%;height:24mm;margin-top:3mm;background:#f1f6fa">{bars}</svg>
    <div style="display:flex;justify-content:space-between;font-size:6.8pt;color:#687b8b"><span>92 s source</span><span>98 s</span><span>104 s</span></div>
    {lanes('Reference · native corpus labels',clip['reference'])}
    {lanes('Anuvani · saved hypothesis',clip['hypotheses']['anuvani'])}
    <p class="small" style="margin-top:3mm">Colors and speaker IDs are local to each track. Same colors do not establish cross-track identity matching.</p></div>
    <div class="cols2" style="margin-top:4mm"><div class="card flat"><h4>Listening controls</h4><p class="small">Play/pause, seek the waveform, set playback speed, zoom the timeline, and click any reference/model turn. Speaker previews play the original source interval, including other voices during overlap.</p></div>
    <div class="card flat"><h4>What is measured</h4><p class="small">Waveform: actual audio amplitude. Turns: saved reference and hypothesis RTTMs. Full-recording DER stays labelled separately from this short excerpt. No separated stems or computed similarity scores are presented.</p></div></div>
    <div class="note" style="margin-top:4mm"><b>How to try it.</b> Open <b>Ayush_Kumar_Q1_Leaderboard.html</b>, then Audio inspector. Bengali, Telugu and Tamil examples are embedded, so playback requires no network. A reviewer can also choose a local file for unscored playback.</div>
    <p class="small" style="margin-top:4mm">Audio: Sarvam AI, Indic DiarBench, telugu_itw_001 (use the companion HTML for exact source/sample attribution), CC BY 4.0. Excerpted and converted to mono 16 kHz PCM. Dataset: https://huggingface.co/datasets/sarvamai/indic-diarbench</p>
    <div class="foot"><span>Static sketch; real audio and interactions are in the companion HTML.</span><span>4 / 4</span></div>
    </div>'''.replace("telugu_itw_001",html.escape(clip["source_id"]))
