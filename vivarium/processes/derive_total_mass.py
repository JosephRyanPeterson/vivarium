'''
==================
Total Mass Deriver
==================
'''

from __future__ import absolute_import, division, print_function

import copy

from vivarium.library.units import units
from vivarium.processes.derive_total_metric import (
    TotalMetricDeriver,
    assert_no_divide,
)


class TotalMassDeriver(TotalMetricDeriver):

    defaults = {
        'metric_variable': 'mass',
        'metric_port_schema': {
            '_default': 0.0 * units.fg,
            '_divider': assert_no_divide,
            '_updater': 'set',
            '_emit': True,
        },
        'agent_metric_glob_schema': {
            'boundary': {
                'mass': {
                    '_default': 0.0 * units.fg,
                    '_divider': 'split',
                    '_updater': 'set',
                    '_emit': True,
                },
            },
        },
    }

    def __init__(self, parameters=None):
        if parameters is None:
            parameters = {}
        config = copy.deepcopy(self.defaults)
        config.update(parameters)
        super(TotalMassDeriver, self).__init__(config)


class TestTotalMassDeriver():

    def test_single_agent_unconfigured(self):
        deriver = TotalMassDeriver()
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
            'total_global': {
                'mass': 5 * units.fg,
            },
        }
        assert update == expected_update

    def test_ignores_underscore_prefixes(self):
        deriver = TotalMassDeriver()
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
            'total_global': {
                'mass': 0 * units.fg,
            },
        }
        assert update == expected_update

    def test_multiple_agents(self):
        deriver = TotalMassDeriver()
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
            'total_global': {
                'mass': 8 * units.fg,
            },
        }
        assert update == expected_update

    def test_configure_mass_path(self):
        deriver = TotalMassDeriver({
            'agent_metric_glob_schema': {
                'globals': {
                    'metrics': {
                        'mass': {
                            '_default': 0.0 * units.fg,
                        },
                    },
                },
            },
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
            'total_global': {
                'mass': 8 * units.fg,
            },
        }
        assert update == expected_update
