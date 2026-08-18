#!/usr/bin/env python3
"""
Build the Toddler Mode sound set.

Each utterance is sourced from the best thing available:

  words   -> a native speaker recording from Wikimedia Commons, when one
             exists (74 of 78 currently do). Real humans beat any small TTS.
  the rest-> Kokoro-82M, driven with explicit IPA for letter sounds.

Output:
  assets/sounds/<key>/NN_<kind>.wav   the clips
  assets/sounds/manifest.json         cycle order + captions + provenance
  assets/credits.json                 attribution for ASSETS.md

Why IPA rather than spellings: passing "sss" or "mmm" through a phonemizer
produces "ess-ess-ess" / "em-em-em" -- the letter name spelled out, not the
sound it makes. Letter sounds are therefore given as IPA in phonics_data.py
and pushed straight into the model's phoneme stream.

Usage:
    python generate_sounds.py                    # build what is missing
    python generate_sounds.py --force            # rebuild everything
    python generate_sounds.py --only a b c       # limit to these keys
    python generate_sounds.py --audition a s     # write audition reels
    python generate_sounds.py --no-commons       # TTS only, skip downloads
    python generate_sounds.py --backend kitten   # use the old ONNX model
"""

import argparse
import json
import os

import numpy as np
import soundfile as sf

import audio_util as au
import commons_audio
from audio_util import SR
from phonics_data import build_utterance_plan
from tts_backends import make_synth

ROOT = os.path.dirname(os.path.abspath(__file__))
SOUND_DIR = os.path.join(ROOT, "assets", "sounds")
MANIFEST = os.path.join(SOUND_DIR, "manifest.json")
CREDITS = os.path.join(ROOT, "assets", "credits.json")

# A plosive needs a carrier vowel to be articulated at all; it gets clipped off.
STOP_CARRIER = "ˈɑː"


def render_tts(synth, utt):
    """Synthesise one utterance and post-process it for its phoneme class."""
    mode = utt.get("mode")
    ipa = utt.get("ipa")

    if ipa is None:
        return au.polish(au.trim_silence(synth.from_text(utt["text"])))

    if mode == "stop":
        raw = synth.from_ipa(ipa + STOP_CARRIER)
        return au.polish(au.clip_plosive(au.trim_silence(raw)))

    if mode == "hold":
        # Continuants are sustainable; tripling the phone gives a held sound a
        # child can hear and imitate.
        return au.polish(au.trim_silence(synth.from_ipa(ipa * 3)))

    # "vowel" and "blend" render as written.
    return au.polish(au.trim_silence(synth.from_ipa(ipa)))


