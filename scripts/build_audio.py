#!/usr/bin/env python3
"""Build the final 8-second audio bed: trims raw narration clips, places them
on a timeline, synthesizes a light uplifting background music pad, ducks the
music under speech, mixes everything, and writes the result plus a timeline
JSON that the video renderer uses to sync animation beats to the voiceover.
"""
import json
import os

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(REPO, "assets", "narration_raw")
OUT_AUDIO = os.path.join(REPO, "assets", "audio_mix.wav")
TIMELINE_JSON = os.path.join(REPO, "assets", "narration_timeline.json")

SR = 44100
DURATION = 8.0
N = int(SR * DURATION)

TEXTS = [
    "Sunlight energizes your body.",
    "Stronger bones.",
    "A brighter mood.",
    "Immune support.",
    "More energy.",
    "Just ten to fifteen minutes a day.",
]

LEAD_IN = 0.08
GAP = 0.06
FADE = 0.012  # seconds, click-free trim edges
SILENCE_THRESH = 0.02


def load_mono(path):
    data, sr = sf.read(path, dtype="float32", always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    return data, sr


def trim_speech(data, sr):
    thresh = SILENCE_THRESH * np.max(np.abs(data)) if np.max(np.abs(data)) > 0 else SILENCE_THRESH
    nz = np.where(np.abs(data) > thresh)[0]
    if len(nz) == 0:
        return data
    start = max(0, nz[0] - int(0.01 * sr))
    end = min(len(data), nz[-1] + int(0.015 * sr))
    clip = data[start:end].copy()
    fade_n = int(FADE * sr)
    if fade_n > 0 and len(clip) > 2 * fade_n:
        ramp = np.linspace(0, 1, fade_n)
        clip[:fade_n] *= ramp
        clip[-fade_n:] *= ramp[::-1]
    return clip


def to_sr(data, src_sr, dst_sr):
    if src_sr == dst_sr:
        return data
    return resample_poly(data, dst_sr, src_sr).astype(np.float32)


def build_narration_timeline():
    clips = []
    for i in range(len(TEXTS)):
        raw, sr = load_mono(os.path.join(RAW_DIR, f"seg_{i}.wav"))
        trimmed = trim_speech(raw, sr)
        trimmed = to_sr(trimmed, sr, SR)
        clips.append(trimmed)

    narration = np.zeros(N, dtype=np.float32)
    timeline = []
    t = LEAD_IN
    for i, clip in enumerate(clips):
        start_sample = int(t * SR)
        end_sample = min(N, start_sample + len(clip))
        seg_len = end_sample - start_sample
        narration[start_sample:end_sample] += clip[:seg_len] * 0.95
        dur = len(clip) / SR
        timeline.append({"index": i, "text": TEXTS[i], "start": round(t, 3), "duration": round(dur, 3), "end": round(t + dur, 3)})
        t += dur + GAP
    return narration, timeline


def chord_freqs(root_midi, quality="maj7"):
    intervals = {"maj7": [0, 4, 7, 11], "min7": [0, 3, 7, 10], "maj": [0, 4, 7]}[quality]
    return [440.0 * 2 ** ((root_midi + iv - 69) / 12) for iv in intervals]


def synth_pad(freqs, n_samples, sr, gain=1.0):
    t = np.arange(n_samples) / sr
    out = np.zeros(n_samples, dtype=np.float32)
    for f in freqs:
        out += np.sin(2 * np.pi * f * t).astype(np.float32) / len(freqs)
    return out * gain


def synth_arpeggio(freqs, n_samples, sr, note_dur=0.28, gain=0.5):
    out = np.zeros(n_samples, dtype=np.float32)
    note_n = int(note_dur * sr)
    i = 0
    step = 0
    while i < n_samples:
        f = freqs[step % len(freqs)]
        seg_n = min(note_n, n_samples - i)
        t = np.arange(seg_n) / sr
        env = np.ones(seg_n, dtype=np.float32)
        atk = min(int(0.01 * sr), seg_n // 2)
        rel = min(int(0.15 * sr), seg_n // 2)
        if atk > 0:
            env[:atk] *= np.linspace(0, 1, atk)
        if rel > 0:
            env[-rel:] *= np.linspace(1, 0, rel)
        note = np.sin(2 * np.pi * f * t).astype(np.float32) * env
        out[i:i + seg_n] += note * gain
        i += note_n
        step += 1
    return out


def build_music_bed(narration_env):
    # Gentle chord progression: Cmaj7 - Fmaj7 - Am7 - Gmaj, ~2s each over 8s.
    progression = [
        (60, "maj7"),
        (65, "maj7"),
        (57, "min7"),
        (55, "maj"),
    ]
    seg_n = N // len(progression)
    music = np.zeros(N, dtype=np.float32)
    for idx, (root, quality) in enumerate(progression):
        s = idx * seg_n
        e = N if idx == len(progression) - 1 else s + seg_n
        freqs = chord_freqs(root, quality)
        music[s:e] += synth_pad(freqs, e - s, SR, gain=0.10)
        arp_freqs = [f * 2 for f in freqs]
        music[s:e] += synth_arpeggio(arp_freqs, e - s, SR, note_dur=0.28, gain=0.045)

    # Overall fade in/out for the whole bed.
    fade_n = int(0.6 * SR)
    music[:fade_n] *= np.linspace(0, 1, fade_n)
    music[-fade_n:] *= np.linspace(1, 0, fade_n)

    # Duck music under narration.
    duck = 1.0 - 0.55 * narration_env
    music *= duck
    return music


def narration_envelope(narration):
    window = int(0.05 * SR)
    energy = np.abs(narration)
    kernel = np.ones(window) / window
    env = np.convolve(energy, kernel, mode="same")
    env = env / (env.max() + 1e-9)
    env = np.clip(env * 3.0, 0, 1)
    return env


def main():
    narration, timeline = build_narration_timeline()
    env = narration_envelope(narration)
    music = build_music_bed(env)

    # Slight stereo width on the music bed (narration stays centered).
    delay = int(0.006 * SR)
    music_r = np.concatenate([np.zeros(delay, dtype=np.float32), music])[:N]
    mix_l = narration + music
    mix_r = narration + music_r
    mix = np.stack([mix_l, mix_r], axis=1)

    peak = np.max(np.abs(mix))
    if peak > 0.97:
        mix = mix * (0.97 / peak)

    os.makedirs(os.path.dirname(OUT_AUDIO), exist_ok=True)
    sf.write(OUT_AUDIO, mix, SR, subtype="PCM_16")

    with open(TIMELINE_JSON, "w") as f:
        json.dump({"duration": DURATION, "segments": timeline}, f, indent=2)

    print("Wrote", OUT_AUDIO)
    print("Wrote", TIMELINE_JSON)
    for seg in timeline:
        print(f"  seg_{seg['index']}: [{seg['start']:.3f}, {seg['end']:.3f}] \"{seg['text']}\"")


if __name__ == "__main__":
    main()
