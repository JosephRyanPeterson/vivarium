'''
===================
Colony Mass Deriver
===================
'''

from __future__ import absolute_import, division, print_function

import copy

from vivarium.core.experiment import get_in
from vivarium.core.process import Deriver
from vivarium.library.dict_utils import deep_merge
from vivarium.library.units import units


def assert_no_divide(state):
    raise AssertionError('Colony mass cannot be divided!')


class ColonyMassDeriver(Deriver):

    defaults = {
        'agent_mass_path': ('boundary', 'mass')
    }

    def ports_schema(self):
        return {
            'colony_global': {
                'mass': {
                    '_default': 0.0 * units.fg,
                    '_divider': assert_no_divide,
                    '_updater': 'set',
                    '_emit': True,
                },
            },
            'agents': {
                '_default': dict(),
                '_divider': assert_no_divide,
                '_updater': 'set',
            },
        }

    def next_update(self, timestep, states):
        agents = states['agents']
        assert isinstance(agents, dict)
        mass = 0 * units.fg
        for agent, agent_state in agents.items():
            if agent.startswith('_'):
                # This is a special key like `_subschema`, not an agent
                continue
            mass += get_in(agent_state, self.parameters['agent_mass_path'])
        return {
            'colony_global': {
                'mass': mass,
            },
        }


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
            'agent_mass_path': ('globals', 'metrics', 'mass'),
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
