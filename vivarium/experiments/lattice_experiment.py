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
from vivarium.plots.multibody_physics import (
    plot_snapshots,
    plot_tags
)

# processes
from vivarium.processes.metabolism import (
    Metabolism,
    get_iAF1260b_config,
)

# compartments
from vivarium.compartments.lattice import Lattice
from vivarium.compartments.growth_division import GrowthDivision
from vivarium.compartments.growth_division_minimal import GrowthDivisionMinimal
from vivarium.compartments.transport_metabolism import TransportMetabolism
from vivarium.compartments.flagella_expression import (
    FlagellaExpressionMetabolism,
    get_flagella_initial_state,
)



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
    'flagella_metabolism': {
        'name': 'flagella_metabolism',
        'type': FlagellaExpressionMetabolism,
        'config': {
            'agents_path': ('..', '..', 'agents'),
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


# environment config
def get_lattice_config(
    bounds=[20, 20],
    n_bins=[10, 10],
    jitter_force=1e-4,
    depth=3000.0,
    diffusion=1e-2,
    molecules=['glc__D_e', 'lcts_e'],
    gradient={},
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
            'gradient': gradient,
        }
    }
    return environment_config

def get_iAF1260b_environment():
    # get external state from iAF1260b metabolism
    config = get_iAF1260b_config()
    metabolism = Metabolism(config)
    molecules = metabolism.initial_state['external']
    gradient = {
        'type': 'uniform',
        'molecules': molecules}
    return get_lattice_config(
        molecules=list(molecules.keys()),
        gradient=gradient,
    )

environments_library = {
    'glc_lcts': {
        'type': DEFAULT_ENVIRONMENT_TYPE,
        'config': get_lattice_config(),
    },
    'iAF1260b': {
        'type': DEFAULT_ENVIRONMENT_TYPE,
        'config': get_iAF1260b_environment(),
    },
}

# simulation settings
def get_simulation_settings(
        total_time=4000,
        emit_step=10,
        emitter='timeseries',
        return_raw_data=True,
):
    return {
        'total_time': total_time,
        'emit_step': emit_step,
        'emitter': emitter,
        'return_raw_data': return_raw_data
    }


# plot settings
def get_plot_settings(
        skip_paths=[],
        fields=[],
        tags=[]
):
    return {
        'plot_types': {
            'agents': {
                'skip_paths': skip_paths,
                'remove_zeros': True,
            },
            'snapshots': {
                'fields': fields
            },
            'tags': {
                'tag_ids': tags
            },
        }
    }

def plot_experiment_output(
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
        plot_settings = plot_types['agents']
        plot_settings['agents_key'] = 'agents'
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
def run_lattice_experiment(
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


def run_workflow(
        agent_type='growth_division_minimal',
        n_agents=1,
        environment_type='glc_lcts',
        initial_state={},
        initial_agent_state={},
        out_dir='out',
        simulation_settings=get_simulation_settings(),
        plot_settings=get_plot_settings()
):
    # agent configuration
    agent_config = agents_library[agent_type]
    agent_config['number'] = n_agents
    agents_config = [
        agent_config,
    ]

    # environment configuration
    environment_config = environments_library[environment_type]

    # simulate
    data = run_lattice_experiment(
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


def test_growth_division_experiment():
    '''test growth_division_minimal agent in lattice experiment'''
    growth_rate = 0.005  # fast!
    total_time = 150

    # get minimal agent config and set growth rate
    agent_config = agents_library['growth_division_minimal']
    agent_config['config']['growth_rate'] = growth_rate
    agent_config['number'] = 1
    agents_config = [agent_config]

    # get environment config
    environment_config = environments_library['glc_lcts']

    # simulate
    simulation_settings = get_simulation_settings(
        total_time=total_time,
        return_raw_data=True)

    data = run_lattice_experiment(
        agents_config=agents_config,
        environment_config=environment_config,
        simulation_settings=simulation_settings)

    # assert division
    time = list(data.keys())
    initial_agents = len(data[time[0]]['agents'])
    final_agents = len(data[time[-1]]['agents'])
    assert final_agents > initial_agents


def make_dir(out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

def main():
    out_dir = os.path.join(EXPERIMENT_OUT_DIR, NAME)
    make_dir(out_dir)

    parser = argparse.ArgumentParser(description='lattice_experiment')
    parser.add_argument('--growth_division', '-g', action='store_true', default=False)
    parser.add_argument('--growth_division_minimal', '-m', action='store_true', default=False)
    parser.add_argument('--flagella_metabolism', '-f', action='store_true', default=False)
    parser.add_argument('--transport_metabolism', '-t', action='store_true', default=False)
    args = parser.parse_args()
    no_args = (len(sys.argv) == 1)

    if args.growth_division_minimal or no_args:
        minimal_out_dir = os.path.join(out_dir, 'minimal')
        make_dir(minimal_out_dir)
        run_workflow(
            agent_type='growth_division_minimal',
            out_dir=minimal_out_dir)

    elif args.growth_division:
        gd_out_dir = os.path.join(out_dir, 'growth_division')
        make_dir(gd_out_dir)
        run_workflow(
            agent_type='growth_division',
            simulation_settings=get_simulation_settings(
                total_time=8000
            ),
            plot_settings=get_plot_settings(
                skip_paths=[
                    ('boundary', 'location')
                ],
                fields=[
                    'glc__D_e',
                    'lcts_e',
                ],
                tags=[
                    ('internal', 'protein1'),
                    ('internal', 'protein2'),
                    ('internal', 'protein3'),
                ]
            ),
            out_dir=gd_out_dir)

    elif args.flagella_metabolism:
        txp_mtb_out_dir = os.path.join(out_dir, 'flagella_metabolism')
        make_dir(txp_mtb_out_dir)
        run_workflow(
            agent_type='flagella_metabolism',
            environment_type='iAF1260b',
            initial_agent_state=get_flagella_initial_state(),
            simulation_settings=get_simulation_settings(
                emit_step=60,
                emitter='database',
                total_time=6000,
            ),
            plot_settings=get_plot_settings(
                skip_paths=[
                    ('boundary', 'external')
                ],
                fields=[
                    'glc__D_e',
                ],
                tags=[
                    ('proteins', 'flagella'),
                ]
            ),
            out_dir=txp_mtb_out_dir)

    elif args.transport_metabolism:
        txp_mtb_out_dir = os.path.join(out_dir, 'transport_metabolism')
        make_dir(txp_mtb_out_dir)
        run_workflow(
            agent_type='transport_metabolism',
            out_dir=txp_mtb_out_dir)


if __name__ == '__main__':
    main()
