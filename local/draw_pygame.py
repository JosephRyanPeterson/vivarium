import os

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
from pygame.locals import *
from pygame.color import *

import pymunk.pygame_util

from vivarium.library.pymunk_multibody import test_multibody


class DrawPygame(object):
    defaults = {}

    def __init__(self):
        self.running = False  # TODO -- is this used?
        self.screen = None

    def configure(self, config):
        self.bounds = config['bounds']
        self.space = config['space']

        pygame.init()
        self.screen = pygame.display.set_mode((
            int(self.bounds[0]),
            int(self.bounds[1])),
            RESIZABLE)
        self.clock = pygame.time.Clock()
        self.draw_options = pymunk.pygame_util.DrawOptions(self.screen)

    def process_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN and event.key == K_ESCAPE:
                self.running = False

    def clear_screen(self):
        self.screen.fill(THECOLORS["white"])

    def draw_objects(self):
        self.space.debug_draw(self.draw_options)

    def update_screen(self):
        self.process_events()
        self.clear_screen()
        self.draw_objects()
        pygame.display.flip()

        # Delay fixed time between frames
        self.clock.tick(2)


if __name__ == '__main__':
    test_multibody(
        total_time=60,
        n_agents=10,
        jitter_force=1e2,
        agent_shape='segment',
        screen=DrawPygame())
