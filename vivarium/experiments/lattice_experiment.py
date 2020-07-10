from __future__ import absolute_import, division, print_function

import os
import sys
import argparse

from vivarium.core.experiment import (
    Experiment
)
from vivarium.core.composition import (
    agent_environment_experiment,
    simulate_experiment,
    plot_agents_multigen,
    EXPERIMENT_OUT_DIR,
)
from vivarium.plots.multibody_physics import plot_snapshots

# compartments
from vivarium.compartments.lattice import Lattice
from vivarium.compartments.growth_division import GrowthDivision
from vivarium.compartments.growth_division_minimal import GrowthDivisionMinimal
from vivarium.compartments.transport_metabolism import TransportMetabolism



NAME = 'lattice'
DEFAULT_ENVIRONMENT_TYPE = Lattice


# agents and their configurations
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
            'growth_rate': 0.001,
            'division_volume': 2.6
        }
    },
    'transport_metabolism': {
        'name': 'transport_metabolism',
        'type': TransportMetabolism,
        'config': {
            'agents_path': ('..', '..', 'agents'),
        }
    },
}

def get_lattice_config(
    bounds=[20, 20],
    n_bins=[10, 10],
    jitter_force=1e-4,
    depth=3000.0,
    diffusion=1e-2,
    molecules=['glc__D_e', 'lcts_e'],
):
    environment_config = {
        'multibody': {
            'bounds': bounds,
            'jitter_force': jitter_force,
            'agents': {}
        },
        'diffusion': {
            'molecules': molecules,
            'n_bins': n_bins,
            'bounds': bounds,
            'depth': depth,
            'diffusion': diffusion,
        }
    }
    return environment_config

def get_simulation_settings(
        total_time=2000,
        emit_step=10,
        return_raw_data=True,
):
    return {
        'total_time': total_time,
        'emit_step': emit_step,
        'return_raw_data': return_raw_data
    }


def run_lattice_experiment(
        agents_config=None,
        environment_config=None,
        initial_state=None,
        simulation_settings=None,
        experiment_settings=None
):
    if experiment_settings is None:
        experiment_settings = {}
    if initial_state is None:
        initial_state = {}

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


    experiment_settings['emitter'] = {
        'type': 'database',
        'host': 'mongodb+srv://cyteam_user:cy2019!@cyteam-db-sanud.gcp.mongodb.net/vivarium?retryWrites=true&w=majority',
        'database': 'simulations2'}



    # make the experiment
    experiment = agent_environment_experiment(
        agents_config,
        environment_config,
        initial_state,
        experiment_settings
    )


    # simulate
    settings = {
        'total_time': simulation_settings['total_time'],
        'emit_step': simulation_settings['emit_step'],
        'return_raw_data': simulation_settings['return_raw_data']}
    return simulate_experiment(
        experiment,
        settings,
    )


def run_growth_division(
        agent_type='growth_division_minimal',
        out_dir='out',
        simulation_settings=get_simulation_settings()
):
    agent_config = agents_library[agent_type]
    agent_config['number'] = 1
    agents_config = [
        agent_config,
    ]

    environment_config = {
        'type': DEFAULT_ENVIRONMENT_TYPE,
        'config': get_lattice_config(),
    }

    # simulate
    data = run_lattice_experiment(
        agents_config=agents_config,
        environment_config=environment_config,
        simulation_settings=simulation_settings,
    )
    plot_growth_division_output(
        data,
        environment_config,
        agent_type,
        out_dir
    )

def plot_growth_division_output(
        data,
        environment_config,
        agent_type='agent',
        out_dir='out'
):
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


def test_growth_division_experiment():
    growth_rate = 0.005  # fast!
    total_time = 150

    # get minimal agent config and set growth rate
    agent_config = agents_library['growth_division_minimal']
    agent_config['config']['growth_rate'] = growth_rate
    agent_config['number'] = 1
    agents_config = [agent_config]

    # get environment config
    environment_config = {
        'type': DEFAULT_ENVIRONMENT_TYPE,
        'config': get_lattice_config(),
    }

    # simulate
    simulation_settings = get_simulation_settings(
        total_time=total_time,
        return_raw_data=True)
    data = run_lattice_experiment(
        agents_config=agents_config,
        environment_config=environment_config,
        simulation_settings=simulation_settings,
    )

    # assert division
    time = list(data.keys())
    initial_agents = len(data[time[0]]['agents'])
    final_agents = len(data[time[-1]]['agents'])
    assert final_agents > initial_agents


def make_dir(out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

if __name__ == '__main__':
    out_dir = os.path.join(EXPERIMENT_OUT_DIR, NAME)
    make_dir(out_dir)

    parser = argparse.ArgumentParser(description='lattice_experiment')
    parser.add_argument('--growth_division', '-g', action='store_true', default=False)
    parser.add_argument('--growth_division_minimal', '-m', action='store_true', default=False)
    parser.add_argument('--transport_metabolism', '-t', action='store_true', default=False)
    args = parser.parse_args()
    no_args = (len(sys.argv) == 1)

    if args.growth_division_minimal or no_args:
        minimal_out_dir = os.path.join(out_dir, 'minimal')
        make_dir(minimal_out_dir)
        run_growth_division(
            agent_type='growth_division_minimal',
            out_dir=minimal_out_dir)

    elif args.growth_division:
        gd_out_dir = os.path.join(out_dir, 'growth_division')
        make_dir(gd_out_dir)
        run_growth_division(
            agent_type='growth_division',
            out_dir=gd_out_dir)

    elif args.transport_metabolism:
        txp_mtb_out_dir = os.path.join(out_dir, 'transport_metabolism')
        make_dir(txp_mtb_out_dir)
        run_growth_division(
            agent_type='transport_metabolism',
            out_dir=txp_mtb_out_dir)
