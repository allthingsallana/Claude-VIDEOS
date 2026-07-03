#!/usr/bin/env bash
# Regenerates the raw narration clips in assets/narration_raw/ using Festival's
# HTS "slt" voice (CMU ARCTIC, female). Requires: apt-get install festival
# festvox-us-slt-hts. Output feeds into scripts/build_audio.py for trimming,
# timeline placement, and mixing with the background music bed.
set -euo pipefail

OUT_DIR="$(dirname "$0")/../assets/narration_raw"
mkdir -p "$OUT_DIR"

declare -a TEXTS=(
  "Sunlight energizes your body."
  "Stronger bones."
  "A brighter mood."
  "Immune support."
  "More energy."
  "Just ten to fifteen minutes a day."
)

for i in "${!TEXTS[@]}"; do
  txt="${TEXTS[$i]}"
  scm="$(mktemp --suffix=.scm)"
  wav="$OUT_DIR/seg_$i.wav"
  cat > "$scm" <<EOF
(load "/usr/share/festival/voices/us/cmu_us_slt_arctic_hts/festvox/cmu_us_slt_arctic_hts.scm")
(voice_cmu_us_slt_arctic_hts)
(utt.save.wave (SayText "$txt") "$wav")
EOF
  festival "$scm" < /dev/null > /dev/null 2>&1
  rm -f "$scm"
  echo "seg_$i: \"$txt\" -> $wav"
done
