from __future__ import absolute_import, division, print_function

import os
import copy
import argparse
import random
import uuid
import pytest

from vivarium.core.process import Generator
from vivarium.core.experiment import Experiment
from vivarium.core.composition import (
    simulate_compartment_in_experiment,
    plot_compartment_topology,
    plot_simulation_output,
    save_timeseries,
    COMPARTMENT_OUT_DIR,
)
from vivarium.data.nucleotides import nucleotides
from vivarium.data.amino_acids import amino_acids
from vivarium.data.chromosomes.flagella_chromosome import FlagellaChromosome
from vivarium.plots.gene_expression import plot_timeseries_heatmaps
from vivarium.states.chromosome import Chromosome, rna_bases, sequence_monomers
from vivarium.parameters.parameters import (
    parameter_scan,
    get_parameters_logspace,
    plot_scan_results,
)

# vivarium libraries
from vivarium.library.dict_utils import deep_merge
from vivarium.library.units import units

# processes
from vivarium.processes.transcription import UNBOUND_RNAP_KEY
from vivarium.processes.translation import UNBOUND_RIBOSOME_KEY
from vivarium.processes.convenience_kinetics import ConvenienceKinetics, get_glc_lct_config
from vivarium.processes.metabolism import Metabolism, get_iAF1260b_config
from vivarium.processes.division_volume import DivisionVolume
from vivarium.processes.meta_division import MetaDivision

# compartments
from vivarium.compartments.gene_expression import (
    GeneExpression,
    plot_gene_expression_output,
    gene_network_plot,
)


NAME = 'flagella_gene_expression'
COMPARTMENT_TIMESTEP = 10.0

def default_metabolism_config():
    metabolism_config = get_iAF1260b_config()
    metabolism_config.update({
        'initial_mass': 1339.0,  # 200, # fg of metabolite pools
        'time_step': COMPARTMENT_TIMESTEP,
        'tolerance': {
            'EX_glc__D_e': [1.05, 1.0],
            'EX_lcts_e': [1.05, 1.0],
        }})
    return metabolism_config



class FlagellaExpressionMetabolism(Generator):
    defaults = {
        'boundary_path': ('boundary',),
        'agents_path': ('agents',),  # ('..', '..', 'agents',),
        'daughter_path': tuple(),
        'transport': get_glc_lct_config(),
        'metabolism': default_metabolism_config(),
        'gene_expression': {
            'initial_mass': 0.0 * units.fg,
            'time_step': COMPARTMENT_TIMESTEP,
        }
    }

    def __init__(self, config=None):
        if not config:
            config = {}
        self.config = copy.deepcopy(self.defaults)
        self.config = deep_merge(self.config, config)

        if 'agent_id' not in self.config:
            self.config['agent_id'] = str(uuid.uuid1())

    def generate_processes(self, process_config):
        config = copy.deepcopy(self.config)
        config = deep_merge(config, process_config)

        daughter_path = config['daughter_path']
        agent_id = config['agent_id']

        # get paths
        boundary_path = config['boundary_path']
        agents_path = config['agents_path']
        external_path = boundary_path + ('external',)

        # configure a flagella gene expression compartment, and get its network
        flagella_expression_config = get_flagella_expression_config({})
        flagella_expression_config['global_path'] = boundary_path
        flagella_expression_config.update(config['gene_expression'])
        gene_expression = GeneExpression(flagella_expression_config)
        gene_expression_network = gene_expression.generate()
        processes = gene_expression_network['processes']
        self.topology = gene_expression_network['topology']

        # Transport
        transport = ConvenienceKinetics(config['transport'])
        target_fluxes = transport.kinetic_rate_laws.reaction_ids

        # Metabolism
        # add target fluxes from transport
        metabolism_config = config.get('metabolism')
        metabolism_config.update({'constrained_reaction_ids': target_fluxes})
        metabolism = Metabolism(metabolism_config)

        # Division
        # configure division condition and meta-division processes
        division_condition = DivisionVolume({})
        meta_division_config = dict(
            {},
            daughter_path=daughter_path,
            agent_id=agent_id,
            compartment=self)
        meta_division = MetaDivision(meta_division_config)

        # combine processes
        processes['transport'] = transport
        processes['metabolism'] = metabolism
        processes['division_condition'] = division_condition
        processes['meta_division'] = meta_division

        # save the topology for generate_topology
        self.topology['transport'] = {
            'internal': ('metabolites',),
            'external': external_path,
            'exchange': ('null',),  # metabolism's exchange is used
            'fluxes': ('flux_bounds',),
            'global': boundary_path
        }
        self.topology['metabolism'] = {
                'internal': ('molecules',),
                'external': external_path,
                'fields': ('fields',),
                'reactions': ('reactions',),
                'flux_bounds': ('flux_bounds',),
                'global': boundary_path,
                'dimensions': ('dimensions',),
        }
        self.topology['division_condition'] = {
            'global': boundary_path
        }
        self.topology['meta_division'] = {
            'global': boundary_path,
            'cells': agents_path
        }

        return processes

    def generate_topology(self, config):
        return self.topology




