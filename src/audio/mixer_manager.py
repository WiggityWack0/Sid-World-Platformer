"""
Audio manager: mixer lifecycle with graceful degradation, lazy SFX/music
caching, dedicated music channel, master/music/SFX volume and M-key mute.
The game must run fine (muted) when no audio device is available.
"""

import pygame

from src import config
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
        # live, settings-driven volumes (6a); config constants are defaults
        self.master_volume = MASTER_VOLUME
        self.music_volume = MUSIC_VOLUME
        self.sfx_volume = SFX_VOLUME
        self._ducked = False
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
            ch.set_volume(min(1.0, vol * self.sfx_volume
                              * self.master_volume))
        return ch

    @staticmethod
    def _pan_gains(world_x, listener_x):
        """Pure pan/falloff math (6c): balance -1 (left) .. +1 (right),
        linear distance gain 1 (centered) .. 0 (at SPATIAL_RANGE)."""
        dx = world_x - listener_x
        balance = max(-1.0, min(1.0, dx / config.SPATIAL_PAN_PX))
        gain = max(0.0, 1.0 - abs(dx) / config.SPATIAL_RANGE)
        return balance, gain

    def play_sfx_at(self, name, world_x, listener_x, vol=1.0):
        """Positional one-shot: stereo balance + distance falloff (6c).
        Falls back to silence beyond range; plain play_sfx when muted/off
        is unchanged (graceful degradation)."""
        if not self.enabled or self.muted:
            return None
        balance, gain = self._pan_gains(world_x, listener_x)
        if gain <= 0.0:
            return None
        try:
            snd = self._load_sfx(name)
        except (pygame.error, KeyError):
            return None
        ch = snd.play()
        if ch is not None:
            base = min(1.0, vol * self.sfx_volume
                       * self.master_volume * gain)
            ch.set_volume(base * (1.0 - max(0.0, balance)),
                          base * (1.0 + min(0.0, balance)))
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
            ch.set_volume(self.music_volume * self.master_volume)
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
        self._ducked = bool(ducked)
        if not self.enabled or self._music_channel is None:
            return
        factor = 0.4 if ducked else 1.0
        vol = self.music_volume * self.master_volume * factor
        try:
            self._music_channel.set_volume(vol if not self.muted else 0.0)
        except pygame.error:
            pass

    def apply_settings(self, settings):
        """Live-apply persisted settings (6a, consumes 4c's schema)."""
        try:
            self.master_volume = float(
                settings.get("master_volume", MASTER_VOLUME))
            self.music_volume = float(
                settings.get("music_volume", MUSIC_VOLUME))
            self.sfx_volume = float(
                settings.get("sfx_volume", SFX_VOLUME))
        except (TypeError, ValueError):
            pass
        muted = settings.get("muted")
        if isinstance(muted, bool) and muted != self.muted:
            self.toggle_mute()
        elif not self.muted and self.enabled and self._music_channel:
            factor = 0.4 if self._ducked else 1.0
            try:
                self._music_channel.set_volume(
                    self.music_volume * self.master_volume * factor)
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
                        self.music_volume * self.master_volume
                        * (0.4 if self._ducked else 1.0))
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
