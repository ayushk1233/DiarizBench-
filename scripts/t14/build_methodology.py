"""Export the PDF authoring source as ordinary GitHub-readable Markdown."""
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
source=(ROOT/'docs/main.md').read_text()
source=re.sub(r'\[\[fig:([^|]+)\|([^\]]+)\]\]',lambda m:f'![{m[2]}](../data/runs/figures/{m[1]})\n\n*{m[2]}*',source)
source=re.sub(r'\[\[kpi:([^\]]+)\]\]',lambda m:'**'+' · '.join(m[1].split('|'))+'**',source)
source=re.sub(r'^\[\[(?:space:[^\]]+|widths:[^\]]+|page|toc)\]\]\s*$', '',source,flags=re.M)
source=re.sub(r'^\^ (.+)$',r'*\1*',source,flags=re.M)
source=re.sub(r'\n{3,}','\n\n',source)
header='# DiarizBench: methodology and measured pilot\n\nThis is the readable Markdown edition of the [main report](../submission/Ayush_Kumar_Q1_Main.pdf).\nThe 60-hour production design and research roadmap are proposals; only the reported pilot was run.\nNo audio is bundled in the public repository. The report describes the original local listening demo;\nthe [public product design](../submission/Ayush_Kumar_Q1_Leaderboard_Design.html) requires separately supplied local audio.\n\n'
(ROOT/'docs/METHODOLOGY.md').write_text(header+source.strip()+'\n')
print('wrote docs/METHODOLOGY.md')
