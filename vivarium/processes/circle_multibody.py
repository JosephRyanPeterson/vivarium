from __future__ import absolute_import, division, print_function

import os
import sys
import argparse
import random
import math

import numpy as np

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# vivarium imports
from vivarium.library.pymunk_multibody import PymunkMultibody
from vivarium.library.units import units, remove_units
from vivarium.core.process import Process
from vivarium.core.composition import (
    simulate_process_in_experiment,
    PROCESS_OUT_DIR,
)


NAME = 'circle_multibody'

DEFAULT_BOUNDS = [10, 10]
PI = math.pi


def volume_from_length(length, width):
    '''
    inverse of length_from_volume
    '''
    radius = width / 2
    cylinder_length = length - width
    volume = cylinder_length * (PI * radius**2) + (4 / 3) * PI * radius**3
    return volume


def make_random_position(bounds):
    return [
        np.random.uniform(0, bounds[0]),
        np.random.uniform(0, bounds[1])]



class CircleMultibody(Process):
    """
    A multi-body physics process with circular agents
    """

    name = NAME
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
            'bounds': self.bounds,
        }
        self.physics = PymunkMultibody(multibody_config)

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
                            'divider': 'set',
                            'topology': {
                                'length': ('length',),
                            }
                        }
                    },
                    'diameter': {
                        '_emit': True,
                        '_default': 1.0,
                        '_divider': 'set',
                        '_updater': 'set'},
                    'mass': {
                        '_emit': True,
                        '_default': 1 * units.fg,
                        '_updater': 'set'},
                }
            }
        }
        schema = {'agents': glob_schema}
        return schema

    def next_update(self, timestep, states):
        agents = states['agents']

        import ipdb;
        ipdb.set_trace()

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


def run_circle_world():
    circle_world = CircleMultibody({})

    timeline = [
        (0, {('agents',): {
            '_add': {
                'path': ('1',),
                'state': {},
            }}}),
        # (0, {tuple(): {
        #     'agents': {
        #         '_add': {
        #             'path': ('1',),
        #             'state': {},
        #         }}}}),
        # (60, {('agents', 'flagella'): 6}),
        # (200, {('agents', 'flagella'): 7}),
        (240, {})]

    settings = {
        'timeline': {'timeline': timeline},
        'return_raw_data': False
    }
    data = simulate_process_in_experiment(circle_world, settings)

    import ipdb;
    ipdb.set_trace()






if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_circle_world()