def slot_filename(index, utt):
    kind = utt["kind"]
    if kind == "word":
        safe = "".join(c if c.isalnum() else "-" for c in utt["text"])
        return f"{index:02d}_word_{safe}.wav"
    if kind == "sound":
        return f"{index:02d}_sound.wav"
    return f"{index:02d}_name.wav"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="kokoro", choices=["kokoro", "kitten"])
    ap.add_argument("--voice", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--audition", nargs="*", default=None)
    ap.add_argument("--clean", action="store_true",
                    help="remove the old flat *.wav layout first")
    ap.add_argument("--no-commons", action="store_true",
                    help="synthesise words instead of downloading human recordings")
    args = ap.parse_args()

    full_plan = build_utterance_plan()
    plan = full_plan
    if args.only:
        unknown = [k for k in args.only if k not in plan]
        if unknown:
            raise SystemExit(f"Unknown keys: {unknown}")
        plan = {k: full_plan[k] for k in args.only}

    os.makedirs(SOUND_DIR, exist_ok=True)

    if args.clean:
        stale = [f for f in os.listdir(SOUND_DIR) if f.endswith(".wav")]
        for f in stale:
            os.remove(os.path.join(SOUND_DIR, f))
        print(f"Removed {len(stale)} files from the old flat layout")

    # -- Which clips are missing? --------------------------------------------
    todo = []
    for key, utterances in plan.items():
        for i, utt in enumerate(utterances):
            rel = f"{key}/{slot_filename(i, utt)}"
            path = os.path.join(SOUND_DIR, rel)
            if args.force or not os.path.exists(path):
                todo.append((key, i, utt, rel, path))

    total = sum(len(v) for v in plan.values())
    print(f"{total} utterances across {len(plan)} keys; {len(todo)} to build")

    # -- Resolve human recordings for the words we need ----------------------
    commons = {}
    if not args.no_commons:
        wanted = sorted({u["text"] for _, _, u, _, _ in todo if u["kind"] == "word"})
        if wanted:
            print(f"Looking up {len(wanted)} words on Wikimedia Commons...")
            commons = commons_audio.lookup_words(wanted)
            usable = {w: m for w, m in commons.items()
                      if commons_audio.license_is_acceptable(m["license"])}
            skipped = set(commons) - set(usable)
            if skipped:
                print(f"  skipped {len(skipped)} on license grounds: {sorted(skipped)}")
            commons = usable
            print(f"  {len(commons)}/{len(wanted)} available as human recordings")

    # -- Build ----------------------------------------------------------------
    credits = {}
    if os.path.exists(CREDITS):
        try:
            with open(CREDITS) as fh:
                credits = json.load(fh)
        except Exception:
            credits = {}
    credits.setdefault("audio", {})
    credits.setdefault("images", {})

    synth = None
    sources = {"commons": 0, "tts": 0, "failed": 0}

    for n, (key, i, utt, rel, path) in enumerate(todo, 1):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        audio = None
        used = None

        # Prefer a real human voice for words.
        if utt["kind"] == "word" and utt["text"] in commons:
            meta = commons[utt["text"]]
            try:
                raw, orig_sr = commons_audio.download_audio(meta["url"])
                audio = au.polish(au.trim_silence(raw))
                used = "commons"
                credits["audio"][rel] = {
                    "source": "Wikimedia Commons",
                    "title": meta["title"],
                    "author": meta["author"],
                    "license": meta["license"],
                    "license_url": meta["license_url"],
                    "page": meta["page"],
                    "url": meta["url"],
                }
            except Exception as e:
                print(f"      download failed for {utt['text']!r} ({e}); synthesising")

        # Everything else, and any failed download, goes to TTS.
        if audio is None:
            if synth is None:
                print(f"Loading TTS backend ({args.backend})...")
                synth = make_synth(args.backend, args.voice)
            try:
                audio = render_tts(synth, utt)
                used = "tts"
                credits["audio"][rel] = {
                    "source": synth.attribution["name"],
                    "author": synth.attribution["author"],
                    "license": synth.attribution["license"],
                    "url": synth.attribution["url"],
                    "voice": synth.voice,
                    "generated": True,
                }
            except Exception as e:
                print(f"      ERROR building {rel}: {e}")
                sources["failed"] += 1
                continue

        if len(audio) < 16:
            print(f"      WARNING: {rel} came out empty")
        sf.write(path, audio, SR)
        sources[used] += 1
        tag = "human" if used == "commons" else "tts"
        src = utt["ipa"] if utt["ipa"] is not None else utt["text"]
        print(f"  [{n}/{len(todo)}] {key:10} {utt['kind']:5} {tag:5} {src!r} -> {rel}")

    print(f"\nbuilt: {sources['commons']} human, {sources['tts']} synthesised, "
          f"{sources['failed']} failed")

    # -- Manifest (always rewritten so it matches phonics_data) --------------
    manifest = {"sample_rate": SR, "keys": {}}
    for key, utterances in full_plan.items():
        entries = []
        for i, utt in enumerate(utterances):
            rel = f"{key}/{slot_filename(i, utt)}"
            if os.path.exists(os.path.join(SOUND_DIR, rel)):
                entry = {
                    "file": rel,
                    "kind": utt["kind"],
                    "label": utt["label"],
                    "hint": utt["hint"],
                }
                cred = credits["audio"].get(rel)
                if cred:
                    entry["source"] = "human" if not cred.get("generated") else "tts"
                if utt["kind"] == "word":
                    entry["word"] = utt["text"]
                entries.append(entry)
        if entries:
            manifest["keys"][key] = entries
    with open(MANIFEST, "w") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    n_human = sum(1 for e in credits["audio"].values() if not e.get("generated"))
    print(f"manifest: {len(manifest['keys'])} keys, "
          f"{sum(len(v) for v in manifest['keys'].values())} clips "
          f"({n_human} human-recorded)")

    os.makedirs(os.path.dirname(CREDITS), exist_ok=True)
    with open(CREDITS, "w") as fh:
        json.dump(credits, fh, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"credits -> {CREDITS}")

    # -- Optional audition reels ---------------------------------------------
    if args.audition:
        for key in args.audition:
            entries = manifest["keys"].get(key)
            if not entries:
                print(f"  no audio for audition key {key!r}")
                continue
            parts = []
            for e in entries:
                a, _ = sf.read(os.path.join(SOUND_DIR, e["file"]), dtype="float32")
                parts.append(a)
                parts.append(np.zeros(int(0.35 * SR), dtype=np.float32))
            out = os.path.join(SOUND_DIR, f"audition_{key}.wav")
            sf.write(out, np.concatenate(parts), SR)
            print(f"  audition reel -> {out} ({len(entries)} utterances)")


if __name__ == "__main__":
    main()
