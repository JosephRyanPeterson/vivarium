from __future__ import absolute_import, division, print_function

import os

from vivarium.compartments.lattice import Lattice
from vivarium.core.composition import (
    EXPERIMENT_OUT_DIR,
    REFERENCE_DATA_DIR,
    make_agents,
    assert_timeseries_close,
    load_timeseries,
    simulate_experiment,
    plot_agents_multigen,
)
from vivarium.core.emitter import path_timeseries_from_data
from vivarium.core.experiment import Experiment
from vivarium.experiments.lattice_experiment import (
    get_gd_minimal_config,
    get_lattice_config,
)
from vivarium.plots.multibody_physics import plot_snapshots
from vivarium.library.timeseries import (
    process_path_timeseries_for_csv,
    save_flat_timeseries,
)
from vivarium.library.units import units


NAME = 'colony_metrics'
OUT_DIR = os.path.join(EXPERIMENT_OUT_DIR, NAME)


def colony_metrics_experiment(config):
    # configure the experiment
    n_agents = config.get('n_agents')
    emitter = config.get('emitter', {'type': 'timeseries'})

    # make lattice environment
    environment = Lattice(config.get('environment', {}))
    network = environment.generate()
    processes = network['processes']
    topology = network['topology']

    # add the agents
    agent_ids = [str(agent_id) for agent_id in range(n_agents)]
    agent_config = config['agent']
    agent_compartment = agent_config['compartment']
    compartment_config = agent_config['config']
    agent = agent_compartment(compartment_config)
    agents = make_agents(agent_ids, agent, {})
    processes['agents'] = agents['processes']
    topology['agents'] = agents['topology']

    return Experiment({
        'processes': processes,
        'topology': topology,
        'emitter': emitter,
        'initial_state': config.get('initial_state', {}),
    })


def get_lattice_with_metrics_config():
    config = get_lattice_config()
    colony_metrics_config = {
        'colony_mass_deriver': {},
        'colony_cell_volume_deriver': {
            'metric_port_schema': {
                '_default': 0.0 * units.fL,
            }
        },
    }
    config['environment'].update(colony_metrics_config)
    return config


def run_experiment(agent_config=None):
    if agent_config is None:
        agent_config = get_gd_minimal_config()
        agent_config['config']['growth_rate_noise'] = 0
    n_agents = 2

    experiment_config = get_lattice_with_metrics_config()
    experiment_config['n_agents'] = n_agents
    experiment_config['agent'] = agent_config
    experiment = colony_metrics_experiment(experiment_config)

    # simulate
    settings = {
        'timestep': 1,
        'total_time': 200,
        'return_raw_data': True,
    }
    return simulate_experiment(experiment, settings), experiment_config


def test_experiment():
    data, _ = run_experiment()
    path_ts = path_timeseries_from_data(data)
    filtered = {
        path: timeseries
        for path, timeseries in path_ts.items()
        # Angles are computed randomly by multibody physics
        if path[-1] != 'angle'
    }
    processed_for_csv = process_path_timeseries_for_csv(filtered)
    save_flat_timeseries(
        processed_for_csv,
        OUT_DIR,
        'test_output.csv'
    )
    test_output = load_timeseries(os.path.join(OUT_DIR, 'test_output.csv'))
    expected = load_timeseries(
        os.path.join(REFERENCE_DATA_DIR, NAME + '.csv'))
    assert_timeseries_close(test_output, expected)


def main():
    if not os.path.exists(OUT_DIR):
        os.makedirs(OUT_DIR)

    data, experiment_config = run_experiment()

    # extract data
    multibody_config = experiment_config['environment']['multibody']
    agents = {time: time_data['agents'] for time, time_data in data.items()}
    fields = {time: time_data['fields'] for time, time_data in data.items()}

    # agents plot
    plot_settings = {
        'agents_key': 'agents'
    }
    plot_agents_multigen(data, plot_settings, OUT_DIR, 'agents')

    # snapshot plot
    data = {
        'agents': agents,
        'fields': fields,
        'config': multibody_config,
    }
    plot_config = {
        'out_dir': OUT_DIR,
        'filename': 'agents_snapshots',
    }
    plot_snapshots(data, plot_config)


if __name__ == '__main__':
    test_experiment()
    main()
