from __future__ import absolute_import, division, print_function

import os
import sys
import argparse

from arpeggio import (
    RegExMatch,
    ParserPython,
    OneOrMore,
)

from vivarium.core.experiment import timestamp
from vivarium.core.composition import (
    agent_environment_experiment,
    simulate_experiment,
    plot_agents_multigen,
    EXPERIMENT_OUT_DIR,
)
from vivarium.analysis.analyze import plot

# plot settings
def get_plot_settings(
        fields=[],
        tags=[]
):
    return {
        'plot_types': {
            'agents': {},
            'snapshots': {
                'fields': fields
            },
            'tags': {
                'tag_ids': tags
            }
        }
    }

def plot_workflow_output(
        data,
        plot_settings={},
        out_dir='out',
):
    environment_config = plot_settings['environment_config']
    agent_type = plot_settings.get('agent_type', 'agent')
    plot_types = plot_settings['plot_types']

    # extract data
    multibody_config = environment_config['config']['multibody']
    agents = {time: time_data['agents'] for time, time_data in data.items()}
    fields = {time: time_data['fields'] for time, time_data in data.items()}

    # pass to plots
    if 'agents' in plot_types:
        plot_settings = {
            'agents_key': 'agents'}
        plot_agents_multigen(data, plot_settings, out_dir, agent_type)

    if 'snapshots' in plot_types:
        field_ids = plot_types['snapshots']['fields']
        plot_fields = {
            time: {
                field_id: field_instance[field_id]
                for field_id in field_ids}
            for time, field_instance in fields.items()}
        data = {
            'agents': agents,
            'fields': plot_fields,
            'config': multibody_config}
        plot_config = {
            'out_dir': out_dir,
            'filename': agent_type + '_snapshots'}
        plot_snapshots(data, plot_config)

    if 'tags' in plot_types:
        tags_ids = plot_types['tags']['tag_ids']
        data = {
            'agents': agents,
            'config': multibody_config}
        plot_config = {
            'out_dir': out_dir,
            'filename': agent_type + '_tags',
            'tagged_molecules': tags_ids,
        }
        plot_tags(data, plot_config)

# Experiment run function
def run_agent_environment_experiment(
        agents_config=None,
        environment_config=None,
        initial_state=None,
        initial_agent_state=None,
        simulation_settings=None,
        experiment_settings=None
):
    if experiment_settings is None:
        experiment_settings = {}
    if initial_state is None:
        initial_state = {}
    if initial_agent_state is None:
        initial_agent_state = {}

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
        agents_config=agents_config,
        environment_config=environment_config,
        initial_state=initial_state,
        initial_agent_state=initial_agent_state,
        settings=experiment_settings,
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

class Workflow():

    def __init__(
        self,
        name=None,
        agents_library={},
        environment_library={},
        experiment_library={},
    ):
        if name is None:
            name = timestamp()

        self.agents_library = agents_library
        self.environment_library = environment_library
        self.experiment_library = experiment_library

        self.args = self.add_arguments()

        # TODO experiment settings

        # TODO plot settings

        # TODO save out_dir
        out_dir = os.path.join(EXPERIMENT_OUT_DIR, name)
        make_dir(out_dir)
        import ipdb; ipdb.set_trace()


    def add_arguments(self):
        parser = argparse.ArgumentParser(
            description='command line control of experiments'
        )
        parser.add_argument(
            '--agents', '-a',
            type=str,
            nargs='+',
            default=None,
            help='A list of agent types and numbers in the format "agent_type1 number1 agent_type2 number2"'
        )
        parser.add_argument(
            '--environment', '-v',
            type=str,
            default=None,
            help='the environment type'
        )
        parser.add_argument(
            '--time', '-t',
            type=int,
            default=100,
            help='total simulation time, in seconds'
        )
        parser.add_argument(
            '--emit', '-m',
            type=int,
            default=1,
            help='emit interval, in seconds'
        )
        parser.add_argument(
            '--experiment', '-e',
            type=str,
            default=None,
            help='preconfigured experiments'
        )

        return parser.parse_args()

    def execute(self):

        if self.args.experiment:
            import ipdb; ipdb.set_trace()
            # get a preset experiment
            # make a directory for this experiment
            experiment_name = str(args.experiment)
            control_out_dir = os.path.join(out_dir, experiment_name)
            make_dir(control_out_dir)

            experiment_config = preset_experiments[experiment_name]
            agents_config = experiment_config['agents_config']
            environment_config = experiment_config['environment_config']
            simulation_settings = experiment_config['simulation_settings']

        # agent configuration
        agent_config = agents_library[agent_type]
        agent_config['number'] = n_agents
        agents_config = [
            agent_config,
        ]

        # environment configuration
        environment_config = environments_library[environment_type]

        # simulate
        data = run_agent_environment_experiment(
            agents_config=agents_config,
            environment_config=environment_config,
            initial_state=initial_state,
            initial_agent_state=initial_agent_state,
            simulation_settings=simulation_settings,
        )

        plot_settings['environment_config'] = environment_config
        plot_settings['agent_type'] = agent_type
        plot_experiment_output(
            data,
            plot_settings,
            out_dir,
        )

        # TODO -- use plot from analysis/analyze.py