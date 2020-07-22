from __future__ import absolute_import, division, print_function

import copy

import numpy as np

from vivarium.library.units import units
from vivarium.library.dict_utils import deep_merge
from vivarium.core.process import Deriver

from vivarium.processes.derive_globals import AVOGADRO


class NonSpatialEnvironment(Deriver):
    '''A non-spatial environment with volume'''

    name = 'nonspatial_environment'
    defaults = {
        'volume': 1e-12 * units.L,
    }

    def __init__(self, initial_parameters=None):
        if initial_parameters is None:
            initial_parameters = {}

        volume = initial_parameters.get('volume', self.defaults['volume'])
        self.mmol_to_counts = (AVOGADRO.to('1/mmol') * volume).to('L/mmol')

        parameters = copy.deepcopy(NonSpatialEnvironment.defaults)
        parameters.update(initial_parameters)
        super(NonSpatialEnvironment, self).__init__(parameters)

    def ports_schema(self):
        return {
            'external': {
                '*': {
                    '_value': 0,
                },
            },
            'fields': {
                '*': {
                    '_value': np.ones((1, 1)),
                },
            },
            'dimensions': {
                'depth': {
                    '_value': 1,
                },
                'n_bins': {
                    '_value': [1, 1],
                },
                'bounds': {
                    '_value': [1, 1],
                },
            },
            'global': {
                'location': {
                    '_value': [0.5, 0.5],
                },
                'volume': {
                    '_value': self.parameters['volume'],
                }
            },
        }

    def next_update(self, timestep, states):
        fields = states['fields']

        update = {
            'external': {
                mol_id: {
                    '_updater': 'set',
                    '_value': field[0][0],
                }
                for mol_id, field in fields.items()
            },
        }

        return update
