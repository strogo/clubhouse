import glob
import json
import os
import random

from gi.repository import GLib, Gtk, GObject, GdkPixbuf


class AnimationImage(Gtk.Image):
    def __init__(self, path):
        super().__init__()
        self._animator = Animator(self)
        self._animator.load(path)

    def play(self, name):
        self._animator.play(name)


class Animator:

    def __init__(self, target_image):
        self._animations = {}
        self._target_image = target_image

    def load(self, path, prefix=None):
        for sprite in glob.glob(os.path.join(path, '*png')):
            name, _ext = os.path.splitext(os.path.basename(sprite))
            animation = Animation(sprite, self._target_image)
            animation_name = name if prefix is None else '{}/{}'.format(prefix, name)
            self._animations[animation_name] = animation

    def play(self, name):
        AnimationSystem.animate(id(self), self._animations[name])

    def has_animation(self, name):
        return self._animations.get(name) is not None


class Animation(GObject.GObject):
    def __init__(self, path, target_image):
        super().__init__()
        self.frames = []
        self.frame_index = 0
        self.last_updated = None
        self.target_image = target_image
        self.load(path)
        self._set_current_frame_delay()

    def advance_frame(self):
        # The animations play in loop for now
        self.frame_index += 1
        if self.frame_index >= len(self.frames):
            self.frame_index = 0

        self._set_current_frame_delay()

    def _get_current_frame(self):
        return self.frames[self.frame_index]

    def _set_current_frame_delay(self):
        delay = self.current_frame['delay']
        if not isinstance(delay, str):
            return

        delay_a, delay_b = delay.split('-')
        new_delay = random.randint(int(delay_a), int(delay_b))
        self.current_frame['delay'] = new_delay

    def update_image(self):
        pixbuf = self.current_frame['pixbuf']
        self.target_image.set_from_pixbuf(pixbuf)

    def load(self, sprite_path):
        metadata = self.get_animation_metadata(sprite_path)
        sprite_pixbuf = GdkPixbuf.Pixbuf.new_from_file(sprite_path)
        sprite_width = sprite_pixbuf.get_width()

        subpixbufs = []
        for offset_x in range(0, sprite_width, metadata['width']):
            pixbuf = GdkPixbuf.Pixbuf.new_subpixbuf(sprite_pixbuf,
                                                    offset_x, 0,
                                                    metadata['width'],
                                                    metadata['height'])
            subpixbufs.append(pixbuf)

        # @todo: Add 'frames' metadata to the format, to repeat frames
        # with a different delay.
        if 'delays' in metadata:
            for pixbuf, delay in zip(subpixbufs, metadata['delays']):
                # GTK needs the delay in microseconds:
                delay = self._convert_delay_to_microseconds(delay)
                self.frames.append({'pixbuf': pixbuf, 'delay': delay})

    current_frame = property(_get_current_frame)

    @staticmethod
    def _convert_delay_to_microseconds(delay):
        if isinstance(delay, str):
            delay_a, delay_b = delay.split('-')
            return ('{}-{}'.format(int(delay_a) * 1000, int(delay_b) * 1000))
        return delay * 1000

    @staticmethod
    def get_animation_metadata(image_path, load_json=True):
        metadata = None
        image_name, _ext = os.path.splitext(image_path)
        metadata_path = image_name + '.json'
        with open(metadata_path) as f:
            if load_json:
                metadata = json.load(f)
            else:
                metadata = f.read()

        return metadata


class AnimationSystem:
    _animations = {}

    @classmethod
    def animate(class_, id_, animation):
        class_._animations[id_] = animation
        animation.update_image()

    @classmethod
    def step(class_, _widget, clock):
        timestamp = clock.get_frame_time()

        for animation in class_._animations.values():
            if animation.last_updated is None:
                animation.last_updated = timestamp

            elapsed = timestamp - animation.last_updated

            if elapsed >= animation.current_frame['delay']:
                animation.advance_frame()
                animation.update_image()

                animation.last_updated = timestamp

        return GLib.SOURCE_CONTINUE
