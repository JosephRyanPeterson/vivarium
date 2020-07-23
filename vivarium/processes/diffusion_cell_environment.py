from __future__ import absolute_import, division, print_function

import numpy as np

from vivarium.library.dict_utils import deep_merge
from vivarium.library.units import units, remove_units
from vivarium.core.process import Process


class CellEnvironmentDiffusion(Process):

    name = "cell_environment_diffusion"
    defaults = {
        'molecules_to_diffuse': [],
        'default_state': {
            'global': {
                'volume': 1.2 * units.fL,
            }
        },
        'default_default': 0,
        'permeabilities': {
            'porin': 1e-1,
        },
    }

    def ports_schema(self):

        schema = {
            'internal': {
                # Molecule concentration in mmol/L
                molecule: {
                    '_default': self.parameters['default_default'],
                }
                for molecule in self.parameters['molecules_to_diffuse']
            },
            'external': {
                # Molecule concentration in mmol/L
                molecule: {
                    '_default': self.parameters['default_default'],
                }
                for molecule in self.parameters['molecules_to_diffuse']
            },
            'membrane': {
                # Porin concentration in mmol/L
                porin: {
                    '_default': self.parameters['default_default'],
                    '_emit': True,
                }
                for porin in self.parameters['permeability_per_porin']
            },
            'fields': {
                # Molecule count in mmol
                molecule: {
                    '_default': np.full(
                        (1, 1), self.parameters['default_default']),
                }
                for molecule in self.parameters['molecules_to_diffuse']
            },
            'global': {
                'volume': {
                    '_default': self.parameters['default_default'],
                },
                'location': {
                    '_default': [0.5, 0.5],
                },
            },
            'dimensions': {
                'bounds': {
                    '_default': [1, 1],
                },
                'n_bins': {
                    '_default': [1, 1],
                },
                'depth': {
                    '_default': 1,
                },
            },
        }

        for port, port_conf in self.parameters['default_state'].items():
            for variable, default in port_conf.items():
                schema[port][variable]['_default'] = default

        return schema

    def next_update(self, timestep, states):
        permeabilities = self.parameters['permeabilities']
        rates = {
            molecule: sum([
                states['membrane'][porin] * permeability
                for porin, permeability in permeabilities.items()
            ])
            for molecule in self.parameters['molecules_to_diffuse']
        }
        # Flux is positive when leaving the cell
        flux = {
            molecule: (
                states['internal'][molecule]
                - states['external'][molecule]
            ) * rate
            for molecule, rate in rates.items()
        }
        cell_volume = remove_units(states['global']['volume'])
        update = {
            'fields': {
                molecule: {
                    '_value': mol_flux,
                    '_updater': {
                        'updater': 'update_field_with_exchange',
                        'port_mapping': {
                            'global': 'global',
                            'dimensions': 'dimensions',
                        },
                    },
                }
                for molecule, mol_flux in flux.items()
            },
            'internal': {
                molecule: - mol_flux / cell_volume
                for molecule, mol_flux in flux.items()
            },
        }
        return update
