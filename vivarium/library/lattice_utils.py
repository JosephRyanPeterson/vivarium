'''
==================================
Utilities for Lattice Environments
==================================
'''

from __future__ import absolute_import, division, print_function

import numpy as np
from scipy import constants


AVOGADRO = constants.N_A


def get_bin_site(location, n_bins, bounds):
    '''Get a bin's indices in the lattice

    Parameters:
        location (list): A list of 2 floats that specify the x and y
            coordinates of a point inside the desired bin.
        n_bins (list): A list of 2 ints that specify the number of bins
            along the x and y axes, respectively.
        bounds (list): A list of 2 floats that define the dimensions of
            the lattice environment along the x and y axes,
            respectively.

    Returns:
        tuple: A 2-tuple of the x and y indices of the bin in the
        lattice.
    '''
    bin_site_no_rounding = np.array([
        location[0] * n_bins[0] / bounds[0],
        location[1] * n_bins[1] / bounds[1]
    ])
    bin_site = tuple(
        np.floor(bin_site_no_rounding).astype(int) % n_bins)
    return bin_site


def get_bin_volume(n_bins, bounds, depth):
    total_volume = (depth * bounds[0] * bounds[1]) * 1e-15  # (L)
    return total_volume / (n_bins[0] * n_bins[1])


def count_to_concentration(count, bin_volume):
    return count / (bin_volume * AVOGADRO)
