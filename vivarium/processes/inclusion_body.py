from __future__ import absolute_import, division, print_function

import os
import random

from vivarium.library.units import units
from vivarium.core.process import Process
from vivarium.core.composition import (
    simulate_process_in_experiment,
    plot_simulation_output,
    PROCESS_OUT_DIR,
)


NAME = 'inclusion_body'


class InclusionBody(Process):
    '''
    This mock process provides a basic template that can be used for a new process
    '''

    # declare default parameters as class variables
    defaults = {
        'growth_rate': 1e-1,
        'unit_mw': 2.09e4 * units.g / units.mol,
        'molecules_list': [],
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}
        super(InclusionBody, self).__init__(initial_parameters)

        # get the parameters out of initial_parameters if available, or use defaults
        self.growth_rate = self.parameters['growth_rate']
        self.molecules_list = self.parameters['molecules_list']

    def ports_schema(self):
        front_back = [0.0, 1.0]
        random.shuffle(front_back)

        return {

            'front': {
                'inclusion_body': {
                    '_default': front_back[0],
                    '_updater': 'accumulate',
                    '_emit': True,
                    '_properties': {
                        'mw': self.parameters['unit_mw']},
                },
            },

            'back': {
                'inclusion_body': {
                    '_default': front_back[1],
                    '_updater': 'accumulate',
                    '_emit': True,
                },
            },

            'molecules': {
                mol_id: {
                    '_default': 0.0,
                    '_updater': 'accumulate',
                }
                for mol_id in self.molecules_list
            },

            'global': {
                'mass': {
                    '_emit': True,
                    '_default': 1339 * units.fg,
                    '_updater': 'set',
                    '_divider': 'split'
                },
            }
        }

    def next_update(self, timestep, states):
        # get the states
        front_body = states['front']['inclusion_body']
        back_body = states['back']['inclusion_body']


        import ipdb; ipdb.set_trace()

        update = {}
        # where is inclusion body? does it move?

        # return an update to the states
        return update


# functions to configure and run the process
def run_inclusion_body(out_dir='out'):

    # initialize the process by passing initial_parameters
    initial_parameters = {
        'molecules_list': ['glucose'],
        'growth_rate': 1e-1,
    }
    inclusion_body_process = InclusionBody(initial_parameters)

    # run the simulation
    sim_settings = {'total_time': 10}
    output = simulate_process_in_experiment(inclusion_body_process, sim_settings)

    # plot the simulation output
    plot_settings = {}
    plot_simulation_output(output, plot_settings, out_dir)


# run module is run as the main program with python vivarium/process/template_process.py
if __name__ == '__main__':
    # make an output directory to save plots
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_inclusion_body(out_dir)
