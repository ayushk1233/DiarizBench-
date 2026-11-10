#!/bin/sh
# Package data/audio/*.wav into a Kaggle dataset and (optionally) upload it.
# Usage: scripts/t09/upload_audio_dataset.sh [--upload]
set -e
cd "$(dirname "$0")/../.."

DSDIR=kaggle/audio-dataset
mkdir -p "$DSDIR"
cp data/audio/*.wav "$DSDIR"/
echo "copied $(ls data/audio/*.wav | wc -l | tr -d ' ') wav files -> $DSDIR"

if [ "$1" = "--upload" ]; then
  kaggle datasets create -p "$DSDIR" --dir-mode zip
else
  echo "dry run: not uploading (pass --upload to upload)"
fi
