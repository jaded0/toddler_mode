#!/usr/bin/env python3
"""
Phonics content for Toddler Mode.

Each key maps to an ordered list of utterances that the app cycles through
on repeated presses: the letter NAME first, then each SOUND the letter
makes, then WORDS that begin with it.

Sounds are given as IPA and fed straight into the TTS phoneme stream, NOT
as English spellings. Spellings like "sss" or "mmm" get read back by the
phonemizer as the letter name repeated ("ess-ess-ess"), which is what made
the original sound set unintelligible.

Consonant sounds are deliberately unvoiced/clipped -- /b/, not "buh". A
schwa tacked onto a stop is the classic phonics mistake: "buh-a-tuh" does
not blend into "bat", but /b/-/a/-/t/ does.

Render modes:
    "vowel"  -- vowel or diphthong, rendered with primary stress
    "hold"   -- continuant (f, l, m, n, r, s, v, z); safe to sustain
    "stop"   -- plosive (b, d, g, k, p, t); synthesized with a carrier
                vowel that is then clipped off just after the burst
    "blend"  -- multi-phone sound (/kw/, /ks/, /dʒ/); rendered whole
"""

# ---------------------------------------------------------------------------
# Letters: name (IPA), the sounds it makes, and words that start with it
# ---------------------------------------------------------------------------
# (ipa, mode, hint)  -- hint is for the manifest / parent-facing labels
LETTERS = {
    "a": {
        "name": "ˈeɪ",
        "sounds": [("ˈæ", "vowel", "a as in cat"), ("ˈeɪ", "vowel", "a as in cake")],
        "words": ["apple", "ant", "alligator"],
    },
    "b": {
        "name": "ˈbiː",
        "sounds": [("b", "stop", "b as in ball")],
        "words": ["ball", "bear", "banana"],
    },
    "c": {
        "name": "ˈsiː",
        "sounds": [("k", "stop", "c as in cat"), ("s", "hold", "c as in city")],
        "words": ["cat", "cup", "car"],
    },
    "d": {
        "name": "ˈdiː",
        "sounds": [("d", "stop", "d as in dog")],
        "words": ["dog", "duck", "door"],
    },
    "e": {
        "name": "ˈiː",
        "sounds": [("ˈɛ", "vowel", "e as in bed"), ("ˈiː", "vowel", "e as in me")],
        "words": ["egg", "elephant", "elbow"],
    },
    "f": {
        "name": "ˈɛf",
        "sounds": [("f", "hold", "f as in fish")],
        "words": ["fish", "frog", "flower"],
    },
    "g": {
        "name": "ˈdʒiː",
        "sounds": [("ɡ", "stop", "g as in goat"), ("dʒ", "blend", "g as in giraffe")],
        "words": ["goat", "girl", "green"],
    },
    "h": {
        "name": "ˈeɪtʃ",
        "sounds": [("h", "hold", "h as in hat")],
        "words": ["hat", "house", "horse"],
    },
    "i": {
        "name": "ˈaɪ",
        "sounds": [("ˈɪ", "vowel", "i as in sit"), ("ˈaɪ", "vowel", "i as in bike")],
        "words": ["igloo", "insect", "ink"],
    },
    "j": {
        "name": "ˈdʒeɪ",
        "sounds": [("dʒ", "blend", "j as in jump")],
        "words": ["jump", "jar", "juice"],
    },
    "k": {
        "name": "ˈkeɪ",
        "sounds": [("k", "stop", "k as in kite")],
        "words": ["kite", "key", "king"],
    },
    "l": {
        "name": "ˈɛl",
        "sounds": [("l", "hold", "l as in lion")],
        "words": ["lion", "leaf", "lamp"],
    },
    "m": {
        "name": "ˈɛm",
        "sounds": [("m", "hold", "m as in moon")],
        "words": ["moon", "mouse", "milk"],
    },
    "n": {
        "name": "ˈɛn",
        "sounds": [("n", "hold", "n as in nest")],
        "words": ["nest", "nose", "night"],
    },
    "o": {
        "name": "ˈoʊ",
        "sounds": [("ˈɑː", "vowel", "o as in hot"), ("ˈoʊ", "vowel", "o as in go")],
        "words": ["octopus", "otter", "ostrich"],
    },
    "p": {
        "name": "ˈpiː",
        "sounds": [("p", "stop", "p as in pig")],
        "words": ["pig", "pen", "pizza"],
    },
    "q": {
        "name": "ˈkjuː",
        "sounds": [("kw", "blend", "q as in queen")],
        "words": ["queen", "quilt", "quiet"],
    },
    "r": {
        "name": "ˈɑːɹ",
        "sounds": [("ɹ", "hold", "r as in rain")],
        "words": ["rain", "rabbit", "robot"],
    },
    "s": {
        "name": "ˈɛs",
        "sounds": [("s", "hold", "s as in sun"), ("z", "hold", "s as in is")],
        "words": ["sun", "snake", "star"],
    },
    "t": {
        "name": "ˈtiː",
        "sounds": [("t", "stop", "t as in tree")],
        "words": ["tree", "train", "tiger"],
    },
    "u": {
        "name": "ˈjuː",
        "sounds": [("ˈʌ", "vowel", "u as in cup"), ("ˈjuː", "vowel", "u as in unicorn")],
        "words": ["umbrella", "up", "under"],
    },
    "v": {
        "name": "ˈviː",
        "sounds": [("v", "hold", "v as in violin")],
        "words": ["violin", "van", "volcano"],
    },
    "w": {
        "name": "ˈdʌbəljuː",
        "sounds": [("w", "hold", "w as in water")],
        "words": ["water", "wagon", "window"],
    },
    "x": {
        # x almost never starts a word with its own sound; the words here
        # contain it instead, which is how it is actually taught.
        "name": "ˈɛks",
        "sounds": [("ks", "blend", "x as in box"), ("z", "hold", "x as in xylophone")],
        "words": ["box", "fox", "six"],
    },
    "y": {
        "name": "ˈwaɪ",
        "sounds": [("j", "hold", "y as in yes"), ("ˈaɪ", "vowel", "y as in my")],
        "words": ["yellow", "yarn", "yo-yo"],
    },
    "z": {
        "name": "ˈziː",
        "sounds": [("z", "hold", "z as in zebra")],
        "words": ["zebra", "zoo", "zipper"],
    },
}

