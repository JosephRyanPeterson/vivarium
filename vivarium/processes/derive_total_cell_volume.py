'''
=========================
Total Cell Volume Deriver
=========================
'''


from __future__ import division, print_function, absolute_import

import copy

from vivarium.processes.derive_total_metric import (
    TotalMetricDeriver,
    assert_no_divide,
)


class TotalCellVolumeDeriver(TotalMetricDeriver):

    defaults = {
        'metric_variable': 'volume',
        'metric_port_schema': {
            '_default': 0.0,
            '_divider': assert_no_divide,
            '_updater': 'set',
            '_emit': True,
        },
        'agent_metric_glob_schema': {
            'boundary': {
                'volume': {
                    '_default': 0.0,
                    '_divider': 'split',
                    '_updater': 'set',
                    '_emit': True,
                }
            }
        }
    }

    def __init__(self, parameters=None):
        if parameters is None:
            parameters = {}
        config = copy.deepcopy(self.defaults)
        config.update(parameters)
        super(TotalCellVolumeDeriver, self).__init__(config)

class TestTotalCellVolumeDeriver():

    def test_single_agent_unconfigured(self):
        deriver = TotalCellVolumeDeriver()
        states = {
            'agents': {
                'agent_1': {
                    'boundary': {
                        'volume': 5,
                    },
                },
            }
        }
        # timestep not used by this deriver
        update = deriver.next_update(-1, states)
        expected_update = {
            'total_global': {
                'volume': 5,
            },
        }
        assert update == expected_update

    def test_ignores_underscore_prefixes(self):
        deriver = TotalCellVolumeDeriver()
        states = {
            'agents': {
                '_agent': {
                    'boundary': {
                        'volume': 5,
                    },
                },
            }
        }
        # timestep not used by this deriver
        update = deriver.next_update(-1, states)
        expected_update = {
            'total_global': {
                'volume': 0,
            },
        }
        assert update == expected_update

    def test_multiple_agents(self):
        deriver = TotalCellVolumeDeriver()
        states = {
            'agents': {
                'agent_1': {
                    'boundary': {
                        'volume': 5,
                    },
                },
                'agent_2': {
                    'boundary': {
                        'volume': 3,
                    },
                },
            }
        }
        # timestep not used by this deriver
        update = deriver.next_update(-1, states)
        expected_update = {
            'total_global': {
                'volume': 8,
            },
        }
        assert update == expected_update

    def test_configure_volume_path(self):
        deriver = TotalCellVolumeDeriver({
            'agent_metric_glob_schema': {
                'globals': {
                    'metrics': {
                        'volume': {
                            '_default': 0.0,
                            '_updater': 'set',
                            '_divider': 'split',
                            '_emit': True,
                        }
                    }
                }
            }
        })
        states = {
            'agents': {
                'agent_1': {
                    'globals': {
                        'metrics': {
                            'volume': 5,
                        },
                    },
                },
                'agent_2': {
                    'globals': {
                        'metrics': {
                            'volume': 3,
                        },
                    },
                },
            }
        }
        # timestep not used by this deriver
        update = deriver.next_update(-1, states)
        expected_update = {
            'total_global': {
                'volume': 8,
            },
        }
        assert update == expected_update
