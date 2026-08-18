# Tuning the sound set

Everything about the current audio has been verified by **measurement**, not by
listening. Signal energy, clip length and edge truncation are all checked
automatically; whether a given clip actually *sounds* like the letter is not.
That judgement is still outstanding.

This document is the shortest path from "that one sounds wrong" to a fixed clip.

## Audition first

```bash
for k in a b s t x; do aplay assets/sounds/audition_$k.wav; done
```

Audition reels concatenate a key's whole cycle with gaps between utterances, in
the order the app plays them. They are gitignored — regenerate any key with:

```bash
python generate_sounds.py --audition a b s t x
```

Listening to one reel per phoneme class is enough to cover the range: a vowel
(`a`), a plosive (`b`, `t`), a continuant (`s`), and a blend (`x`).

## The knobs

All in `audio_util.py`. After changing any of them, regenerate the affected
keys — the parameters apply at build time, not at playback.

| Constant | Default | What it does | Symptom that means "change me" |
| --- | --- | --- | --- |
| `STOP_KEEP_SEC` | `0.20` | How much audio is kept for a plosive before the carrier vowel is cut away | Too low: `b`/`d`/`g`/`k`/`p`/`t` sound clipped to a click. Too high: the schwa leaks back in and you hear "buh" instead of /b/ |
| `STOP_FADE_SEC` | `0.070` | Fade applied to the plosive tail | Too low: audible click at the end. Too high: the sound dissolves before it registers |
| `SILENCE_THRESH` | `0.005` | Fraction of peak that counts as signal when trimming | Too high: quiet `/s/` and `/f/` onsets get eaten — words like *six*, *fish*, *sun* start mid-word |
| `EDGE_PAD_SEC` | `0.06` | Silence kept either side of the signal | Too low: clips feel abrupt and run into each other |
| `FADE_SEC` | `0.012` | Edge fade on every clip | Too low: clicks at clip boundaries |
| `TARGET_RMS` | `0.12` | Loudness all clips are normalised to | Some keys jarringly louder than others |

The plosive trade-off is the one most likely to need your ear. There is no
setting that is simultaneously crisp and fully articulated — a stop consonant
is inherently brief, and the model can only produce one by articulating it
against a vowel that then gets cut. `0.20` is a middle guess.

## Regenerating

Selective rebuilds — only what you name gets rebuilt:

```bash
python generate_sounds.py --force --only b c d g k p t   # the plosives
python generate_sounds.py --force --only a e i o u       # the vowels
python generate_sounds.py --force                        # everything
```

`--force` is required to overwrite existing clips; without it only missing
files are built.

Words are downloaded from Wikimedia Commons rather than synthesised, so the
knobs above barely affect them. To synthesise words instead of downloading:

```bash
python generate_sounds.py --force --no-commons
```

To fall back to the old, smaller ONNX model (no torch required):

```bash
python generate_sounds.py --force --backend kitten
```

### If a bulk run comes back mostly synthesised

Commons throttles rapid sequential fetches. Downloads retry with backoff, but a
large `--force` run can still lose some. Check what actually landed:

```bash
python -c "
import json; c=json.load(open('assets/credits.json'))
tts=[k.split('_word_')[1][:-4] for k,v in c['audio'].items()
     if v.get('generated') and '_word_' in k]
print(f'{len(tts)} words fell back to TTS:', sorted(tts))"
```

Expect exactly `['igloo', 'otter']` — those two have no Commons recording. More
than that means throttling. Delete the affected clips and re-run; each pass
picks up more.

## Verifying a change without ears

`audio_util.edge_energy()` returns how much signal sits at each edge of a clip,
as a fraction of peak. High values mean the clip starts or ends mid-sound.

```bash
python -c "
import soundfile as sf, json, os, audio_util as au
man=json.load(open('assets/sounds/manifest.json'))
rows=[]
for k,es in man['keys'].items():
    for e in es:
        a,_=sf.read(os.path.join('assets/sounds',e['file']),dtype='float64')
        h,t=au.edge_energy(a); rows.append((max(h,t),e['file'],len(a)/24000))
for s,f,d in sorted(rows,reverse=True)[:10]:
    print(f'{f:32} {d:5.2f}s  worst edge {s*100:5.1f}%')"
```

Healthy clips sit near 0%. Anything above ~10% is being cut. For reference, the
original broken set measured 41% on `t` and 23% on `g`.

### Current outliers — listen to these first

As of the last build, three clips exceed that 10% line:

| Clip | Worst edge | Likely cause |
| --- | --- | --- |
| `k/01_sound.wav` | 15.0% | Tail. The `/k/` carrier vowel is cut by `STOP_KEEP_SEC`; expected by design, but `k` and `c` are the two most likely to sound abrupt |
| `c/01_sound.wav` | 14.0% | Same — `c` uses the same `/k/` phoneme |
| `z/03_word_zoo.wav` | 14.7% | A human recording ending on a sustained vowel. Probably natural decay rather than a cut, but worth confirming by ear |

The metric cannot tell "deliberately clipped plosive" apart from "accidentally
truncated", which is precisely why this needs a listen.

## Changing the content

- **Words, sounds, letter names** — `phonics_data.py`. Sounds are IPA and go
  straight into the model's phoneme stream. Do **not** write them as English
  spellings: `"sss"` phonemizes to "ess-ess-ESS", which is the bug that made the
  original set unintelligible.
- **Word pictures** — `visual_data.py` maps each word to an emoji codepoint,
  then `python fetch_visuals.py --force`.
- **Attribution** — rerun `python build_assets_doc.py` after any re-fetch.
  `ASSETS.md` is generated; editing it by hand gets overwritten.

## Known compromises

- **`igloo` and `otter`** have no Commons recording and stay synthesised.
- **`house` is British, `zipper` is Australian.** No US recording exists for
  either. Everything else is en-us.
- **Seven emoji are approximations**, flagged `"approximate": true` in
  `assets/images/manifest.json`: `igloo` reuses the house emoji, `zipper` and
  `quilt` share the thread spool, `zoo` borrows the lion, plus `ink`, `up`,
  `under`. A wrong picture teaches a wrong word, so these are worth replacing
  with a proper pictogram set ([Mulberry Symbols](https://mulberrysymbols.org/),
  CC BY-SA) if it starts to matter.
- **`x` uses words that contain it** (`box`, `fox`, `six`) rather than words
  starting with it, which is how it is actually taught.
