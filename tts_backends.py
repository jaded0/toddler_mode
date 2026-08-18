#!/usr/bin/env python3
"""
TTS backends for the parts of the sound set no human recording covers:
letter names, isolated phonemes, symbols and modifier keys.

Kokoro-82M is the default. It is Apache 2.0, runs on CPU, and at 82M
parameters is roughly 5x the size of KittenTTS nano -- audibly better on the
short, context-free utterances phonics needs. KittenTTS stays available as a
fallback so the generator still runs without the heavier torch stack.

Both backends expose the same two calls:

    synth.from_text(text) -> float32 @ 24kHz
    synth.from_ipa(ipa)   -> float32 @ 24kHz

`from_ipa` is the important one. Passing spellings like "sss" through a
phonemizer yields "ess-ess-ess" -- the letter name, not its sound -- so letter
sounds are specified as IPA and pushed straight into the phoneme stream.
"""

import numpy as np

SR = 24000


class KokoroSynth:
    """Kokoro-82M (Apache 2.0). Accepts phonemes directly via KModel."""

    name = "Kokoro-82M"
    attribution = {
        "name": "Kokoro-82M",
        "author": "hexgrad",
        "license": "Apache-2.0",
        "url": "https://huggingface.co/hexgrad/Kokoro-82M",
    }
    DEFAULT_VOICE = "af_heart"

    def __init__(self, voice=DEFAULT_VOICE):
        import torch
        from huggingface_hub import hf_hub_download
        from kokoro import KModel, KPipeline

        self._torch = torch
        self.voice = voice
        self._model = KModel().eval()
        # lang_code 'a' = American English. model=False -> we only want its G2P.
        self._g2p = KPipeline(lang_code="a", model=False)
        path = hf_hub_download("hexgrad/Kokoro-82M", f"voices/{voice}.pt")
        self._ref = torch.load(path, weights_only=True)

    def _ref_for(self, phonemes):
        """Kokoro indexes its voice tensor by phoneme-sequence length."""
        idx = min(max(len(phonemes) - 1, 0), self._ref.shape[0] - 1)
        return self._ref[idx]

    def from_ipa(self, ipa, speed=1.0):
        with self._torch.no_grad():
            out = self._model(ipa, self._ref_for(ipa), speed=speed)
        audio = out.audio if hasattr(out, "audio") else out
        return np.asarray(audio, dtype=np.float32).flatten()

    def from_text(self, text, speed=1.0):
        phonemes, _ = self._g2p.g2p(text)
        return self.from_ipa(phonemes, speed=speed)


class KittenSynth:
    """KittenTTS nano fallback (15M params, ONNX, no torch needed)."""

    name = "KittenTTS-nano-0.1"
    attribution = {
        "name": "KittenTTS nano 0.1",
        "author": "KittenML",
        "license": "Apache-2.0",
        "url": "https://github.com/KittenML/KittenTTS",
    }
    DEFAULT_VOICE = "expr-voice-5-f"

    def __init__(self, voice=DEFAULT_VOICE):
        from kittentts import KittenTTS
        self.voice = voice
        self._inner = KittenTTS("KittenML/kitten-tts-nano-0.1").model
        if voice not in self._inner.available_voices:
            raise SystemExit(
                f"Unknown voice {voice!r}. Available: {self._inner.available_voices}"
            )

    def _run(self, inputs):
        out = self._inner.session.run(None, inputs)[0]
        return np.asarray(out, dtype=np.float32).flatten()

    def from_text(self, text, speed=1.0):
        return self._run(self._inner._prepare_inputs(text, self.voice, speed))

    def from_ipa(self, ipa, speed=1.0):
        tokens = [0] + self._inner.text_cleaner(ipa) + [0]
        return self._run({
            "input_ids": np.array([tokens], dtype=np.int64),
            "style": self._inner.voices[self.voice],
            "speed": np.array([speed], dtype=np.float32),
        })


BACKENDS = {"kokoro": KokoroSynth, "kitten": KittenSynth}


def make_synth(backend="kokoro", voice=None):
    """Build a backend, falling back to KittenTTS if Kokoro will not load."""
    if backend not in BACKENDS:
        raise SystemExit(f"Unknown backend {backend!r}; pick from {list(BACKENDS)}")
    cls = BACKENDS[backend]
    try:
        return cls(voice or cls.DEFAULT_VOICE)
    except Exception as e:
        if backend == "kokoro":
            print(f"  Kokoro unavailable ({e}); falling back to KittenTTS")
            return KittenSynth(KittenSynth.DEFAULT_VOICE)
        raise
