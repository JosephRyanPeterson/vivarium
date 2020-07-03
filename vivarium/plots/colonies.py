'''
=====================
Colony Plotting Tools
=====================

This module contains tools to help you plot colony data.
'''

from __future__ import division, absolute_import, print_function

from matplotlib import pyplot as plt
import numpy as np
from scipy import stats

from vivarium.library.units import remove_units


INCH_PER_COL = 4
INCH_PER_ROW = 2
SUBPLOT_W_SPACE = 0.4
SUBPLOT_H_SPACE = 1.5

NUM_COLONIES_PATH = 'Number of Colonies'


def plot_colony_metrics(
    path_ts, title_size=16, tick_label_size=12, max_cols=5
):
    '''Plot colony metrics over time.

    Metric mean is plotted with SEM error bands.

    Arguments:
        path_ts (dict): Path timeseries of the data to plot. Each item
            in the dictionary should have as its key the path and as its
            value a list of values for each timepoint. Each value should
            be a list of metric values, one entry per colony. The
            dictionary should have one additional key, ``time``, whose
            value is a list of times for each timepoint.
        title_size (int): Font size for the title of each plot
        tick_label_size (int): Font size for each plot's axis tick
            labels.
        max_cols (int): The maximum number of columns. We add columns
            until we hit this limit, and only then do we add rows.

    Returns:
        matplotlib.figure.Figure: The plot as a Figure object.
    '''
    path_ts = remove_units(path_ts)
    times = path_ts['time']
    del path_ts['time']
    # path_ts has tuples for keys. Here we turn those into strings so
    # that numpy doesn't iterate through the path elements
    path_ts = {
        str(key): val for key, val in path_ts.items()
    }
    arbitrary_metric = list(path_ts.keys())[0]
    path_ts[NUM_COLONIES_PATH] = [
        len(timepoint) for timepoint in path_ts[arbitrary_metric]
    ]
    # Create Figure
    paths = sorted(path_ts.keys())
    n_cols = min(len(paths), max_cols)
    n_rows = int(np.ceil(len(paths) / n_cols))
    fig = plt.figure(
        figsize=(INCH_PER_COL * n_cols, INCH_PER_ROW * n_rows))
    grid = plt.GridSpec(
        ncols=n_cols, nrows=n_rows, wspace=SUBPLOT_W_SPACE,
        hspace=SUBPLOT_H_SPACE
    )

    # Assign paths to subplot coordinates
    padding = [None] * int(n_cols * n_rows - len(paths))
    paths += padding
    paths_grid = np.array(paths)
    paths_grid = paths_grid.reshape((n_rows, n_cols))

    # Create the subplots
    for i in range(n_rows):
        for j in range(n_cols):
            path = paths_grid[i, j]
            if path is None:
                continue
            ax = fig.add_subplot(grid[i, j])
            # Configure axes and titles
            for tick_type in ('major', 'minor'):
                ax.tick_params(
                    axis='both', which=tick_type,
                    labelsize=tick_label_size
                )
            ax.title.set_text(path)
            ax.title.set_fontsize(title_size)
            ax.set_xlim([times[0], times[-1]])
            # Plot data
            data = path_ts[path]
            if path == NUM_COLONIES_PATH:
                ax.plot(times, data)
            else:
                means = []
                sems = []
                plot_times = []
                for i_time, metrics_list in enumerate(data):
                    if not metrics_list:
                        continue
                    array = np.array(metrics_list)
                    means.append(np.mean(array))
                    sems.append(stats.sem(array))
                    plot_times.append(times[i_time])
                x = np.array(plot_times)
                y = np.array(means)
                yerr = np.array(sems)
                yerr[np.isnan(yerr)] = 0
                ax.plot(x, y)
                ax.fill_between(x, y - yerr, y + yerr, alpha=0.2)

    return fig