# ---------------------------------------------------------------------------
# Numbers: name only, plus a counting word so it is not a one-item cycle
# ---------------------------------------------------------------------------
NUMBERS = {
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

# ---------------------------------------------------------------------------
# Everything below speaks its name only -- no phonics content applies
# ---------------------------------------------------------------------------
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

FUNCTION_KEYS = {f"f{i}": f"F {i}" for i in range(1, 13)}

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

MOUSE_SOUNDS = {
    "click": "click",
    "rightclick": "right click",
    "middleclick": "middle click",
}


def build_utterance_plan():
    """Return {key: [utterance, ...]} in the order the app should cycle them.

    Each utterance is a dict:
        kind    -- "name" | "sound" | "word"
        ipa     -- IPA to synthesize, or None to use `text`
        text    -- English text to synthesize, or None to use `ipa`
        mode    -- render mode (see module docstring); None for plain text
        label   -- what to show under the big letter (None = show nothing)
        hint    -- parent-facing description, for the manifest
    """
    plan = {}

    for letter, data in LETTERS.items():
        items = [{
            "kind": "name", "ipa": data["name"], "text": None,
            "mode": "vowel", "label": None, "hint": f"the letter {letter.upper()}",
        }]
        for ipa, mode, hint in data["sounds"]:
            items.append({
                "kind": "sound", "ipa": ipa, "text": None,
                "mode": mode, "label": None, "hint": hint,
            })
        for word in data["words"]:
            items.append({
                "kind": "word", "ipa": None, "text": word,
                "mode": None, "label": word, "hint": word,
            })
        plan[letter] = items

    for digit, word in NUMBERS.items():
        plan[digit] = [{
            "kind": "name", "ipa": None, "text": word,
            "mode": None, "label": None, "hint": word,
        }]

    for group in (SYMBOL_WORDS, FUNCTION_KEYS, SPECIAL_KEYS, MOUSE_SOUNDS):
        for key, word in group.items():
            plan[key] = [{
                "kind": "name", "ipa": None, "text": word,
                "mode": None, "label": None, "hint": word,
            }]

    return plan
