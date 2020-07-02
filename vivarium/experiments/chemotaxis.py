'''
====================
Chemotaxis Experiments
====================

Chemotaxis provides several pre-configured :py:class:`Experiments`
with different chemotactic agents and environments.
'''

from __future__ import absolute_import, division, print_function

import os
import copy
import sys
import argparse

from arpeggio import (
    RegExMatch,
    ParserPython,
    OneOrMore,
)

from vivarium.library.dict_utils import deep_merge
from vivarium.core.emitter import timeseries_from_data
from vivarium.core.composition import (
    agent_environment_experiment,
    make_agents,
    simulate_experiment,
    plot_agents_multigen,
    process_in_compartment,
    EXPERIMENT_OUT_DIR,
)

# compartments
from vivarium.compartments.static_lattice import StaticLattice
from vivarium.compartments.chemotaxis_minimal import ChemotaxisMinimal
from vivarium.compartments.chemotaxis_master import ChemotaxisMaster
from vivarium.compartments.chemotaxis_flagella import (
    ChemotaxisVariableFlagella,
    ChemotaxisExpressionFlagella,
    ChemotaxisODEExpressionFlagella,
)

# processes
from vivarium.processes.Vladimirov2008_motor import MotorActivity
from vivarium.processes.multibody_physics import agent_body_config
from vivarium.processes.static_field import make_field

# plots
from vivarium.plots.multibody_physics import (
    plot_temporal_trajectory,
    plot_agent_trajectory,
    plot_motility,
)


# make an agent from a lone MotorActivity process
MotorActivityAgent = process_in_compartment(
    MotorActivity,
    paths={
        'external': ('boundary',),
        'internal': ('cell',)
    })

# defaults
DEFAULT_BOUNDS = [1000, 3000]
DEFAULT_AGENT_LOCATION = [0.5, 0.1]
DEFAULT_LIGAND_ID = 'MeAsp'
DEFAULT_INITIAL_LIGAND = 25.0
DEFAULT_ENVIRONMENT_TYPE = StaticLattice

def get_exponential_env_config():
    # field parameters
    field_scale = 1.0
    exponential_base = 2e2
    field_center = [0.5, 0.0]

    # multibody process config
    multibody_config = {
        'animate': False,
        'jitter_force': 5e-4,
        'bounds': DEFAULT_BOUNDS}

    # static field config
    field_config = {
        'molecules': [DEFAULT_LIGAND_ID],
        'gradient': {
            'type': 'exponential',
            'molecules': {
                DEFAULT_LIGAND_ID: {
                    'center': field_center,
                    'scale': field_scale,
                    'base': exponential_base}}},
        'bounds': DEFAULT_BOUNDS}

    return {
        'multibody': multibody_config,
        'field': field_config}

def get_linear_env_config():
    # field parameters
    slope = 1.0
    base = 1e-1
    field_center = [0.5, 0.0]

    # multibody process config
    multibody_config = {
        'animate': False,
        'jitter_force': 5e-4,
        'bounds': DEFAULT_BOUNDS}

    # static field config
    field_config = {
        'molecules': [DEFAULT_LIGAND_ID],
        'gradient': {
            'type': 'linear',
            'molecules': {
                DEFAULT_LIGAND_ID: {
                    'base': base,
                    'center': field_center,
                    'slope': slope,
                }
            }
        },
        'bounds': DEFAULT_BOUNDS}

    return {
        'multibody': multibody_config,
        'field': field_config}

DEFAULT_ENVIRONMENT_CONFIG = {
    'type': DEFAULT_ENVIRONMENT_TYPE,
    'config': get_exponential_env_config()
}

DEFAULT_AGENT_CONFIG = {
    'ligand_id': DEFAULT_LIGAND_ID,
    'initial_ligand': DEFAULT_INITIAL_LIGAND,
    'external_path': ('global',),
    'agents_path': ('..', '..', 'agents'),
    'daughter_path': tuple(),
}

def set_agent_config(config={}):
    return deep_merge(dict(DEFAULT_AGENT_CONFIG), config)


