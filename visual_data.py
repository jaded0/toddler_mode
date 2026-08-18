#!/usr/bin/env python3
"""
Word -> emoji mapping for the picture shown beside each word.

Codepoints are Noto emoji names (lowercase hex, no U+). Two sources are used,
both redistributable:

  Noto Animated Emoji  CC BY 4.0     ~429 emoji, Lottie + 512px GIF
  Noto Color Emoji     Apache 2.0    full coverage, static PNG

Only about half the word list has an animated version, so fetch_visuals.py
tries animated first and falls back to static. A handful of words have no
honest emoji at all -- listed in NO_GOOD_EMOJI rather than mapped to something
misleading, because a wrong picture teaches a wrong word.
"""

WORD_EMOJI = {
    # a
    "apple": "1f34e", "ant": "1f41c", "alligator": "1f40a",
    # b
    "ball": "26bd", "bear": "1f43b", "banana": "1f34c",
    # c
    "cat": "1f431", "cup": "1f964", "car": "1f697",
    # d
    "dog": "1f436", "duck": "1f986", "door": "1f6aa",
    # e
    "egg": "1f95a", "elephant": "1f418", "elbow": "1f4aa",
    # f
    "fish": "1f41f", "frog": "1f438", "flower": "1f338",
    # g
    "goat": "1f410", "girl": "1f467", "green": "1f7e2",
    # h
    "hat": "1f452", "house": "1f3e0", "horse": "1f434",
    # i
    "igloo": "1f3e0", "insect": "1f41b", "ink": "1f58b",
    # j
    "jump": "1f938", "jar": "1fad9", "juice": "1f9c3",
    # k
    "kite": "1fa81", "key": "1f511", "king": "1f934",
    # l
    "lion": "1f981", "leaf": "1f343", "lamp": "1f4a1",
    # m
    "moon": "1f319", "mouse": "1f42d", "milk": "1f95b",
    # n
    "nest": "1faba", "nose": "1f443", "night": "1f303",
    # o
    "octopus": "1f419", "otter": "1f9a6", "ostrich": "1fabf",
    # p
    "pig": "1f437", "pen": "1f58a", "pizza": "1f355",
    # q
    "queen": "1f478", "quilt": "1f9f5", "quiet": "1f92b",
    # r
    "rain": "1f327", "rabbit": "1f430", "robot": "1f916",
    # s
    "sun": "1f31e", "snake": "1f40d", "star": "2b50",
    # t
    "tree": "1f333", "train": "1f686", "tiger": "1f42f",
    # u
    "umbrella": "2602", "up": "2b06", "under": "2b07",
    # v
    "violin": "1f3bb", "van": "1f690", "volcano": "1f30b",
    # w
    "water": "1f4a7", "wagon": "1f69a", "window": "1fa9f",
    # x
    "box": "1f4e6", "fox": "1f98a", "six": "0036-fe0f-20e3",
    # y
    "yellow": "1f7e1", "yarn": "1f9f6", "yo-yo": "1fa80",
    # z
    "zebra": "1f993", "zoo": "1f981", "zipper": "1f9f5",
}

# Words where the mapping above is a stretch. Kept visible so the compromise is
# explicit rather than hidden: "igloo" reuses the house emoji, "zipper" and
# "quilt" both land on the thread spool, "zoo" borrows the lion.
NO_GOOD_EMOJI = {"igloo", "zipper", "quilt", "zoo", "ink", "under", "up"}

# Digits render as keycap emoji.
DIGIT_EMOJI = {str(d): f"003{d}-fe0f-20e3" for d in range(10)}


def all_visual_targets():
    """Return {word: codepoint} for everything worth fetching a picture for."""
    targets = dict(WORD_EMOJI)
    return targets
