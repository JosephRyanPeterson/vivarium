from __future__ import absolute_import, division, print_function

import os
import argparse
import random

from vivarium.core.experiment import Experiment
from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    plot_compartment_topology,
    plot_simulation_output,
    COMPARTMENT_OUT_DIR,
)
from vivarium.data.nucleotides import nucleotides
from vivarium.data.amino_acids import amino_acids
from vivarium.data.chromosomes.flagella_chromosome import FlagellaChromosome
from vivarium.plots.gene_expression import plot_timeseries_heatmaps
from vivarium.states.chromosome import Chromosome, rna_bases, sequence_monomers
from vivarium.processes.transcription import UNBOUND_RNAP_KEY
from vivarium.processes.translation import UNBOUND_RIBOSOME_KEY
from vivarium.compartments.gene_expression import (
    GeneExpression,
    plot_gene_expression_output,
    gene_network_plot,
)
from vivarium.parameters.parameters import (
    parameter_scan,
    get_parameters_logspace,
    plot_scan_results,
)


NAME = 'flagella_gene_expression'


def get_flagella_expression_config(config):
    flagella_data = FlagellaChromosome(config)
    chromosome_config = flagella_data.chromosome_config
    sequences = flagella_data.chromosome.product_sequences()

    return {

        'transcription': {

            'sequence': chromosome_config['sequence'],
            'templates': chromosome_config['promoters'],
            'genes': chromosome_config['genes'],
            'transcription_factors': flagella_data.transcription_factors,
            'promoter_affinities': flagella_data.promoter_affinities,
            'polymerase_occlusion': 30,
            'elongation_rate': 50},

        'translation': {

            'sequences': flagella_data.protein_sequences,
            'templates': flagella_data.transcript_templates,
            'concentration_keys': ['CRP', 'flhDC', 'fliA'],
            'transcript_affinities': flagella_data.transcript_affinities,
            'elongation_rate': 22,
            'polymerase_occlusion': 50},

        'degradation': {

            'sequences': sequences,
            'catalytic_rates': {
                'endoRNAse': 0.01},
            'michaelis_constants': {
                'transcripts': {
                    'endoRNAse': {
                        transcript: 1e-23
                        for transcript in chromosome_config['genes'].keys()}}}},

        'complexation': {
            'monomer_ids': flagella_data.complexation_monomer_ids,
            'complex_ids': flagella_data.complexation_complex_ids,
            'stoichiometry': flagella_data.complexation_stoichiometry,
            'rates': flagella_data.complexation_rates},
    }


def get_flagella_initial_state(ports={}):
    flagella_data = FlagellaChromosome()
    chromosome_config = flagella_data.chromosome_config

    molecules = {}
    for nucleotide in nucleotides.values():
        molecules[nucleotide] = 5000000
    for amino_acid in amino_acids.values():
        molecules[amino_acid] = 1000000

    return {
        ports.get(
            'molecules',
            'molecules'): molecules,
        ports.get(
            'transcripts',
            'transcripts'): {
                gene: 0
                for gene in chromosome_config['genes'].keys()
        },
        ports.get(
            'proteins',
            'proteins'): {
                'CpxR': 10,
                'CRP': 10,
                'Fnr': 10,
                'endoRNAse': 1,
                'flagella': 8,
                UNBOUND_RIBOSOME_KEY: 200,  # e. coli has ~ 20000 ribosomes
                UNBOUND_RNAP_KEY: 200
            }
    }


def get_flagella_compartment(config):
    flagella_expression_config = get_flagella_expression_config(config)
    return GeneExpression(flagella_expression_config)


def make_compartment_topology(out_dir='out'):
    # load the compartment
    flagella_compartment = get_flagella_compartment({})

    settings = {'show_ports': True}
    plot_compartment_topology(
        flagella_compartment,
        settings,
        out_dir)


def make_flagella_network(out_dir='out'):
    # load the compartment
    flagella_compartment = get_flagella_compartment({})

    # make expression network plot
    flagella_expression_processes = flagella_compartment.generate_processes({})
    operons = flagella_expression_processes['transcription'].genes
    promoters = flagella_expression_processes['transcription'].templates
    complexes = flagella_expression_processes['complexation'].stoichiometry
    data = {
        'operons': operons,
        'templates': promoters,
        'complexes': complexes}
    gene_network_plot(data, out_dir)


