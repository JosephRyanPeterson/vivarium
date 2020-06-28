from __future__ import absolute_import, division, print_function

import os
import sys
import argparse

from arpeggio import (
    RegExMatch,
    ParserPython,
    OneOrMore,
)

from vivarium.core.composition import (
    agent_environment_experiment,
    make_agents,
    simulate_experiment,
    plot_agents_multigen,
    process_in_compartment,
    EXPERIMENT_OUT_DIR,
)

from vivarium.experiments.chemotaxis import (
    run_chemotaxis_experiment,
    DEFAULT_AGENT_CONFIG,
    DEFAULT_ENVIRONMENT_TYPE,
    get_exponential_env_config,
    get_linear_env_config,
    plot_chemotaxis_experiment,
)

# compartments
from vivarium.compartments.static_lattice import StaticLattice
from vivarium.compartments.chemotaxis_minimal import ChemotaxisMinimal
from vivarium.compartments.chemotaxis_master import ChemotaxisMaster
from vivarium.compartments.chemotaxis_flagella import (
    ChemotaxisVariableFlagella,
    ChemotaxisExpressionFlagella,
)

# processes
from vivarium.processes.Vladimirov2008_motor import MotorActivity

# make an agent from a lone MotorActivity process
MotorActivityAgent = process_in_compartment(
    MotorActivity,
    paths={
        'external': ('boundary',),
        'internal': ('cell',)
    })


# parsing expression grammar for agents
def agent_type(): return RegExMatch(r'[a-zA-Z0-9.\-\_]+')
def number(): return RegExMatch(r'[0-9]+')
def specification(): return agent_type, number
def rule(): return OneOrMore(specification)

def make_agent(agent_specs):
    agent_type = agent_specs[0].value
    number = int(agent_specs[1].value)

    if agent_type == 'motor':
        agents_config = {
                'number': number,
                'name': 'motor',
                'type': MotorActivityAgent,
                'config': DEFAULT_AGENT_CONFIG}

    elif agent_type == 'minimal':
        agents_config = {
            'number': number,
            'name': 'minimal',
            'type': ChemotaxisMinimal,
            'config': DEFAULT_AGENT_CONFIG}

    elif agent_type == 'variable':
        agents_config = {
            'number': number,
            'name': 'variable',
            'type': ChemotaxisVariableFlagella,
            'config': DEFAULT_AGENT_CONFIG}

    elif agent_type == 'expression':
        agents_config = {
            'number': number,
            'name': 'expression',
            'type': ChemotaxisExpressionFlagella,
            'config': DEFAULT_AGENT_CONFIG}

    return agents_config

agent_parser = ParserPython(rule)
def parse_agents(agents_string):
    all_agents = agent_parser.parse(agents_string)
    agents_config = []
    for idx, agent_specs in enumerate(all_agents):
        agents_config.append(make_agent(agent_specs))
    return agents_config


def make_dir(out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)


def execute():
    out_dir = os.path.join(EXPERIMENT_OUT_DIR, 'chemotaxis')
    make_dir(out_dir)

    parser = argparse.ArgumentParser(description='chemotaxis control')
    parser.add_argument(
        '--agents', '-a',
        type=str,
        nargs='+',
        default='',
        help='A list of agent types and numbers in the format "agent_type1 number1 agent_type2 number2"')
    parser.add_argument(
        '--environment', '-e',
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
    args = parser.parse_args()


    # configure the agents
    agents_config = []
    if args.agents:
        agents_string = ' '.join(args.agents)
        agents_config = parse_agents(agents_string)

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
    plot_chemotaxis_experiment(data, field_config, out_dir, 'control_')


if __name__ == '__main__':
    execute()
