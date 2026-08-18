#!/usr/bin/env python3
"""
Toddler Mode - A fullscreen interactive toy for toddlers.

Covers all monitors, captures all input, shows big colorful letters
when keys are pressed, plays phonetic sounds, and draws a bubble trail
behind a big custom cursor. Exit by holding Escape for 5 seconds.
"""

import os
import json
import collections
import sys
import math
import random
import time
import signal
import subprocess

import pygame
from pygame import gfxdraw

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ESCAPE_HOLD_SECONDS = 5
MAX_BUBBLES = 120
BUBBLE_SPAWN_INTERVAL = 0.03  # seconds between bubble spawns while moving
MAX_KEY_DISPLAYS = 10
KEY_DISPLAY_DURATION = 2.0  # seconds
KEY_FONT_SIZE = 300
KEY_WORD_FONT_SIZE = 110  # the word shown beneath the letter
WORD_GAP = 10  # pixels between the big letter and the word/picture row
IMAGE_GAP = 18  # pixels between the picture and the word
MAX_CACHED_IMAGES = 24  # sprite sheets held in memory at once
STAMP_DURATION = 3.0  # seconds
MAX_STAMPS = 20
CURSOR_RADIUS = 30
AUDIO_CHANNELS = 16
EXIT_BAR_HEIGHT = 3  # pixels - very subtle

# Bright, toddler-friendly colors
BRIGHT_COLORS = [
    (255, 87, 87),    # red
    (255, 150, 50),   # orange
    (255, 220, 50),   # yellow
    (80, 220, 80),    # green
    (50, 180, 255),   # blue
    (150, 100, 255),  # purple
    (255, 100, 200),  # pink
    (0, 220, 220),    # cyan
    (255, 170, 130),  # peach
    (130, 255, 170),  # mint
]

# ---------------------------------------------------------------------------
# Key name mapping: pygame key constant -> sound file name & display text
# ---------------------------------------------------------------------------
def build_key_map():
    """Build mapping from pygame key constants to (sound_name, display_text)."""
    km = {}

    # Letters
    for i in range(26):
        letter = chr(ord('a') + i)
        key = getattr(pygame, f'K_{letter}')
        km[key] = (letter, letter.upper())

    # Numbers
    for i in range(10):
        key = getattr(pygame, f'K_{i}')
        km[key] = (str(i), str(i))

    # Symbol keys (unshifted versions via their pygame constant)
    symbol_map = {
        pygame.K_BACKQUOTE: ("backtick", "`"),
        pygame.K_MINUS: ("minus", "-"),
        pygame.K_EQUALS: ("equals", "="),
        pygame.K_LEFTBRACKET: ("leftbracket", "["),
        pygame.K_RIGHTBRACKET: ("rightbracket", "]"),
        pygame.K_BACKSLASH: ("backslash", "\\"),
        pygame.K_SEMICOLON: ("semicolon", ";"),
        pygame.K_QUOTE: ("quote", "'"),
        pygame.K_COMMA: ("comma", ","),
        pygame.K_PERIOD: ("period", "."),
        pygame.K_SLASH: ("slash", "/"),
    }
    km.update(symbol_map)

    # Function keys
    for i in range(1, 13):
        key = getattr(pygame, f'K_F{i}')
        km[key] = (f"f{i}", f"F{i}")

    # Special keys
    special = {
        pygame.K_SPACE: ("space", "SPACE"),
        pygame.K_RETURN: ("enter", "ENTER"),
        pygame.K_TAB: ("tab", "TAB"),
        pygame.K_BACKSPACE: ("backspace", "BACK"),
        pygame.K_ESCAPE: ("escape", "ESC"),
        pygame.K_LSHIFT: ("shift", "SHIFT"),
        pygame.K_RSHIFT: ("shift", "SHIFT"),
        pygame.K_LCTRL: ("control", "CTRL"),
        pygame.K_RCTRL: ("control", "CTRL"),
        pygame.K_LALT: ("alt", "ALT"),
        pygame.K_RALT: ("alt", "ALT"),
        pygame.K_CAPSLOCK: ("capslock", "CAPS"),
        pygame.K_DELETE: ("delete", "DEL"),
        pygame.K_HOME: ("home", "HOME"),
        pygame.K_END: ("end", "END"),
        pygame.K_PAGEUP: ("pageup", "PGUP"),
        pygame.K_PAGEDOWN: ("pagedown", "PGDN"),
        pygame.K_UP: ("up", "UP"),
        pygame.K_DOWN: ("down", "DOWN"),
        pygame.K_LEFT: ("left", "LEFT"),
        pygame.K_RIGHT: ("right", "RIGHT"),
        pygame.K_INSERT: ("insert", "INS"),
        pygame.K_PRINT: ("printscreen", "PRNT"),
        pygame.K_SCROLLLOCK: ("scrolllock", "SCRL"),
        pygame.K_PAUSE: ("pause", "PAUSE"),
        pygame.K_NUMLOCK: ("numlock", "NUM"),
        pygame.K_LSUPER: ("super", "SUPER"),
        pygame.K_RSUPER: ("super", "SUPER"),
        pygame.K_MENU: ("menu", "MENU"),
    }
    km.update(special)

    return km