def run_flagella_expression(out_dir='out'):
    # load the compartment
    flagella_compartment = get_flagella_compartment({})

    # get flagella data
    flagella_data = FlagellaChromosome()

    # run simulation
    initial_state = get_flagella_initial_state()
    settings = {
        # a cell cycle of 2520 sec is expected to express 8 flagella.
        # 2 flagella expected in ~630 seconds.
        'total_time': 760,
        'verbose': True,
        'initial_state': initial_state}
    timeseries = simulate_compartment_in_experiment(flagella_compartment, settings)

    plot_config = {
        'name': 'flagella_expression',
        'ports': {
            'transcripts': 'transcripts',
            'proteins': 'proteins',
            'molecules': 'molecules'}}

    plot_gene_expression_output(
        timeseries,
        plot_config,
        out_dir)

    # just-in-time figure
    plot_config2 = plot_config.copy()
    plot_config2.update({
        'name': 'flagella',
        'plot_ports': {
            'transcripts': list(flagella_data.chromosome_config['genes'].keys()),
            'proteins': flagella_data.complexation_monomer_ids + flagella_data.complexation_complex_ids,
            'molecules': list(nucleotides.values()) + list(amino_acids.values())}})

    plot_timeseries_heatmaps(
        timeseries,
        plot_config2,
        out_dir)

    # make a basic sim output
    plot_settings = {
        'max_rows': 30,
        'remove_zeros': False,
        'skip_ports': ['chromosome', 'ribosomes']}
    plot_simulation_output(
        timeseries,
        plot_settings,
        out_dir)


def test_flagella_expression():
    flagella_compartment = get_flagella_compartment({})

    # initial state for flagella complexation
    initial_state = get_flagella_initial_state()
    initial_state['proteins'].update({
        'Ribosome': 400,  # plenty of ribosomes
        'flagella': 0,
        # required flagella components
        'flagellar export apparatus': 1,
        'flagellar motor': 1,
        'fliC': 1,
        'flgL': 1,
        'flgK': 1,
        'fliD': 5,
        'flgE': 120
    })

    # run simulation
    random.seed(0)  # set seed because process is stochastic
    settings = {
        'total_time': 100,
        'emit_step': 10,
        'initial_state': initial_state}
    timeseries = simulate_compartment_in_experiment(flagella_compartment, settings)

    print(timeseries['proteins']['flagella'])
    final_flagella = timeseries['proteins']['flagella'][-1]
    # this should have been long enough for flagellar complexation to occur
    assert final_flagella == 1


def scan_flagella_expression_parameters():
    compartment = get_flagella_compartment({})
    flagella_data = FlagellaChromosome()

    # conditions
    conditions = {}

    # parameters
    scan_params = {}
    # # add promoter affinities
    # for promoter in flagella_data.chromosome_config['promoters'].keys():
    #     scan_params[('promoter_affinities', promoter)] = get_parameters_logspace(1e-3, 1e0, 4)

    # scan minimum transcript affinity -- other affinities are a scaled factor of this value
    scan_params[('min_tr_affinity', flagella_data.min_tr_affinity)] = get_parameters_logspace(1e-2, 1e2, 6)

    # # add transcription factor thresholds
    # for threshold in flagella_data.factor_thresholds.keys():
    #     scan_params[('thresholds', threshold)] = get_parameters_logspace(1e-7, 1e-4, 4)

    # metrics
    metrics = [
        ('proteins', monomer)
        for monomer in flagella_data.complexation_monomer_ids] + [
        ('proteins', complex)
        for complex in flagella_data.complexation_complex_ids]

    print('number of parameters: {}'.format(len(scan_params)))  # TODO -- get this down to 10

    # run the scan
    scan_config = {
        'compartment': compartment,
        'scan_parameters': scan_params,
        'conditions': conditions,
        'metrics': metrics,
        'settings': {'total_time': 480}}
    results = parameter_scan(scan_config)

    return results


if __name__ == '__main__':
    out_dir = os.path.join(COMPARTMENT_OUT_DIR, NAME)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # run scan with python vivarium/compartments/flagella_expression.py --scan
    parser = argparse.ArgumentParser(description='flagella expression')
    parser.add_argument('--scan', '-s', action='store_true', default=False,)
    parser.add_argument('--network', '-n', action='store_true', default=False,)
    parser.add_argument('--topology', '-t', action='store_true', default=False,)
    args = parser.parse_args()

    if args.scan:
        results = scan_flagella_expression_parameters()
        plot_scan_results(results, out_dir)
    elif args.network:
        make_flagella_network(out_dir)
    elif args.topology:
        make_compartment_topology(out_dir)
    else:
        run_flagella_expression(out_dir)

