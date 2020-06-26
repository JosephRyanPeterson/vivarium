from __future__ import absolute_import, division, print_function

import os
import sys
import argparse

import random
import math

import numpy as np

import matplotlib
matplotlib.use('TKAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# vivarium imports
from vivarium.library.pymunk_multibody import MultiBody
from vivarium.library.units import units, remove_units
from vivarium.core.process import Process
from vivarium.core.composition import (
    process_in_experiment,
    simulate_experiment,
    PROCESS_OUT_DIR,
)


NAME = 'circle_multibody'

DEFAULT_BOUNDS = [10, 10]
PI = math.pi


class CircleMultibody(Process):
    """
    A multi-body physics process using pymunk
    """

    defaults = {
        'agents': {},
        'bounds': DEFAULT_BOUNDS,
        'animate': False,
        'time_step': 2,
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}

        # multibody parameters
        self.bounds = self.or_default(
            initial_parameters, 'bounds')

        # make the multibody object
        multibody_config = {
            'jitter_force': jitter_force,
            'bounds': self.bounds,
        }
        self.physics = MultiBody(multibody_config)

        # interactive plot for visualization
        self.animate = initial_parameters.get('animate', self.defaults['animate'])
        if self.animate:
            plt.ion()
            self.ax = plt.gca()
            self.ax.set_aspect('equal')

        parameters = {'time_step': self.defaults['time_step']}
        parameters.update(initial_parameters)

        super(CircleMultibody, self).__init__(parameters)

    def ports_schema(self):
        glob_schema = {
            '*': {
                'boundary': {
                    'location': {
                        '_emit': True,
                        '_default': [0.5, 0.5],
                        '_updater': 'set',
                        '_divider': {
                            'divider': daughter_locations,
                            'topology': {
                                'length': ('length',),
                                'angle': ('angle',)}}},
                    'length': {
                        '_emit': True,
                        '_default': 2.0,
                        '_divider': 'split',
                        '_updater': 'set'},
                    'width': {
                        '_emit': True,
                        '_default': 1.0,
                        '_updater': 'set'},
                    'angle': {
                        '_emit': True,
                        '_default': 0.0,
                        '_updater': 'set'},
                    'mass': {
                        '_emit': True,
                        '_default': 1339 * units.fg,
                        '_updater': 'set'},
                    'thrust': {
                        '_default': 0.0,
                        '_updater': 'set'},
                    'torque': {
                        '_default': 0.0,
                        '_updater': 'set'},
                }
            }
        }
        schema = {'agents': glob_schema}
        return schema

    def next_update(self, timestep, states):
        agents = states['agents']

        # animate before update
        if self.animate:
            self.animate_frame(agents)

        # update multibody with new agents
        self.physics.update_bodies(remove_units(agents))

        # run simulation
        self.physics.run(timestep)

        # get new agent positions
        agent_positions = self.physics.get_body_positions()

        return {'agents': agent_positions}

    ## matplotlib interactive plot
    def animate_frame(self, agents):
        plt.cla()
        for agent_id, data in agents.items():
            # location, orientation, length
            data = data['boundary']
            x_center = data['location'][0]
            y_center = data['location'][1]
            angle = data['angle'] / PI * 180 + 90  # rotate 90 degrees to match field
            length = data['length']
            width = data['width']

            # get bottom left position
            x_offset = (width / 2)
            y_offset = (length / 2)
            theta_rad = math.radians(angle)
            dx = x_offset * math.cos(theta_rad) - y_offset * math.sin(theta_rad)
            dy = x_offset * math.sin(theta_rad) + y_offset * math.cos(theta_rad)

            x = x_center - dx
            y = y_center - dy

            # Create a rectangle
            rect = patches.Rectangle((x, y), width, length, angle=angle, linewidth=1, edgecolor='b')
            self.ax.add_patch(rect)

        plt.xlim([0, self.bounds[0]])
        plt.ylim([0, self.bounds[1]])
        plt.draw()
        plt.pause(0.005)

def run_growth_division():
    import ipdb; ipdb.set_trace()

if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_growth_division()