# agent types
agents_library = {
    'motor': {
        'name': 'motor',
        'type': MotorActivityAgent,
        'config': DEFAULT_AGENT_CONFIG
    },
    'minimal': {
        'name': 'minimal',
        'type': ChemotaxisMinimal,
        'config': DEFAULT_AGENT_CONFIG
    },
    'variable': {
        'name': 'variable',
        'type': ChemotaxisVariableFlagella,
        'config': DEFAULT_AGENT_CONFIG
    },
    'expression': {
        'name': 'expression',
        'type': ChemotaxisExpressionFlagella,
        'config': DEFAULT_AGENT_CONFIG
    },
    'ode': {
        'name': 'ode_expression',
        'type': ChemotaxisODEExpressionFlagella,
        'config': DEFAULT_AGENT_CONFIG
    }
}

def make_agent_config(agent_specs):
    agent_type = agent_specs[0].value
    number = int(agent_specs[1].value)
    config = agents_library[agent_type]
    config['number'] = number
    return config


# preset experimental configurations
preset_experiments = {
    'minimal': {
        'agents_config': [
            {
                'number': 6,
                'name': 'minimal',
                'type': ChemotaxisMinimal,
                'config': DEFAULT_AGENT_CONFIG
            }
        ],
        'environment_config': DEFAULT_ENVIRONMENT_CONFIG,
        'simulation_settings': {
            'total_time': 30,
            'emit_step': 0.1,
        },
    },
    'ode': {
        'agents_config': [
            {
                'number': 1,
                'name': 'ode_expression',
                'type': ChemotaxisODEExpressionFlagella,
                'config': deep_merge(
                    dict(DEFAULT_AGENT_CONFIG),
                    {'growth_rate': 0.0005})  # fast growth
            }
        ],
        'environment_config': DEFAULT_ENVIRONMENT_CONFIG,
        'simulation_settings': {
            'total_time': 5000,
            'emit_step': 1.0,
        },
    },
    'master': {
        'agents_config': [
            {
                'number': 1,
                'name': 'master',
                'type': ChemotaxisMaster,
                'config': DEFAULT_AGENT_CONFIG
            }
        ],
        'environment_config': DEFAULT_ENVIRONMENT_CONFIG,
        'simulation_settings': {
            'total_time': 30,
            'emit_step': 0.1,
        },
    },
    'variable': {
        'agents_config': [
            {
                'number': 1,
                'name': '{}_flagella'.format(n_flagella),
                'type': ChemotaxisVariableFlagella,
                'config': set_agent_config({'n_flagella': n_flagella})
            }
            for n_flagella in [0, 3, 6, 9, 12]
        ],
        'environment_config': DEFAULT_ENVIRONMENT_CONFIG,
        'simulation_settings': {
            'total_time': 720,
            'emit_step': 0.1,
        },
    },
    'mixed': {
        'agents_config': [
            {
                'type': ChemotaxisMinimal,
                'name': 'motor_receptor',
                'number': 1,
                'config': DEFAULT_AGENT_CONFIG
            },
            {
                'type': MotorActivityAgent,
                'name': 'motor',
                'number': 1,
                'config': DEFAULT_AGENT_CONFIG
            }
        ],
        'environment_config': DEFAULT_ENVIRONMENT_CONFIG,
        'simulation_settings': {
            'total_time': 720,
            'emit_step': 0.1,
        },
    },
}


def run_chemotaxis_experiment(
    agents_config=None,
    environment_config=None,
    initial_state=None,
    simulation_settings=None,
    experiment_settings=None):

    if not initial_state:
        initial_state = {}
    if not experiment_settings:
        experiment_settings = {}

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

    initial_agent_body = agent_body_config({
        'bounds': DEFAULT_BOUNDS,
        'agent_ids': agent_ids,
        'location': DEFAULT_AGENT_LOCATION})
    initial_state.update(initial_agent_body)

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


