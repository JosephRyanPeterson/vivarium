from __future__ import absolute_import, division, print_function

import os
import sys
import argparse

from vivarium.core.workflow import Workflow
from vivarium.core.experiment import Experiment
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
agent_library = {
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

environment_library = {
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
        return_raw_data=True,
):
    return {
        'total_time': total_time,
        'emit_step': emit_step,
        'return_raw_data': return_raw_data
    }



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
                emit_step=20,
                total_time=500,
            ),
            plot_settings=get_plot_settings(
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



experiment_library = {
    'flagella_metabolism': {
            'agent_type': 'flagella_metabolism',
            'environment_type': 'iAF1260b',
            'initial_agent_state': get_flagella_initial_state(),
            'simulation_settings': {
                'emit_step': 20,
                'total_time': 500,
            },
            'plot_settings': {
                'fields': ['glc__D_e'],
                'tags': [['proteins', 'flagella']],
            },
        }
    }

def workflow():
    workflow = Workflow(
        name=NAME,
        agent_library=agent_library,
        environment_library=environment_library,
        experiment_library=experiment_library,
        )

    workflow.execute()


if __name__ == '__main__':
    # main()
    workflow()