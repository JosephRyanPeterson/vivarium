from __future__ import absolute_import, division, print_function

import os
import sys
import uuid
import argparse

from vivarium.core.experiment import (
    generate_state,
    Experiment
)
from vivarium.core.composition import (
    agent_environment_experiment,
    # make_agents,
    simulate_experiment,
    plot_agents_multigen,
    EXPERIMENT_OUT_DIR,
)

from vivarium.plots.multibody_physics import plot_snapshots

# compartments
from vivarium.compartments.lattice import Lattice
from vivarium.compartments.growth_division import GrowthDivision
from vivarium.compartments.growth_division_minimal import GrowthDivisionMinimal


NAME = 'lattice'
DEFAULT_ENVIRONMENT_TYPE = Lattice

agents_library = {
    'growth_division': {
        'name': 'growth_division',
        'type': GrowthDivision,
        'config': {
            'agents_path': ('..', '..', 'agents'),
        }
    },
    'growth_division_minimal': {
        'name': 'growth_division_minimal',
        'type': GrowthDivisionMinimal,
        'config': {
            'agents_path': ('..', '..', 'agents'),
            'growth_rate': 0.01,
            'division_volume': 2.6
        }
    },
}

def get_lattice_config():
    bounds = [20, 20]
    n_bins = [10, 10]
    molecules = ['glc__D_e', 'lcts_e']

    environment_config = {
        'multibody': {
            'bounds': bounds,
            'agents': {}
        },
        'diffusion': {
            'molecules': molecules,
            'n_bins': n_bins,
            'bounds': bounds,
            'depth': 3000.0,
            'diffusion': 1e-2,
        }
    }
    return environment_config


def run_lattice_experiment(
    agents_config=None,
    environment_config=None,
    initial_state=None,
    simulation_settings=None,
    experiment_settings=None):
    if experiment_settings is None:
        experiment_settings = {}
    if initial_state is None:
        initial_state = {}

    total_time = simulation_settings['total_time']
    emit_step = simulation_settings['emit_step']

    # agents ids
    agent_ids = []
    for config in agents_config:
        number = config['number']
        if 'name' in config:
            name = config['name']
            if number > 1:
                new_agent_ids = [name + '_' + str(num) for num in range(number)]
            else:
                new_agent_ids = [name]
        else:
            new_agent_ids = [str(uuid.uuid1()) for num in range(number)]
        config['ids'] = new_agent_ids
        agent_ids.extend(new_agent_ids)

    # make the experiment
    experiment = agent_environment_experiment(
        agents_config,
        environment_config,
        initial_state,
        experiment_settings)

    # simulate
    settings = {
        'total_time': total_time,
        'emit_step': emit_step,
        'return_raw_data': True}
    return simulate_experiment(experiment, settings)


def run_growth_division(agent_type='growth_division'):
    agent_config = agents_library[agent_type]
    agent_config['number'] = 1
    agents_config = [
        agent_config,
    ]

    environment_config = {
        'type': DEFAULT_ENVIRONMENT_TYPE,
        'config': get_lattice_config(),
    }

    # configure the simulation
    total_time = 10
    emit_step = 1
    simulation_settings = {
        'total_time': total_time,
        'emit_step': emit_step,
    }

    # simulate
    data = run_lattice_experiment(
        agents_config=agents_config,
        environment_config=environment_config,
        simulation_settings=simulation_settings,
    )

    # extract data
    multibody_config = environment_config['config']['multibody']
    agents = {time: time_data['agents'] for time, time_data in data.items()}
    fields = {time: time_data['fields'] for time, time_data in data.items()}

    # agents plot
    plot_settings = {
        'agents_key': 'agents'}
    plot_agents_multigen(data, plot_settings, out_dir, agent_type)

    # snapshot plot
    data = {
        'agents': agents,
        'fields': fields,
        'config': multibody_config}
    plot_config = {
        'out_dir': out_dir,
        'filename': agent_type + '_snapshots'}
    plot_snapshots(data, plot_config)



if __name__ == '__main__':
    out_dir = os.path.join(EXPERIMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    parser = argparse.ArgumentParser(description='lattice_experiment')
    parser.add_argument('--gd', '-g', action='store_true', default=False)
    parser.add_argument('--gd_minimal', '-m', action='store_true', default=False)
    args = parser.parse_args()
    no_args = (len(sys.argv) == 1)

    if args.gd_minimal or no_args:
        run_growth_division('growth_division_minimal')
    elif args.gd:
        run_growth_division('growth_division')