# plotting
def plot_chemotaxis_experiment(
        data,
        field_config,
        out_dir,
        filename=''):

    # multigen agents plot
    plot_settings = {
        'agents_key': 'agents',
        'max_rows': 30,
        'skip_paths': [
            ('boundary', 'mass'),
            ('boundary', 'length'),
            ('boundary', 'width'),
            ('boundary', 'location'),
        ]}
    plot_agents_multigen(data, plot_settings, out_dir, 'agents')

    # trajectory and motility
    agents_timeseries = timeseries_from_data(data)
    field = make_field(field_config)
    trajectory_config = {
        'bounds': field_config['bounds'],
        'field': field,
        'rotate_90': True}

    plot_temporal_trajectory(copy.deepcopy(agents_timeseries), trajectory_config, out_dir, filename + 'temporal')
    plot_agent_trajectory(agents_timeseries, trajectory_config, out_dir, filename + 'trajectory')
    try:
        plot_motility(agents_timeseries, out_dir, filename + 'motility_analysis')
    except:
        print('plot_motility failed')


# parsing expression grammar for agents
def agent_type(): return RegExMatch(r'[a-zA-Z0-9.\-\_]+')
def number(): return RegExMatch(r'[0-9]+')
def specification(): return agent_type, number
def rule(): return OneOrMore(specification)
agent_parser = ParserPython(rule)
def parse_agents_string(agents_string):
    all_agents = agent_parser.parse(agents_string)
    agents_config = []
    for idx, agent_specs in enumerate(all_agents):
        agents_config.append(make_agent_config(agent_specs))
    return agents_config


def make_dir(out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

def add_arguments():
    parser = argparse.ArgumentParser(description='chemotaxis control')
    parser.add_argument(
        '--agents', '-a',
        type=str,
        nargs='+',
        default='"minimal 1"',
        help='A list of agent types and numbers in the format "agent_type1 number1 agent_type2 number2"')
    parser.add_argument(
        '--environment', '-v',
        type=str,
        default='exponential',
        help='the environment type ("linear" or "exponential")')
    parser.add_argument(
        '--time', '-t',
        type=int,
        default=10,
        help='total simulation time, in seconds')
    parser.add_argument(
        '--emit', '-m',
        type=int,
        default=1,
        help='emit interval, in seconds')
    parser.add_argument(
        '--experiment', '-e',
        type=str,
        default=None,
        help='preconfigured experiments')
    return parser.parse_args()


def run_chemotaxis_simulation():
    """
    Execute a chemotaxis simulation with any number of chemotactic agent types
    """
    out_dir = os.path.join(EXPERIMENT_OUT_DIR, 'chemotaxis')
    make_dir(out_dir)

    args = add_arguments()

    if args.experiment:
        # get a preset experiment
        # make a directory for this experiment
        experiment_name = str(args.experiment)
        control_out_dir = os.path.join(out_dir, experiment_name)
        make_dir(control_out_dir)

        experiment_config = preset_experiments[experiment_name]
        agents_config = experiment_config['agents_config']
        environment_config = experiment_config['environment_config']
        simulation_settings = experiment_config['simulation_settings']

    else:
        # make a directory for this experiment
        experiment_name = '_'.join(args.agents)
        control_out_dir = os.path.join(out_dir, experiment_name)
        make_dir(control_out_dir)

        # configure the agents
        agents_config = []
        if args.agents:
            agents_string = ' '.join(args.agents)
            agents_config = parse_agents_string(agents_string)

        # configure the environment
        if args.environment == 'linear':
            env_config = get_linear_env_config()
        else:
            env_config = get_exponential_env_config()
        environment_config = {
            'type': DEFAULT_ENVIRONMENT_TYPE,
            'config': env_config,
        }

        # configure the simulation
        total_time = args.time
        emit_step = args.emit
        simulation_settings = {
            'total_time': total_time,
            'emit_step': emit_step,
        }

    # simulate
    data = run_chemotaxis_experiment(
        agents_config=agents_config,
        environment_config=environment_config,
        simulation_settings=simulation_settings,
    )

    # plot
    field_config = environment_config['config']['field']
    plot_chemotaxis_experiment(data, field_config, control_out_dir)


if __name__ == '__main__':
    run_chemotaxis_simulation()
