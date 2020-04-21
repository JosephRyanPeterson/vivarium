from __future__ import absolute_import, division, print_function

import os

from vivarium.compartment.process import initialize_state
from vivarium.compartment.composition import (
    get_derivers,
    simulate_with_environment,
    plot_simulation_output,
    load_compartment)

# processes
from vivarium.processes.division import (
    Division,
    divide_condition)
from vivarium.processes.metabolism import (
    Metabolism,
    get_iAF1260b_config)
from vivarium.processes.convenience_kinetics import (
    ConvenienceKinetics,
    get_glc_lct_config)
from vivarium.processes.ode_expression import (
    ODE_expression,
    get_lacy_config)



# the composite compartment
def txp_mtb_ge_compartment(config):
    '''
    Transport-Metabolism-Gene expression compartment.

    TODO -- this should replace ode_expression composite, with glc-lcts-shifter as default
    '''

    ## Declare the processes.
    # Transport
    # load the kinetic parameters
    transport_config = config.get('transport', get_glc_lct_config())
    transport = ConvenienceKinetics(transport_config)
    target_fluxes = transport.kinetic_rate_laws.reaction_ids

    # Metabolism
    # get target fluxes from transport
    metabolism_config = config.get('metabolism', default_metabolism_config())
    metabolism_config.update({'constrained_reaction_ids': target_fluxes})
    metabolism = Metabolism(metabolism_config)

    # Gene expression
    gene_expression_config = config.get('expression', get_lacy_config())
    gene_expression = ODE_expression(gene_expression_config)

    # Division
    # get initial volume from metabolism
    division_config = config.get('division', {})
    # division_config.update({'initial_state': metabolism.initial_state})  # TODO -- metabolism no longer has an initial volume
    division = Division(division_config)

    # Place processes in layers
    processes = [
        {'transport': transport},
        {'metabolism': metabolism,
         'expression': gene_expression},
        {'division': division}]

    # Make the topology
    # for each process, map process ports to store ids
    topology = {
        'transport': {
            'internal': 'cytoplasm',
            'external': 'environment',
            'exchange': 'null',  # metabolism's exchange is used
            'fluxes': 'flux_bounds',
            'global': 'global'},
        'metabolism': {
            'internal': 'cytoplasm',
            'external': 'environment',
            'reactions': 'reactions',
            'exchange': 'exchange',
            'flux_bounds': 'flux_bounds',
            'global': 'global'},
        'expression': {
            'counts': 'cytoplasm_counts',
            'internal': 'cytoplasm',
            'external': 'environment'},
        'division': {
            'global': 'global'}
    }

    return {
        'processes': processes,
        'topology': topology}




def compose_txb_mtb_ge(config):
    """
    A composite with kinetic transport, metabolism, and gene expression
    """

    compartment = txp_mtb_ge_compartment(config)
    processes = compartment['processes']
    topology = compartment['topology']

    # add derivers
    derivers = get_derivers(processes, topology)
    deriver_processes = derivers['deriver_processes']
    all_processes = processes + derivers['deriver_processes']
    topology.update(derivers['deriver_topology'])  # add derivers to the topology

    # initialize the states
    states = initialize_state(
        all_processes,
        topology,
        config.get('initial_state', {}))

    options = {
        'name': config.get('name', 'master_composite'),
        'environment_port': 'environment',
        'exchange_port': 'exchange',
        'topology': topology,
        'initial_time': config.get('initial_time', 0.0),
        'divide_condition': divide_condition}

    return {
        'processes': processes,
        'derivers': deriver_processes,
        'states': states,
        'options': options}



# toy functions/ defaults
def default_metabolism_config():
    config = get_iAF1260b_config()

    # set flux bond tolerance for reactions in ode_expression's lacy_config
    metabolism_config = {
        'moma': False,
        'tolerance': {
            'EX_glc__D_e': [1.05, 1.0],
            'EX_lcts_e': [1.05, 1.0]}}

    config.update(metabolism_config)

    return config


# simulate
def test_txb_mtb_ge(time=10):
    compartment = load_compartment(compose_txb_mtb_ge)
    options = compartment.configuration
    settings = {
        'environment_port': options['environment_port'],
        'exchange_port': options['exchange_port'],
        'environment_volume': 1e-5,  # L
        'timeline': [(time, {})]}
    return simulate_with_environment(compartment, settings)



if __name__ == '__main__':
    out_dir = os.path.join('out', 'tests', 'txb_mtb_ge_composite')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    timeseries = test_txb_mtb_ge(100) # 2520 sec (42 min) is the expected doubling time in minimal media
    plot_settings = {
        'max_rows': 20,
        'remove_zeros': True,
        'overlay': {
            'reactions': 'flux_bounds'},
        'skip_ports': [
            'prior_state', 'null'],
        'show_state': [
            ('reactions', 'EX_glc__D_e'),
            ('reactions', 'EX_lcts_e')]}

    plot_simulation_output(timeseries, plot_settings, out_dir)
