'''
===================
Colony Mass Deriver
===================
'''

from __future__ import absolute_import, division, print_function

import copy

from vivarium.library.dict_utils import deep_merge
from vivarium.library.units import units
from vivarium.processes.derive_colony_metric import (
    ColonyMetricDeriver,
    assert_no_divide,
)


class ColonyMassDeriver(ColonyMetricDeriver):

    defaults = {
        'metric_port': 'mass',
        'metric_port_schema': {
            '_default': 0.0 * units.fg,
            '_divider': assert_no_divide,
            '_updater': 'set',
            '_emit': True,
        },
        'agent_metric_path': ('boundary', 'mass'),
        'variable_name': 'mass',
    }

    def __init__(self, parameters=None):
        if parameters is None:
            parameters = {}
        config = copy.deepcopy(self.defaults)
        deep_merge(config, parameters)
        super(ColonyMassDeriver, self).__init__(config)


class TestColonyMassDeriver():

    def test_single_agent_unconfigured(self):
        deriver = ColonyMassDeriver()
        states = {
            'agents': {
                'agent_1': {
                    'boundary': {
                        'mass': 5 * units.fg
                    },
                },
            }
        }
        # timestep not used by this deriver
        update = deriver.next_update(-1, states)
        expected_update = {
            'colony_global': {
                'mass': 5 * units.fg,
            },
        }
        assert update == expected_update

    def test_ignores_underscore_prefixes(self):
        deriver = ColonyMassDeriver()
        states = {
            'agents': {
                '_agent': {
                    'boundary': {
                        'mass': 5 * units.fg
                    },
                },
            }
        }
        # timestep not used by this deriver
        update = deriver.next_update(-1, states)
        expected_update = {
            'colony_global': {
                'mass': 0 * units.fg,
            },
        }
        assert update == expected_update

    def test_multiple_agents(self):
        deriver = ColonyMassDeriver()
        states = {
            'agents': {
                'agent_1': {
                    'boundary': {
                        'mass': 5 * units.fg
                    },
                },
                'agent_2': {
                    'boundary': {
                        'mass': 3 * units.fg
                    },
                },
            }
        }
        # timestep not used by this deriver
        update = deriver.next_update(-1, states)
        expected_update = {
            'colony_global': {
                'mass': 8 * units.fg,
            },
        }
        assert update == expected_update

    def test_configure_mass_path(self):
        deriver = ColonyMassDeriver({
            'agent_metric_path': ('globals', 'metrics', 'mass'),
        })
        states = {
            'agents': {
                'agent_1': {
                    'globals': {
                        'metrics': {
                            'mass': 5 * units.fg
                        },
                    },
                },
                'agent_2': {
                    'globals': {
                        'metrics': {
                            'mass': 3 * units.fg
                        },
                    },
                },
            }
        }
        # timestep not used by this deriver
        update = deriver.next_update(-1, states)
        expected_update = {
            'colony_global': {
                'mass': 8 * units.fg,
            },
        }
        assert update == expected_update