def flagella_expression_compartment(config):
    flagella_expression_config = get_flagella_expression_config(config)
    return GeneExpression(flagella_expression_config)


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
                'endoRNAse': 0.02},
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
                UNBOUND_RIBOSOME_KEY: 100,  # e. coli has ~ 20000 ribosomes
                UNBOUND_RNAP_KEY: 100
            }
    }


def make_compartment_topology(compartment, out_dir='out'):
    settings = {'show_ports': True}
    plot_compartment_topology(
        compartment,
        settings,
        out_dir)


def make_flagella_network(out_dir='out'):
    # load the compartment
    flagella_compartment = flagella_expression_compartment({})

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


def run_flagella_compartment(compartment, out_dir='out'):

    # get flagella data
    flagella_data = FlagellaChromosome()

    # run simulation
    initial_state = get_flagella_initial_state()
    settings = {
        # a cell cycle of 2520 sec is expected to express 8 flagella.
        # 2 flagella expected in approximately 630 seconds.
        'total_time': 2520,
        'emit_step': COMPARTMENT_TIMESTEP,
        'verbose': True,
        'initial_state': initial_state}
    timeseries = simulate_compartment_in_experiment(compartment, settings)

    # save reference timeseries
    save_timeseries(timeseries, out_dir)

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
        'remove_zeros': True,
        'skip_ports': ['chromosome', 'ribosomes']}
    plot_simulation_output(
        timeseries,
        plot_settings,
        out_dir)


# @pytest.mark.slow
def test_flagella_expression():
    flagella_compartment = flagella_expression_compartment({})

    # initial state for flagella complexation
    initial_state = get_flagella_initial_state()
    initial_state['proteins'].update({
        'Ribosome': 100,  # plenty of ribosomes
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
        'total_time': 1000,
        'emit_step': 100,
        'initial_state': initial_state}
    timeseries = simulate_compartment_in_experiment(flagella_compartment, settings)

    print(timeseries['proteins']['flagella'])
    final_flagella = timeseries['proteins']['flagella'][-1]
    # this should have been long enough for flagellar complexation to occur
    assert final_flagella > 0


def scan_flagella_expression_parameters():
    compartment = flagella_expression_compartment({})
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
    parser.add_argument('--metabolism', '-m', action='store_true', default=False, )
    args = parser.parse_args()

    if args.scan:
        results = scan_flagella_expression_parameters()
        plot_scan_results(results, out_dir)
    elif args.network:
        make_flagella_network(out_dir)
    elif args.topology:
        compartment = flagella_expression_compartment({})
        make_compartment_topology(compartment, out_dir)
    elif args.metabolism:
        mtb_out_dir = os.path.join(out_dir, 'metabolism')
        if not os.path.exists(mtb_out_dir):
            os.makedirs(mtb_out_dir)
        compartment = FlagellaExpressionMetabolism({})
        make_compartment_topology(compartment, mtb_out_dir)
        run_flagella_compartment(compartment, mtb_out_dir)
    else:
        compartment = flagella_expression_compartment({})
        run_flagella_compartment(compartment, out_dir)

