"""
Audio manager: mixer lifecycle with graceful degradation, lazy SFX/music
caching, dedicated music channel, master/music/SFX volume and M-key mute.
The game must run fine (muted) when no audio device is available.
"""

import pygame

from src.config import AUDIO_RATE, MASTER_VOLUME, MUSIC_VOLUME, SFX_VOLUME
from src.audio import music_synthesizer as music
from src.audio import sfx_synthesizer as sfx

_SFX_BYTES = {}        # raw sample caches (shared across AudioManager)
_MUSIC_BYTES = {}


class AudioManager:
    NUM_CHANNELS = 12

    def __init__(self):
        self.enabled = False
        self.muted = False
        self._sfx = {}
        self._music = {}
        self._music_name = None
        self._music_channel = None
        try:
            if pygame.mixer.get_init() is not None:
                pygame.mixer.quit()
            pygame.mixer.init(AUDIO_RATE, -16, 2, 512)
            pygame.mixer.set_num_channels(self.NUM_CHANNELS)
            self.enabled = True
        except pygame.error:
            self.enabled = False
            return
        for name in sfx.EAGER_SFX:
            self._load_sfx(name)

    # ---------------------------------------------------------------- sfx
    def _load_sfx(self, name):
        snd = self._sfx.get(name)
        if snd is None:
            raw = _SFX_BYTES.get(name)
            if raw is None:
                raw = sfx.SFX_BUILDERS[name]()
                _SFX_BYTES[name] = raw
            snd = pygame.mixer.Sound(buffer=raw)
            self._sfx[name] = snd
        return snd

    def play_sfx(self, name, vol=1.0):
        if not self.enabled or self.muted:
            return None
        try:
            snd = self._load_sfx(name)
        except (pygame.error, KeyError):
            return None
        ch = snd.play()
        if ch is not None:
            ch.set_volume(min(1.0, vol * SFX_VOLUME * MASTER_VOLUME))
        return ch

    # -------------------------------------------------------------- music
    def _get_music(self, name):
        cached = self._music.get(name)
        if cached is None:
            raw = _MUSIC_BYTES.get(name)
            if raw is None:
                raw = music.MUSIC_BUILDERS[name]()
                _MUSIC_BYTES[name] = raw
            cached = pygame.mixer.Sound(buffer=raw)
            self._music[name] = cached
        return cached

    def play_music(self, name):
        if not self.enabled:
            return
        if self._music_name == name and self._music_channel is not None \
                and self._music_channel.get_busy():
            return
        self.stop_music(fade=150)
        try:
            snd = self._get_music(name)
        except (pygame.error, KeyError):
            return
        loops = -1 if name in music.LOOPING_MUSIC else 0
        if self.muted:
            self._music_name = name
            return                      # remember, stay silent
        ch = snd.play(loops=loops, fade_ms=250)
        if ch is not None:
            ch.set_volume(MUSIC_VOLUME * MASTER_VOLUME)
            self._music_channel = ch
        self._music_name = name

    def stop_music(self, fade=200):
        if self._music_channel is not None and self.enabled:
            try:
                self._music_channel.fadeout(fade)
            except pygame.error:
                pass
        self._music_channel = None
        self._music_name = None

    def duck_music(self, ducked):
        """Pause-style volume duck (pause screen / menus)."""
        if not self.enabled or self._music_channel is None:
            return
        factor = 0.4 if ducked else 1.0
        vol = MUSIC_VOLUME * MASTER_VOLUME * factor
        try:
            self._music_channel.set_volume(vol if not self.muted else 0.0)
        except pygame.error:
            pass

    # --------------------------------------------------------------- mute
    def toggle_mute(self):
        self.muted = not self.muted
        if not self.enabled:
            return self.muted
        if self.muted:
            if self._music_channel is not None:
                try:
                    self._music_channel.pause()
                except pygame.error:
                    pass
        else:
            if self._music_channel is not None:
                try:
                    self._music_channel.unpause()
                    self._music_channel.set_volume(
                        MUSIC_VOLUME * MASTER_VOLUME)
                except pygame.error:
                    pass
            elif self._music_name:
                name = self._music_name
                self._music_name = None
                self.play_music(name)
        return self.muted

    @property
    def current_music(self):
        return self._music_name