# Shifted symbol mapping: when shift is held and a key is pressed,
# we may want a different display and sound
SHIFTED_SYMBOLS = {
    pygame.K_1: ("exclaim", "!"),
    pygame.K_2: ("at", "@"),
    pygame.K_3: ("hash", "#"),
    pygame.K_4: ("dollar", "$"),
    pygame.K_5: ("percent", "%"),
    pygame.K_6: ("caret", "^"),
    pygame.K_7: ("ampersand", "&"),
    pygame.K_8: ("asterisk", "*"),
    pygame.K_9: ("leftparen", "("),
    pygame.K_0: ("rightparen", ")"),
    pygame.K_MINUS: ("underscore", "_"),
    pygame.K_EQUALS: ("plus", "+"),
    pygame.K_LEFTBRACKET: ("leftbrace", "{"),
    pygame.K_RIGHTBRACKET: ("rightbrace", "}"),
    pygame.K_BACKSLASH: ("pipe", "|"),
    pygame.K_SEMICOLON: ("colon", ":"),
    pygame.K_QUOTE: ("doublequote", '"'),
    pygame.K_COMMA: ("less", "<"),
    pygame.K_PERIOD: ("greater", ">"),
    pygame.K_SLASH: ("question", "?"),
    pygame.K_BACKQUOTE: ("tilde", "~"),
}


