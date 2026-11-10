"""Check Git's index for audio, credentials, archives and unintended submissions."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
AUDIO = {'.wav','.flac','.mp3','.m4a','.aac','.ogg','.opus','.aiff','.aif','.webm','.mp4','.mov'}
ARCHIVES = {'.zip','.tar','.gz','.parquet','.safetensors','.pt','.pth','.onnx'}
SUBMISSION = {'Ayush_Kumar_Q1_Main.pdf','Ayush_Kumar_Q1_OnePager.pdf',
              'Ayush_Kumar_Q1_Leaderboard.pdf','Ayush_Kumar_Q1_Leaderboard_Design.html'}
PATTERNS = {
    'credential-like token': re.compile(rb'hf_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9]{24,}'),
    'embedded audio payload': re.compile(rb'data:audio/[^;,\s]+;base64,[A-Za-z0-9+/=]{64,}'),
    'private key': re.compile(rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'),
}


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def main():
    paths=[x.decode() for x in git('ls-files','-z').split(b'\0') if x]
    problems=[]
    for line in git('ls-files','--stage').decode().splitlines():
        if line.startswith('160000 '):problems.append((line.split('\t',1)[-1],'embedded repository/submodule'))
    for name in paths:
        p=Path(name)
        if p.suffix.lower() in AUDIO|ARCHIVES:
            problems.append((name,'audio/video/archive/weight file'))
        if 'submission' in p.parts and p.name not in SUBMISSION:
            problems.append((name,'non-core submission file'))
        if p.name=='.env' or p.name=='kaggle.json':
            problems.append((name,'credential configuration'))
        if '.git' in p.parts:
            problems.append((name,'nested Git metadata'))
        data=git('show',':'+name)
        for reason,pattern in PATTERNS.items():
            if pattern.search(data):problems.append((name,reason))
        if data.startswith(b'%PDF') and re.search(rb'/(?:EmbeddedFile|RichMedia|Sound)\b',data):
            problems.append((name,'embedded PDF attachment/media'))
        if p.suffix=='.ipynb':
            import json
            notebook=json.loads(data)
            if any(c.get('outputs') for c in notebook.get('cells',[])):
                problems.append((name,'notebook output cells must be cleared'))
    if problems:
        for name,reason in problems:print(f'FAIL {name}: {reason}')
        return 1
    print(f'PASS: {len(paths)} indexed files; no audio/embedded audio, tokens, archives or non-core submissions.')
    return 0


if __name__=='__main__':sys.exit(main())
