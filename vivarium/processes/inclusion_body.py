from __future__ import absolute_import, division, print_function

import os

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
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}
        super(InclusionBody, self).__init__(initial_parameters)

        # get the parameters out of initial_parameters if available, or use defaults
        self.growth_rate = self.parameters['growth_rate']

    def ports_schema(self):

        return {
            'front': {
                'inclusion_body': {
                    '_default': 1.0,
                    '_updater': 'accumulate',
                    '_emit': True,
                }
            },
            'back': {
                'inclusion_body': {
                    '_default': 0.0,
                    '_updater': 'accumulate',
                    '_emit': True,
                }
            },
        }

    def next_update(self, timestep, states):
        # get the states
        front_body = states['front']['inclusion_body']
        back_body = states['back']['inclusion_body']

        update = {}
        # where is inclusion body? does it move?

        # return an update to the states
        return update


# functions to configure and run the process
def run_inclusion_body(out_dir='out'):
    # initialize the process by passing initial_parameters
    initial_parameters = {}
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