# ---------------------------------------------------------------------------
# Visual effect classes
# ---------------------------------------------------------------------------
class Bubble:
    """A colorful bubble that floats upward and fades."""
    def __init__(self, x, y):
        self.x = x + random.uniform(-8, 8)
        self.y = y + random.uniform(-8, 8)
        self.radius = random.uniform(8, 22)
        self.color = random.choice(BRIGHT_COLORS)
        self.alpha = 200
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-1.5, -0.3)
        self.grow_rate = random.uniform(0.1, 0.4)
        self.fade_rate = random.uniform(80, 150)  # alpha per second
        self.alive = True

    def update(self, dt):
        self.x += self.vx * 60 * dt
        self.y += self.vy * 60 * dt
        self.radius += self.grow_rate * 60 * dt
        self.alpha -= self.fade_rate * dt
        if self.alpha <= 0 or self.radius > 60:
            self.alive = False

    def draw(self, surface):
        if not self.alive:
            return
        alpha = max(0, min(255, int(self.alpha)))
        r, g, b = self.color
        # Draw filled circle with transparency via a temp surface
        size = int(self.radius * 2) + 4
        if size < 4:
            return
        temp = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        radius_int = max(1, int(self.radius))
        pygame.draw.circle(temp, (r, g, b, alpha), (center, center), radius_int)
        # Highlight for shininess
        highlight_r = max(1, radius_int // 3)
        highlight_pos = (center - radius_int // 4, center - radius_int // 4)
        pygame.draw.circle(temp, (255, 255, 255, alpha // 3), highlight_pos, highlight_r)
        surface.blit(temp, (int(self.x) - center, int(self.y) - center))


class KeyDisplay:
    """A big letter, with the spoken word and its picture beneath it.

    Layout, when a word is being spoken:

            A            <- huge, colored
        [picture] apple  <- picture beside the word

    The picture is a frame from a sprite sheet; animated emoji cycle through
    their frames for as long as the display lives.
    """
    def __init__(self, text, screen_w, screen_h, font_large, font_small,
                 font_word=None, subtitle=None, image=None):
        self.text = text
        self.subtitle = subtitle
        self.font_word = font_word
        self.image = image
        self.color = random.choice(BRIGHT_COLORS)
        self.spawn_time = time.time()
        self.duration = KEY_DISPLAY_DURATION
        self.alive = True

        # Use the smaller font for long text (like "SPACE", "ENTER")
        if len(text) > 2:
            self.font = font_small
        else:
            self.font = font_large

        # Random position, but keep it mostly centered-ish
        self.screen_w = screen_w
        self.screen_h = screen_h
        margin_x = screen_w // 6
        margin_y = screen_h // 6
        self.x = random.randint(margin_x, screen_w - margin_x)
        self.y = random.randint(margin_y, screen_h - margin_y)

    def update(self):
        elapsed = time.time() - self.spawn_time
        if elapsed > self.duration:
            self.alive = False

    def draw(self, surface):
        if not self.alive:
            return
        elapsed = time.time() - self.spawn_time
        # Fade in for first 0.1s, hold, fade out for last 0.5s
        if elapsed < 0.1:
            alpha = int(255 * (elapsed / 0.1))
        elif elapsed > self.duration - 0.5:
            alpha = int(255 * ((self.duration - elapsed) / 0.5))
        else:
            alpha = 255
        alpha = max(0, min(255, alpha))

        # Scale effect: start slightly big, settle to normal
        if elapsed < 0.15:
            scale = 1.0 + 0.3 * (1.0 - elapsed / 0.15)
        else:
            scale = 1.0

        r, g, b = self.color
        text_surf = self.font.render(self.text, True, (r, g, b))

        if scale != 1.0:
            new_w = int(text_surf.get_width() * scale)
            new_h = int(text_surf.get_height() * scale)
            text_surf = pygame.transform.smoothscale(text_surf, (new_w, new_h))

        # Word and picture form a row under the letter; all centred as a unit.
        sub_surf = None
        if self.subtitle and self.font_word:
            sub_surf = self.font_word.render(self.subtitle, True, (r, g, b))
            sub_surf.set_alpha(alpha)

        frame, frame_size = self._current_frame(elapsed)

        row_w = row_h = 0
        if sub_surf is not None:
            row_w, row_h = sub_surf.get_width(), sub_surf.get_height()
        if frame is not None:
            row_w += frame_size + (IMAGE_GAP if sub_surf is not None else 0)
            row_h = max(row_h, frame_size)

        total_h = text_surf.get_height()
        if row_h:
            total_h += WORD_GAP + row_h
        top = self.y - total_h // 2

        # A picture-plus-word row is far wider than a bare letter, so keep the
        # whole group on screen rather than letting it run off the edge.
        widest = max(text_surf.get_width(), row_w)
        cx = min(max(self.x, widest // 2 + 8), self.screen_w - widest // 2 - 8)
        top = min(max(top, 8), self.screen_h - total_h - 8)

        text_surf.set_alpha(alpha)
        surface.blit(text_surf, text_surf.get_rect(midtop=(cx, top)))

        if row_h:
            row_y = top + text_surf.get_height() + WORD_GAP
            cursor = cx - row_w // 2
            if frame is not None:
                sheet, area = frame
                sheet.set_alpha(alpha)
                surface.blit(sheet, (cursor, row_y + (row_h - frame_size) // 2), area)
                cursor += frame_size + (IMAGE_GAP if sub_surf is not None else 0)
            if sub_surf is not None:
                surface.blit(sub_surf, (cursor, row_y + (row_h - sub_surf.get_height()) // 2))

    def _current_frame(self, elapsed):
        """Pick the sprite-sheet frame to show, or (None, 0) if no picture."""
        if not self.image:
            return None, 0
        size = self.image["size"]
        count = self.image["frames"]
        step = self.image["frame_ms"]
        index = 0
        if count > 1 and step > 0:
            index = int(elapsed * 1000 / step) % count
        area = pygame.Rect(index * size, 0, size, size)
        return (self.image["sheet"], area), size


class Stamp:
    """A shape stamped on screen from a mouse click."""
    SHAPES = ["circle", "star", "heart", "diamond", "triangle"]

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.shape = random.choice(self.SHAPES)
        self.color = random.choice(BRIGHT_COLORS)
        self.size = random.randint(40, 70)
        self.rotation = random.uniform(0, 360)
        self.spawn_time = time.time()
        self.duration = STAMP_DURATION
        self.alive = True

    def update(self):
        elapsed = time.time() - self.spawn_time
        if elapsed > self.duration:
            self.alive = False

    def draw(self, surface):
        if not self.alive:
            return
        elapsed = time.time() - self.spawn_time
        # Fade out in last second
        if elapsed > self.duration - 1.0:
            alpha = int(255 * ((self.duration - elapsed) / 1.0))
        else:
            alpha = 255
        alpha = max(0, min(255, alpha))

        # Pop-in scale
        if elapsed < 0.15:
            scale = 0.5 + 0.8 * (elapsed / 0.15)
        elif elapsed < 0.3:
            scale = 1.3 - 0.3 * ((elapsed - 0.15) / 0.15)
        else:
            scale = 1.0

        size = int(self.size * scale)
        r, g, b = self.color

        temp = pygame.Surface((size * 2 + 4, size * 2 + 4), pygame.SRCALPHA)
        cx, cy = size + 2, size + 2

        if self.shape == "circle":
            pygame.draw.circle(temp, (r, g, b, alpha), (cx, cy), size)
            pygame.draw.circle(temp, (255, 255, 255, alpha // 3), (cx, cy), size, 3)
        elif self.shape == "star":
            points = []
            for i in range(10):
                angle = math.radians(self.rotation + i * 36 - 90)
                rad = size if i % 2 == 0 else size * 0.4
                points.append((cx + rad * math.cos(angle), cy + rad * math.sin(angle)))
            pygame.draw.polygon(temp, (r, g, b, alpha), points)
        elif self.shape == "heart":
            # Simple heart shape using circles and triangle
            hs = size * 0.5
            pygame.draw.circle(temp, (r, g, b, alpha), (int(cx - hs * 0.5), int(cy - hs * 0.3)), int(hs * 0.6))
            pygame.draw.circle(temp, (r, g, b, alpha), (int(cx + hs * 0.5), int(cy - hs * 0.3)), int(hs * 0.6))
            pygame.draw.polygon(temp, (r, g, b, alpha), [
                (int(cx - hs), int(cy - hs * 0.1)),
                (int(cx + hs), int(cy - hs * 0.1)),
                (int(cx), int(cy + hs)),
            ])
        elif self.shape == "diamond":
            points = [
                (cx, cy - size),
                (cx + size * 0.6, cy),
                (cx, cy + size),
                (cx - size * 0.6, cy),
            ]
            pygame.draw.polygon(temp, (r, g, b, alpha), points)
        elif self.shape == "triangle":
            points = []
            for i in range(3):
                angle = math.radians(self.rotation + i * 120 - 90)
                points.append((cx + size * math.cos(angle), cy + size * math.sin(angle)))
            pygame.draw.polygon(temp, (r, g, b, alpha), points)

        surface.blit(temp, (self.x - cx, self.y - cy))


# ---------------------------------------------------------------------------
# Cursor drawing
# ---------------------------------------------------------------------------
def draw_cursor(surface, x, y, t):
    """Draw a big colorful custom cursor."""
    # Outer ring that color-cycles
    hue = (t * 60) % 360
    color = pygame.Color(0)
    color.hsva = (hue, 90, 100, 100)
    r, g, b = color.r, color.g, color.b

    # Glow
    glow_surf = pygame.Surface((CURSOR_RADIUS * 4, CURSOR_RADIUS * 4), pygame.SRCALPHA)
    glow_center = CURSOR_RADIUS * 2
    for i in range(CURSOR_RADIUS * 2, CURSOR_RADIUS // 2, -2):
        alpha = int(30 * (1.0 - i / (CURSOR_RADIUS * 2)))
        pygame.draw.circle(glow_surf, (r, g, b, alpha), (glow_center, glow_center), i)
    surface.blit(glow_surf, (x - glow_center, y - glow_center))

    # Main circle
    pygame.draw.circle(surface, (r, g, b), (x, y), CURSOR_RADIUS)
    # White center
    pygame.draw.circle(surface, (255, 255, 255), (x, y), CURSOR_RADIUS // 2)
    # Ring outline
    pygame.draw.circle(surface, (255, 255, 255), (x, y), CURSOR_RADIUS, 3)


# ---------------------------------------------------------------------------
# X11 input grabbing
# ---------------------------------------------------------------------------
def disable_wm_shortcuts(pygame_window_id):
    """Disable window manager shortcuts that could escape fullscreen.
    
    Uses override-redirect to tell the WM to leave this window alone,
    and grabs common escape keys. Does NOT do XGrabKeyboard since that
    conflicts with SDL's own grab (pygame.event.set_grab).
    """
    if not pygame_window_id:
        print("WARNING: No Pygame window ID, skipping WM shortcut disable")
        return None
    try:
        from Xlib import X, display as xdisplay
        d = xdisplay.Display()

        window = d.create_resource_object('window', pygame_window_id)

        # Set override-redirect so the WM doesn't manage this window
        # (no decorations, no Alt+Tab listing, no WM key interception)
        window.change_attributes(override_redirect=True)

        # Set _NET_WM_STATE to fullscreen and above
        net_wm_state = d.intern_atom('_NET_WM_STATE')
        net_wm_state_fullscreen = d.intern_atom('_NET_WM_STATE_FULLSCREEN')
        net_wm_state_above = d.intern_atom('_NET_WM_STATE_ABOVE')
        
        window.change_property(
            net_wm_state,
            d.intern_atom('ATOM'),
            32,
            [net_wm_state_fullscreen, net_wm_state_above],
        )

        d.flush()
        print(f"WM shortcuts disabled for window {pygame_window_id}")
        return d
    except Exception as e:
        print(f"WARNING: Could not disable WM shortcuts: {e}")
        return None


# ---------------------------------------------------------------------------
# Get total desktop size across all monitors
# ---------------------------------------------------------------------------
def get_desktop_size():
    """Get total desktop dimensions using xrandr."""
    try:
        output = subprocess.check_output(["xrandr", "--query"], text=True)
        # Find the line like "Screen 0: ... current 3840 x 1080"
        for line in output.splitlines():
            if "Screen" in line and "current" in line:
                # Parse: "Screen 0: minimum 8 x 8, current 3840 x 1080, maximum ..."
                parts = line.split("current")[1].split(",")[0].strip()
                w, h = parts.split(" x ")
                return int(w.strip()), int(h.strip())
    except Exception as e:
        print(f"Warning: xrandr failed: {e}")

    # Fallback: use pygame display info
    pygame.display.init()
    info = pygame.display.Info()
    return info.current_w, info.current_h


# ---------------------------------------------------------------------------
# Sound loading
# ---------------------------------------------------------------------------
def load_sound_cycles(sound_dir):
    """Load assets/sounds/manifest.json into {key: [(Sound, label), ...]}.

    The list is the cycle a key walks through on repeated presses. `label` is
    the caption to draw under the big letter, or None to show the letter alone.

    Falls back to the old flat `<key>.wav` layout so the app still makes noise
    if the sounds have not been regenerated yet.
    """
    manifest_path = os.path.join(sound_dir, "manifest.json")
    cycles = {}

    if os.path.exists(manifest_path):
        try:
            with open(manifest_path) as fh:
                manifest = json.load(fh)
            for key, entries in manifest.get("keys", {}).items():
                clips = []
                for entry in entries:
                    path = os.path.join(sound_dir, entry["file"])
                    try:
                        clips.append((pygame.mixer.Sound(path), entry.get("label")))
                    except Exception as e:
                        print(f"Warning: couldn't load {entry['file']}: {e}")
                if clips:
                    cycles[key] = clips
            if cycles:
                return cycles
            print("Warning: manifest.json had no loadable clips")
        except Exception as e:
            print(f"Warning: couldn't read manifest.json: {e}")

    print("Falling back to flat .wav layout (run generate_sounds.py)")
    if os.path.isdir(sound_dir):
        for f in sorted(os.listdir(sound_dir)):
            if f.endswith(".wav"):
                try:
                    cycles[f[:-4]] = [(pygame.mixer.Sound(os.path.join(sound_dir, f)), None)]
                except Exception as e:
                    print(f"Warning: couldn't load {f}: {e}")
    return cycles


class ImageLibrary:
    """Lazily-loaded word pictures backed by sprite sheets.

    Loading all of them up front would cost a few hundred MB of surfaces (an
    animated sheet is 30 frames of 192px RGBA), so sheets are loaded on first
    use and the least-recently-used ones are dropped past MAX_CACHED_IMAGES.
    """

    def __init__(self, image_dir):
        self.dir = image_dir
        self.meta = {}
        self._cache = collections.OrderedDict()
        manifest_path = os.path.join(image_dir, "manifest.json")
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path) as fh:
                    self.meta = json.load(fh).get("words", {})
            except Exception as e:
                print(f"Warning: couldn't read image manifest: {e}")

    def get(self, word):
        """Return {sheet, frames, frame_ms, size} for a word, or None."""
        if not word or word not in self.meta:
            return None
        if word in self._cache:
            self._cache.move_to_end(word)
            return self._cache[word]

        info = self.meta[word]
        path = os.path.join(self.dir, info["file"])
        try:
            sheet = pygame.image.load(path).convert_alpha()
        except Exception as e:
            print(f"Warning: couldn't load image {info['file']}: {e}")
            self.meta.pop(word, None)
            return None

        entry = {
            "sheet": sheet,
            "frames": info.get("frames", 1),
            "frame_ms": info.get("frame_ms", 0),
            "size": info.get("size", sheet.get_height()),
        }
        self._cache[word] = entry
        while len(self._cache) > MAX_CACHED_IMAGES:
            self._cache.popitem(last=False)
        return entry


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------
def main():
    # Get desktop size before pygame takes over
    desktop_w, desktop_h = get_desktop_size()
    print(f"Desktop size: {desktop_w} x {desktop_h}")

    # Set environment for borderless fullscreen spanning all monitors
    os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'

    pygame.init()
    pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=1024)
    pygame.mixer.set_num_channels(AUDIO_CHANNELS)

    # Create borderless window spanning full desktop
    screen = pygame.display.set_mode((desktop_w, desktop_h), pygame.NOFRAME)
    pygame.display.set_caption("Toddler Mode")

    # Get Pygame's X11 window ID (used for xdotool and X11 grab)
    pygame_wid = pygame.display.get_wm_info().get("window")

    # Try to set always-on-top via xdotool
    try:
        if pygame_wid:
            subprocess.Popen(
                ["xdotool", "set_window", "--overrideredirect", "1", str(pygame_wid)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
    except Exception:
        pass

    # Hide system cursor
    pygame.mouse.set_visible(False)

    # Grab input within pygame
    pygame.event.set_grab(True)

    # Disable key repeat so held keys don't generate spurious KEYDOWN events
    pygame.key.set_repeat(0, 0)

    # Disable WM shortcuts (Alt+Tab, Super, etc.) via X11
    # This does NOT grab the keyboard (which would conflict with SDL's grab)
    # Instead it sets override-redirect and fullscreen/above hints
    x11_display = disable_wm_shortcuts(pygame_wid)

    # Load fonts
    font_large = pygame.font.Font(None, KEY_FONT_SIZE)
    font_small = pygame.font.Font(None, KEY_FONT_SIZE // 2)
    font_word = pygame.font.Font(None, KEY_WORD_FONT_SIZE)

    # Load sounds
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sound_dir = os.path.join(script_dir, "assets", "sounds")
    sounds = load_sound_cycles(sound_dir)
    cycle_pos = {}  # key name -> index of the next utterance to play
    total_clips = sum(len(v) for v in sounds.values())
    print(f"Loaded {total_clips} clips across {len(sounds)} keys")

    images = ImageLibrary(os.path.join(script_dir, "assets", "images"))
    print(f"Found {len(images.meta)} word pictures")

    # Build key map
    key_map = build_key_map()

    # State
    bubbles: list[Bubble] = []
    key_displays: list[KeyDisplay] = []
    stamps: list[Stamp] = []
    escape_hold_start: float | None = None
    last_bubble_time = 0.0
    last_mouse_pos = pygame.mouse.get_pos()
    clock = pygame.time.Clock()
    running = True
    start_time = time.time()

    # Handle SIGTERM for clean shutdown (so 'kill <pid>' works without -9)
    def handle_sigterm(signum, frame):
        nonlocal running
        print("Received SIGTERM, shutting down...")
        running = False

    signal.signal(signal.SIGTERM, handle_sigterm)

    def play_sound(name):
        """Play the next utterance for `name` and return its on-screen label.

        Repeated presses walk the cycle: letter name -> each sound it makes
        -> words that start with it -> back to the name.
        """
        clips = sounds.get(name)
        if not clips:
            return None
        index = cycle_pos.get(name, 0) % len(clips)
        cycle_pos[name] = (index + 1) % len(clips)
        sound, label = clips[index]
        channel = pygame.mixer.find_channel()
        if channel:
            channel.play(sound)
        return label

    while running:
        dt = clock.tick(60) / 1000.0
        now = time.time()
        t = now - start_time

        # Process events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Ignore quit events (toddler-proof)
                pass

            elif event.type == pygame.KEYDOWN:
                key = event.key
                mods = pygame.key.get_mods()
                shifted = mods & (pygame.KMOD_LSHIFT | pygame.KMOD_RSHIFT)

                # Check for escape hold
                if key == pygame.K_ESCAPE:
                    if escape_hold_start is None:
                        escape_hold_start = now

                # Determine sound and display text
                if shifted and key in SHIFTED_SYMBOLS:
                    sound_name, display_text = SHIFTED_SYMBOLS[key]
                elif key in key_map:
                    sound_name, display_text = key_map[key]
                else:
                    # Unknown key - try to get unicode
                    if event.unicode and event.unicode.isprintable():
                        display_text = event.unicode.upper()
                        sound_name = None
                    else:
                        sound_name = None
                        display_text = None

                # Play first: the utterance decides what caption to show.
                label = play_sound(sound_name) if sound_name else None

                if display_text:
                    kd = KeyDisplay(display_text, desktop_w, desktop_h,
                                    font_large, font_small,
                                    font_word=font_word, subtitle=label,
                                    image=images.get(label))
                    key_displays.append(kd)
                    if len(key_displays) > MAX_KEY_DISPLAYS:
                        key_displays.pop(0)

            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_ESCAPE:
                    escape_hold_start = None

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                stamp = Stamp(mx, my)
                stamps.append(stamp)
                if len(stamps) > MAX_STAMPS:
                    stamps.pop(0)

                # Play click sound
                if event.button == 1:
                    play_sound("click")
                elif event.button == 3:
                    play_sound("rightclick")
                elif event.button == 2:
                    play_sound("middleclick")

        # Mouse position and bubble trail
        mx, my = pygame.mouse.get_pos()
        mouse_moved = (mx != last_mouse_pos[0] or my != last_mouse_pos[1])

        if mouse_moved and now - last_bubble_time > BUBBLE_SPAWN_INTERVAL:
            bubbles.append(Bubble(mx, my))
            if len(bubbles) > MAX_BUBBLES:
                bubbles.pop(0)
            last_bubble_time = now

        last_mouse_pos = (mx, my)

        # Update effects
        for b in bubbles:
            b.update(dt)
        bubbles = [b for b in bubbles if b.alive]

        for kd in key_displays:
            kd.update()
        key_displays = [kd for kd in key_displays if kd.alive]

        for s in stamps:
            s.update()
        stamps = [s for s in stamps if s.alive]

        # Check escape hold
        if escape_hold_start is not None:
            escape_elapsed = now - escape_hold_start
            if escape_elapsed >= ESCAPE_HOLD_SECONDS:
                running = False
        else:
            escape_elapsed = 0

        # -- Draw --
        screen.fill((0, 0, 0))

        # Draw stamps
        for s in stamps:
            s.draw(screen)

        # Draw bubbles
        for b in bubbles:
            b.draw(screen)

        # Draw key displays
        for kd in key_displays:
            kd.draw(screen)

        # Draw custom cursor
        draw_cursor(screen, mx, my, t)

        # Draw escape progress bar (subtle, bottom edge)
        if escape_hold_start is not None and escape_elapsed > 0:
            progress = min(1.0, escape_elapsed / ESCAPE_HOLD_SECONDS)
            bar_width = int(desktop_w * progress)
            bar_color = (100, 100, 100, 180)
            bar_rect = pygame.Rect(0, desktop_h - EXIT_BAR_HEIGHT, bar_width, EXIT_BAR_HEIGHT)
            pygame.draw.rect(screen, (100, 100, 100), bar_rect)

        pygame.display.flip()

    # Cleanup
    pygame.event.set_grab(False)
    pygame.mouse.set_visible(True)
    # No X11 keyboard/pointer ungrab needed since we don't grab them anymore
    # (SDL handles its own grab release via set_grab(False))
    pygame.quit()
    print("Toddler Mode exited cleanly.")


if __name__ == "__main__":
    main()
