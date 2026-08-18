#!/usr/bin/env python3
"""
Fetch native-speaker word pronunciations from Wikimedia Commons.

Wiktionary contributors and the Lingua Libre project have recorded well over
100,000 English words, published as `File:En-us-<word>.ogg` on Commons. For the
word half of the phonics cycle these beat any small TTS model outright -- they
are real humans.

Most are CC BY-SA, which is an attribution AND share-alike obligation. Every
download therefore records its author, license and source URL so ASSETS.md can
credit it properly.
"""

import io
import json
import re
import time
import urllib.parse
import urllib.request

import numpy as np
import soundfile as sf

from audio_util import SR, resample, to_mono

API = "https://commons.wikimedia.org/w/api.php"
UA = "toddler-mode/0.1 (https://github.com/jaded0/toddler_mode) python-urllib"

# Tried in order; Commons capitalisation is inconsistent and some words only
# exist in a regional variant.
TITLE_PATTERNS = [
    "En-us-{lower}.ogg",
    "En-us-{cap}.ogg",
    "En-uk-{lower}.ogg",
    "En-au-{lower}.ogg",
    "LL-Q1860 (eng)-Vealhurl-{lower}.wav",
]

_TAGS = re.compile(r"<[^>]+>")


def _strip_html(text):
    return _TAGS.sub("", text or "").strip()


def _api(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def lookup_words(words):
    """Resolve words to Commons recordings.

    Returns {word: {url, license, license_url, author, title}} for those found.
    Queries in batches and tries each title pattern until something hits.
    """
    found = {}
    for pattern in TITLE_PATTERNS:
        pending = [w for w in words if w not in found]
        if not pending:
            break
        for i in range(0, len(pending), 40):
            batch = pending[i:i + 40]
            titles = {}
            for w in batch:
                t = "File:" + pattern.format(lower=w.lower(), cap=w.capitalize())
                titles[t.lower()] = w
            try:
                data = _api({
                    "action": "query", "format": "json", "prop": "imageinfo",
                    "iiprop": "url|extmetadata", "titles": "|".join(titles),
                })
            except Exception as e:
                print(f"    Commons query failed: {e}")
                continue
            for page in data.get("query", {}).get("pages", {}).values():
                if "missing" in page or not page.get("imageinfo"):
                    continue
                word = titles.get(page["title"].lower())
                if word is None or word in found:
                    continue
                info = page["imageinfo"][0]
                meta = info.get("extmetadata", {})
                found[word] = {
                    "url": info["url"].split("?")[0],
                    "title": page["title"],
                    "license": meta.get("LicenseShortName", {}).get("value", "unknown"),
                    "license_url": meta.get("LicenseUrl", {}).get("value", ""),
                    "author": _strip_html(meta.get("Artist", {}).get("value", "")) or "unknown",
                    "page": "https://commons.wikimedia.org/wiki/"
                            + urllib.parse.quote(page["title"].replace(" ", "_")),
                }
    return found


def download_audio(url, attempts=6, pause=0.4):
    """Download and decode a Commons audio file to mono float32 at SR.

    Commons throttles rapid sequential fetches -- a bulk run without backoff
    starts failing partway through the alphabet and silently falls back to
    TTS. Retries with exponential backoff, and paces requests slightly.
    """
    last = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
            audio, src_sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
            time.sleep(pause)
            return resample(to_mono(audio), src_sr), src_sr
        except Exception as e:
            last = e
            if attempt < attempts - 1:
                time.sleep(pause * (2 ** attempt) + 1.0)
    raise last


# Licenses we are willing to redistribute. Anything non-commercial or unclear
# is skipped rather than quietly shipped.
ALLOWED_LICENSE_HINTS = (
    "cc0", "public domain", "cc by", "cc by-sa", "cc-by", "cc-by-sa",
)


def license_is_acceptable(license_name):
    lic = (license_name or "").lower()
    if "nc" in lic.replace("-", " ").split() or "noncommercial" in lic:
        return False
    return any(h in lic for h in ALLOWED_LICENSE_HINTS)
