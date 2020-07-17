from __future__ import absolute_import, division, print_function

import os
import sys
import copy
import random

from vivarium.library.units import units
from vivarium.library.dict_utils import deep_merge
from vivarium.core.process import Process
from vivarium.core.composition import (
    simulate_process_in_experiment,
    plot_simulation_output,
    PROCESS_OUT_DIR,
)
from vivarium.core.process import Generator
from vivarium.processes.meta_division import MetaDivision


NAME = 'T_cell'


class TCellProcess(Process):
    """T-cell process with 2 states

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

    name = 't_cell'
    defaults = {
        'diameter': 10 * units.um,
        'initial_PD1n': 0.8,
        'transition_PD1n_to_PD1p': 0.01,  # probability/sec
        # death rates
        'death_PD1p': 7e-3,  # 0.7 / 14 hrs (Petrovas 2007)
        'death_PD1n': 2e-3,  # 0.2 / 14 hrs (Petrovas 2007)
        'death_PD1p_next_to_PDL1p': 9.5e-3,  # 0.95 / 14 hrs (Petrovas 2007)
        # production rates
        'PD1n_IFNg_production': 1.6e4/3600,  # (molecules/cell/second) (Bouchnita 2017)
        'PD1p_IFNg_production': 0.0,  # (molecules/cell/second)
        'PD1p_PD1_equilibrium': 5e4,  # equilibrium value of PD1 for PD1p (TODO -- get reference)
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
        # settings
        'self_path': tuple(),
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

        self.self_path = self.or_default(
            initial_parameters, 'self_path'
        )

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
                    '_emit': True,
                    '_updater': 'accumulate',
                },
                'PD1': {
                    '_default': 0,
                    '_emit': True,
                    '_updater': 'set',
                },  # membrane protein, promotes T-cell death
                'cytotoxic_packets': {},  # release into the tumor cells
            },
            'neighbors': {
                'PDL1': {},
                'MHC1': {},
            }
        }

    def next_update(self, timestep, states):
        cell_state = states['internal']['cell_state']

        # death
        if cell_state == 'PD1n':
            if random.uniform(0, 1) < self.parameters['death_PD1n'] * timestep:
                print('PD1n DEATH!')
                return {
                    '_delete': {
                        'path': self.self_path
                    }
                }
        elif cell_state == 'PD1p':
            if random.uniform(0, 1) < self.parameters['death_PD1p'] * timestep:
                print('PD1p DEATH!')
                return {
                    '_delete': {
                        'path': self.self_path
                    }
                }

        # division
        if cell_state == 'PD1n':
            if random.uniform(0, 1) < self.parameters['PD1n_growth'] * timestep:
                print('PD1n DIVIDE!')
                return {
                    'globals': {
                        'divide': True
                    }
                }
        elif cell_state == 'PD1p':
            if random.uniform(0, 1) < self.parameters['PD1p_growth'] * timestep:
                print('PD1p DIVIDE!')
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
        IFNg = 0
        PD1 = 0
        cytotoxic_packets = 0

        # TODO migration
        #  #also dependent on MHCI+
        #  #50% bound vs. 30% bound in flow cytometry experiment on low vs. high
        #  #@Eran how do I reference a parameter from tumors process that influences migration?
        #  Also, how do I reference the environment here? You might already have migration modules,
        #  so maybe we should do this one together.

        # TODO killing -- pass cytotoxic packets to contacted tumor cells, based on tumor type
        if new_cell_state == 'PD1n':
            # produce IFNg  # TODO -- integer? save remainder
            #TODO - @Eran - What will we decide on time step? I can base these
            # parameters/calculate based on that decision
            IFNg = self.parameters['PD1n_IFNg_production'] * timestep

            # cytotoxic_packets = f(PDL1, MHC1, PD1)
            #TODO cytotoxic packets -
            # @Eran - I have done the research with packets and think I have a good place to start -
            #   I think that the key thing will be to describe an activation event that happens once
            #   the T cell encounters the tumor and depending on the states will dictate the rate of
            #   production of cytotoxic packets and assume passage is equal. How do we save such an
            #   occurance of contact?
            # Max production happens for PD1- T cells in contact with MHCI+ tumor
            #   linear production over 4 hr up to a total of 102+-20 granules
            # #MHCI activates the T cell for production
            #   #4 fold reduction in killing packet production when low level of MHCI+
            # #1:10 fold reduction of PD1+ T cell cytotoxic production
            # #target behavior 3 contacts required for cell death, 1-4 cells killed/day
            # similar reductions for IFNg expression with less MHCI+ - production will mirror each other


            # self.parameters['PD1n_cytotoxic_packets']

        elif new_cell_state == 'PD1p':
            # produce IFNg  # TODO -- integer? save remainder
            IFNg = self.parameters['PD1p_IFNg_production'] * timestep
            PD1 = self.parameters['PD1p_PD1_equilibrium']

            # cytotoxic_packets = function(PDL1, MHC1, PD1) TODO -- get this
            # self.parameters['PD1p_cytotoxic_packets']

        return {
            'internal': {
                'cell_state': new_cell_state
            },
            'boundary': {
                'IFNg': IFNg,
                'PD1': PD1,
                'cytotoxic_packets': cytotoxic_packets,
            },
        }



class TCellCompartment(Generator):

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



def test_single_t_cell(total_time=20, out_dir='out'):
    t_cell_process = TCellProcess({})
    settings = {'total_time': total_time}
    timeseries = simulate_process_in_experiment(t_cell_process, settings)

    # plot
    plot_settings = {}
    plot_simulation_output(timeseries, plot_settings, out_dir)


def run_batch_t_cells(out_dir='out'):
    import ipdb; ipdb.set_trace()
    pass

if __name__ == '__main__':
    out_dir = os.path.join(PROCESS_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    parser = argparse.ArgumentParser(description='ODE expression')
    parser.add_argument('--single', '-s', action='store_true', default=False)
    parser.add_argument('--batch', '-b', action='store_true', default=False)
    args = parser.parse_args()
    no_args = (len(sys.argv) == 1)

    total_time = 1000
    if args.single or no_args:
        test_single_t_cell(
            total_time,
            out_dir)

    if args.batch:
        run_batch_t_cells(
            out_dir,
            total_time)
