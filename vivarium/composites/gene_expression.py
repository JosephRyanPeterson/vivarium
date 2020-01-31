from __future__ import absolute_import, division, print_function

import os

import matplotlib.pyplot as plt

from vivarium.actor.process import initialize_state

# processes
from vivarium.processes.transcription import Transcription
from vivarium.processes.translation import Translation
from vivarium.processes.deriver import Deriver
from vivarium.processes.division import Division, divide_condition, divide_state



def compose_gene_expression(config):

    # declare the processes
    transcription = Transcription(config.get('transcription', {}))
    translation = Translation(config.get('translation', {}))
    deriver = Deriver(config)
    division = Division(config)

    # place processes in layers
    processes = [
        {'transcription': transcription,
         'translation': translation},
        {'deriver': deriver,
         'division': division}]

    # make the topology
    topology = {
        'transcription': {
            'chromosome': 'chromosome',
            'molecules': 'molecules',
            'transcripts': 'transcripts'},
        'translation': {
            'ribosomes': 'ribosomes',
            'molecules': 'molecules',
            'transcripts': 'transcripts',
            'proteins': 'proteins'},
        'deriver': {
            'counts': 'cell_counts',
            'state': 'cell',
            'prior_state': 'prior_state'},
        'division': {
            'internal': 'cell'}}

    # initialize the states
    states = initialize_state(processes, topology, config.get('initial_state', {}))

    options = {
        'name': 'growth_division_composite',
        'environment_role': 'environment',
        'exchange_role': 'exchange',
        'topology': topology,
        'initial_time': config.get('initial_time', 0.0),
        'divide_condition': divide_condition,
        'divide_state': divide_state}

    return {
        'processes': processes,
        'states': states,
        'options': options}


# analysis
def plot_gene_expression_output(timeseries, out_dir='out'):

    molecules = timeseries['molecules']
    transcripts = timeseries['transcripts']
    proteins = timeseries['proteins']
    time = timeseries['time']

    # make figure and plot
    n_cols = 1
    n_rows = 3
    plt.figure(figsize=(n_cols * 6, n_rows * 1.5))

    # define subplots
    ax1 = plt.subplot(n_rows, n_cols, 1)
    ax2 = plt.subplot(n_rows, n_cols, 2)
    ax3 = plt.subplot(n_rows, n_cols, 3)

    # plot molecules
    for mol_id, series in molecules.items():
        ax1.plot(time, series, label=mol_id)
    # ax1.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))
    ax1.title.set_text('metabolites')

    # plot transcripts
    for transcript_id, series in transcripts.items():
        ax2.plot(time, series, label=transcript_id)
    ax2.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))
    ax2.title.set_text('transcripts')

    # plot proteins
    for protein_id, series in proteins.items():
        ax3.plot(time, series, label=protein_id)
    ax3.legend(loc='center left', bbox_to_anchor=(1.0, 0.5))
    ax3.title.set_text('proteins')

    # adjust axes
    for axis in [ax1, ax2, ax3]:
        axis.spines['right'].set_visible(False)
        axis.spines['top'].set_visible(False)

    ax1.set_xticklabels([])
    ax2.set_xticklabels([])
    ax3.set_xlabel('time (s)', fontsize=12)

    # save figure
    fig_path = os.path.join(out_dir, 'gene_expression')
    plt.subplots_adjust(wspace=0.3, hspace=0.5)
    plt.savefig(fig_path, bbox_inches='tight')


if __name__ == '__main__':
    from vivarium.actor.process import load_compartment, simulate_compartment, convert_to_timeseries

    out_dir = os.path.join('out', 'tests', 'gene_expression_composite')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # load the compartment
    gene_expression_compartment = load_compartment(compose_gene_expression)

    # run simulation
    settings = {
        'total_time': 40}
    saved_state = simulate_compartment(gene_expression_compartment, settings)
    del saved_state[0]  # remove the first state
    timeseries = convert_to_timeseries(saved_state)
    plot_gene_expression_output(timeseries, out_dir)