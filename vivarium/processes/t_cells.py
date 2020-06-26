from __future__ import absolute_import, division, print_function

import os
import random

from vivarium.library.units import units
from vivarium.library.dict_utils import deep_merge
from vivarium.core.process import Process
from vivarium.core.composition import (
    simulate_process_in_experiment,
    plot_simulation_output,
    PROCESS_OUT_DIR,
)
from vivarium.core.experiment import Compartment
from vivarium.processes.meta_division import MetaDivision

NAME = 'T_cell'


class TCellProcess(Process):
    """
    T-cell process with 2 states

    States:
        - PD1p (PD1+)
        - PD1n (PD1-)

    Required parameters:
        -

    Target behavior:
        - a population of (how many) PD1n cells transition to PD1p in sigmoidal fashion in ~2 weeks

    TODOs
        - make this work!
    """

    defaults = {
        'diameter': 10 * units.um,
        'initial_PD1n': 0.8,
        'transition_PD1n_to_PD1p': 0.01,  # probability/sec
        # death rates
        'death_PD1p': 7e-3,  # 0.7 / 14 hrs (Petrovas 2007)
        'death_PD1n': 2e-3,  # 0.2 / 14 hrs (Petrovas 2007)
        'death_PD1p_next_to_PDL1p': 9.5e-3,  # 0.95 / 14 hrs (Petrovas 2007)
        # IFNg_production
        'PD1n_IFNg_production': 1.6e4/3600,  # (molecules/cell/second) (Bouchnita 2017)
        'PD1p_IFNg_production': 0.0,  # (molecules/cell/second)
        # division rate (Petrovas 2007)
        'PD1n_growth': 0.9,  # probability of division in 8 hours
        'PD1p_growth': 0.05,  # probability of division in 8 hours
        # migration
        'PD1n_migration': 10.0,  # um/minute (Boissonnas 2007)
        'PD1n_migration_MHC1p_tumor': 2.0,  # um/minute (Boissonnas 2007)
        'PD1n_migration_MHC1p_tumor_dwell_time': 25.0,  # minutes (Thibaut 2020)
        'PD1p_migration': 5.0,   # um/minute (Boissonnas 2007)
        'PD1p_migration_MHC1p_tumor': 1.0,   # um/minute (Boissonnas 2007)
        'PD1p_migration_MHC1p_tumor_dwell_time': 10.0,  # minutes (Thibaut 2020)
        # killing  # TODO -- pass these to contacted tumor cells. TODO -- base this on tumor type (MHC1p, MHC1n)
        'PD1n_cytotoxic_packets': 5,  # number of packets to each contacted tumor cell
        'PD1p_cytotoxic_packets': 1,  # number of packets to each contacted tumor cell
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}
        parameters = copy.deepcopy(self.defaults)
        deep_merge(parameters, initial_parameters)
        super(TCellProcess, self).__init__(parameters)

        if random.uniform(0, 1) < self.defaults['initial_PD1n']:
            self.initial_state = 'PD1n'
        else:
            self.initial_state = 'PD1p'



    def ports_schema(self):
        return {
            'globals': {
                'divide': {
                    '_default': False,
                    '_updater': 'set'}
            },
            'internal': {
                'cell_state': {
                    '_default': self.initial_state,
                    '_emit': True,
                    '_updater': 'set'
                }
            },
            'boundary': {
                'diameter': {
                    '_default': self.parameters['diameter']
                },
                'IFNg': {
                    '_default': 0,
                    '_updater': 'accumulate',
                }
            }
        }

    def next_update(self, timestep, states):
        cell_state = states['internal']['cell_state']

        # death
        if cell_state == 'PD1n':
            if random.uniform(0, 1) < self.parameters['death_PD1n'] * timestep:
                return {
                    '_delete': {}
                }
        elif cell_state == 'PD1p':
            if random.uniform(0, 1) < self.parameters['death_PD1p'] * timestep:
                return {
                    '_delete': {}
                }

        # division
        if cell_state == 'PD1n':
            if random.uniform(0, 1) < self.parameters['PD1n_growth'] * timestep:
                return {
                    'globals': {
                        'divide': True
                    }
                }
        elif cell_state == 'PD1p':
            if random.uniform(0, 1) < self.parameters['PD1p_growth'] * timestep:
                return {
                    'globals': {
                        'divide': True
                    }
                }

        # state transition
        new_cell_state = cell_state
        IFNg = 0.0
        if cell_state == 'PD1n':
            if random.uniform(0, 1) < self.parameters['transition_PD1n_to_PD1p'] * timestep:
                new_cell_state = 'PD1p'
        elif cell_state == 'PD1p':
            pass

        # behavior
        if cell_state == 'PD1n':
            # produce IFNg  # TODO -- integer? save remainder
            IFNg = self.parameters['PD1n_IFNg_production'] * timestep

            # TODO migration

            # TODO killing -- pass cytotoxic packets to contacted tumor cells, based on tumor type

        elif cell_state == 'PD1p':

            # produce IFNg  # TODO -- integer? save remainder
            IFNg = self.parameters['PD1p_IFNg_production'] * timestep


        return {
            'internal': {
                'cell_state': new_cell_state
            },
            'boundary': {
                'IFNg': IFNg
            },
        }



class TCellCompartment(Compartment):

    defaults = {
        'boundary_path': ('boundary',),
        'agents_path': ('..', '..', 'agents',),
        'daughter_path': tuple()}

    def __init__(self, config):
        self.config = config
        for key, value in self.defaults.items():
            if key not in self.config:
                self.config[key] = value

        # paths
        self.boundary_path = config.get('boundary_path', self.defaults['boundary_path'])
        self.agents_path = config.get('agents_path', self.defaults['agents_path'])

    def generate_processes(self, config):
        daughter_path = config['daughter_path']
        agent_id = config['agent_id']

        division_config = dict(
            config.get('division', {}),
            daughter_path=daughter_path,
            agent_id=agent_id,
            compartment=self)

        t_cell = TCellProcess(config.get('growth', {}))
        division = MetaDivision(division_config)

        return {
            't_cell': t_cell,
            'division': division}

    def generate_topology(self, config):
        return {
            't_cell': {
                'internal': ('internal',),
                'boundary': self.boundary_path,
                'global': self.boundary_path},
            'division': {
                'global': self.boundary_path,
                'cells': self.agents_path},
            }



def run_t_cells():
    t_cell_process = TCellProcess({})
    settings = {'total_time': 1000}
    timeseries = simulate_process_in_experiment(t_cell_process, settings)

    import ipdb;
    ipdb.set_trace()


if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    run_t_cells()
