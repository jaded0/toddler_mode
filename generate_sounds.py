#!/usr/bin/env python3
"""
Generate TTS audio files for all keyboard keys using KittenTTS.
Letters get phonetic sounds, special keys get their names spoken.
"""

import os
import soundfile as sf
from kittentts import KittenTTS

SOUND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "sounds")

# Mapping of key name -> text to speak
# Letters: phonetic sounds
LETTER_PHONETICS = {
    "a": "ah",
    "b": "buh",
    "c": "kuh",
    "d": "duh",
    "e": "eh",
    "f": "fff",
    "g": "guh",
    "h": "huh",
    "i": "ih",
    "j": "juh",
    "k": "kuh",
    "l": "lll",
    "m": "mmm",
    "n": "nnn",
    "o": "oh",
    "p": "puh",
    "q": "kwuh",
    "r": "rrr",
    "s": "sss",
    "t": "tuh",
    "u": "uh",
    "v": "vvv",
    "w": "wuh",
    "x": "ks",
    "y": "yuh",
    "z": "zzz",
}

# Numbers: spoken as words
NUMBER_WORDS = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}

# Symbols: spoken description
SYMBOL_WORDS = {
    "exclaim": "exclamation mark",
    "at": "at sign",
    "hash": "hash",
    "dollar": "dollar sign",
    "percent": "percent",
    "caret": "caret",
    "ampersand": "ampersand",
    "asterisk": "asterisk",
    "leftparen": "left parenthesis",
    "rightparen": "right parenthesis",
    "minus": "minus",
    "underscore": "underscore",
    "equals": "equals",
    "plus": "plus",
    "leftbracket": "left bracket",
    "rightbracket": "right bracket",
    "leftbrace": "left brace",
    "rightbrace": "right brace",
    "backslash": "backslash",
    "pipe": "pipe",
    "semicolon": "semicolon",
    "colon": "colon",
    "quote": "quote",
    "doublequote": "double quote",
    "comma": "comma",
    "period": "period",
    "slash": "slash",
    "question": "question mark",
    "less": "less than",
    "greater": "greater than",
    "tilde": "tilde",
    "backtick": "backtick",
}

# Function keys
FUNCTION_KEYS = {f"f{i}": f"F {i}" for i in range(1, 13)}

# Special keys: spoken as their name
SPECIAL_KEYS = {
    "space": "space",
    "enter": "enter",
    "return": "return",
    "tab": "tab",
    "backspace": "backspace",
    "escape": "escape",
    "shift": "shift",
    "control": "control",
    "alt": "alt",
    "capslock": "caps lock",
    "delete": "delete",
    "home": "home",
    "end": "end",
    "pageup": "page up",
    "pagedown": "page down",
    "up": "up arrow",
    "down": "down arrow",
    "left": "left arrow",
    "right": "right arrow",
    "insert": "insert",
    "printscreen": "print screen",
    "scrolllock": "scroll lock",
    "pause": "pause",
    "numlock": "num lock",
    "super": "super",
    "menu": "menu",
}

# Mouse sounds
MOUSE_SOUNDS = {
    "click": "click",
    "rightclick": "right click",
    "middleclick": "middle click",
}


def generate_all_sounds():
    os.makedirs(SOUND_DIR, exist_ok=True)

    # Combine all sound mappings
    all_sounds = {}
    all_sounds.update(LETTER_PHONETICS)
    all_sounds.update(NUMBER_WORDS)
    all_sounds.update(SYMBOL_WORDS)
    all_sounds.update(FUNCTION_KEYS)
    all_sounds.update(SPECIAL_KEYS)
    all_sounds.update(MOUSE_SOUNDS)

    # Check which files already exist
    existing = set()
    if os.path.isdir(SOUND_DIR):
        for f in os.listdir(SOUND_DIR):
            if f.endswith(".wav"):
                existing.add(f[:-4])

    to_generate = {k: v for k, v in all_sounds.items() if k not in existing}

    if not to_generate:
        print("All sound files already exist!")
        return

    print(f"Generating {len(to_generate)} sound files ({len(existing)} already exist)...")
    print("Loading KittenTTS model...")

    model = KittenTTS("KittenML/kitten-tts-nano-0.1")

    for i, (key_name, text) in enumerate(to_generate.items()):
        filepath = os.path.join(SOUND_DIR, f"{key_name}.wav")
        print(f"  [{i+1}/{len(to_generate)}] Generating '{key_name}' -> \"{text}\"")
        try:
            audio = model.generate(text)
            sf.write(filepath, audio, 24000)
        except Exception as e:
            print(f"    ERROR generating '{key_name}': {e}")

    print("Done!")


if __name__ == "__main__":
    generate_all_sounds()
