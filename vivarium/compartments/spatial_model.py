from __future__ import absolute_import, division, print_function

import os
import copy

from vivarium.library.units import units
from vivarium.core.process import Generator
from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    plot_agents_multigen,
    COMPARTMENT_OUT_DIR,
)

# processes
from vivarium.processes.growth_protein import GrowthProtein
from vivarium.processes.meta_division import MetaDivision
from vivarium.processes.diffusion_network import DiffusionNetwork

from vivarium.library.dict_utils import deep_merge


NAME = 'spatial_model'

def get_spatial_config():
    locations = [
        # 'outer_membrane',
        'periplasm',
        # 'inner_membrane',
        'front_cytoplasm',
        'back_cytoplasm',
        'center_cytoplasm',
        'nucleoid',
    ]

    # membranes = [
    #     'inner_membrane',
    #     'outer_membrane'
    # ]

    edges = [
        ('front_cytoplasm', 'center_cytoplasm'),
        ('back_cytoplasm', 'center_cytoplasm'),
        ('periplasm', 'front_cytoplasm'),
        ('periplasm', 'center_cytoplasm'),
        ('periplasm', 'back_cytoplasm'),
        ('nucleoid', 'front_cytoplasm'),
        ('nucleoid', 'center_cytoplasm'),
        ('nucleoid', 'back_cytoplasm'),
    ]

    membrane_edges = [
        ('periplasm', 'front_cytoplasm'),
        ('periplasm', 'center_cytoplasm'),
        ('periplasm', 'back_cytoplasm'),
    ]

    initial_state = {
        'membrane_composition': {
            'porin': 5},
        'concentrations': {
            'periplasm': {
                'glc': 20.0},
            'front_cytoplasm': {
                'glc': 20.0},
            'center_cytoplasm': {
                'glc': 20.0},
            'back_cytoplasm': {
                'glc': 20.0},
            'nucleoid': {
                'glc': 20.0},
        }}

    return {
        'locations': locations,
        'network': {
            'initial_state': initial_state,
            'molecules': ['glc'],
            'network': {
                'type': 'standard',
                'locations': locations,
                'edges': edges,
                'membrane_edges': membrane_edges,
            },
            'channels':{
                'porin': 5e-2  # diffusion rate through porin
            },
            'diffusion': 1e-1
        }
    }


class SpatialModel(Generator):

    defaults = {
        'growth_rate': 0.006,  # very fast growth
        'boundary_path': ('boundary',),
        'agents_path': ('..', '..', 'agents',),
        'daughter_path': tuple()}

    def __init__(self, config):
        self.config = config
        for key, value in self.defaults.items():
            if key not in self.config:
                self.config[key] = value

    def generate_processes(self, config):
        growth_config = config.get('growth', {})
        growth_rate = config['growth_rate']
        growth_config['growth_rate'] = growth_rate
        growth_config['divide_condition'] = False

        processes = {}
        for location in config['locations']:
            growth_process_name = location + '_growth'
            processes[growth_process_name] = GrowthProtein(growth_config)

        # connect all locations with diffusion network
        processes['diffusion_network'] = DiffusionNetwork(config['network'])

        # division config
        daughter_path = config['daughter_path']
        agent_id = config['agent_id']
        division_config = dict(
            config.get('division', {}),
            daughter_path=daughter_path,
            agent_id=agent_id,
            compartment=self)
        processes['division'] = MetaDivision(division_config)

        return processes

    def generate_topology(self, config):
        boundary_path = config['boundary_path']
        agents_path = config['agents_path']

        import ipdb;
        ipdb.set_trace()
        # TODO -- connect up diffusion network

        topology = {
            location + '_growth': {
                'internal': (location,),
                'global': boundary_path
            } for location in config['locations']}

        topology['division'] = {
                'global': boundary_path,
                'cells': agents_path}

        return topology



if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    agent_id = '0'
    parameters = get_spatial_config()
    parameters['agent_id'] = agent_id
    compartment = SpatialModel(parameters)

    # settings for simulation and plot
    settings = {
        'outer_path': ('agents', agent_id),
        'return_raw_data': True,
        'timestep': 1,
        'total_time': 600}
    output_data = simulate_compartment_in_experiment(compartment, settings)

    plot_settings = {}
    plot_agents_multigen(output_data, plot_settings, out_dir)