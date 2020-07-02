'''
====================
Total Metric Deriver
====================

This is used as the base class for other total metric derivers.
'''


from __future__ import division, absolute_import, print_function

import pytest

from vivarium.core.process import Deriver
from vivarium.core.experiment import get_in

def assert_no_divide(state):
    raise AssertionError('Total mass cannot be divided!')


def path_from_schema(schema):
    assert isinstance(schema, dict)
    if not schema:
        return tuple()
    if len(schema) > 1:
        # Make sure we are at a config
        for val in schema.values():
            if isinstance(val, dict):
                raise ValueError(
                    'Schema has subschema and multiple children: {}'
                    .format(schema)
                )
        return tuple()
    child_name = list(schema.keys())[0]
    if not isinstance(schema[child_name], dict):
        return tuple()
    path = (child_name,) + path_from_schema(schema[child_name])
    return path


class TotalMetricDeriver(Deriver):

    defaults = {}

    def __init__(self, parameters):
        required = (
            'metric_variable', 'metric_port_schema',
            'agent_metric_glob_schema',
        )
        for parameter in required:
            if parameter not in parameters:
                raise ValueError(
                    'TotalMetricDeriver requires parameter {}'.format(
                        parameter
                    )
                )
        if 'metric_zero' not in parameters:
            parameters['metric_zero'] = parameters[
                'metric_port_schema']['_default']
        super(TotalMetricDeriver, self).__init__(parameters)
        # Superclass does a deep merge, between parameters and
        # self.defaults, which we don't want because we don't want to
        # merge schemas. Thus, we override self.parameters here
        self.parameters = parameters

    def ports_schema(self):
        return {
            'total_global': {
                self.parameters['metric_variable']: (
                    self.parameters['metric_port_schema'])
            },
            'agents': {
                '*': self.parameters['agent_metric_glob_schema'],
            },
        }

    def next_update(self, timestep, states):
        agents = states['agents']
        assert isinstance(agents, dict)
        metric = self.parameters['metric_zero']
        agent_metric_path = path_from_schema(
            self.parameters['agent_metric_glob_schema'])
        for agent, agent_state in agents.items():
            if agent.startswith('_'):
                # This is a special key like `_subschema`, not an agent
                continue
            agent_metric = get_in(
                agent_state, agent_metric_path)
            if agent_metric:
                # Ignore agents that don't have the variable
                metric += agent_metric
        return {
            'total_global': {
                self.parameters['metric_variable']: metric,
            }
        }


class TestPathFromSchema():

    def test_realistic_example(self):
        schema = {
            'boundary': {
                'metric': {
                    '_updater': 'set',
                    '_divider': 'split',
                }
            }
        }
        path = path_from_schema(schema)
        expected_path = ('boundary', 'metric')
        assert path == expected_path

    def test_empty_schema(self):
        schema = {}
        path = path_from_schema(schema)
        expected_path = tuple()
        assert path == expected_path

    def test_empty_path(self):
        schema = {
            '_updater': 'set',
        }
        path = path_from_schema(schema)
        expected_path = tuple()
        assert path == expected_path

    def test_invalid_schema_siblings(self):
        schema = {
            'boundary': {
                'metric': {
                    '_updater': 'set',
                },
                'metric2': {
                    '_updater': 'set',
                },
            }
        }
        with pytest.raises(ValueError) as error:
            path_from_schema(schema)
        assert (
            'Schema has subschema and multiple children'
            in str(error.value)
        )

    def test_empty_variable_config(self):
        schema = {
            'boundary': {
                'metric': {
                }
            }
        }
        path = path_from_schema(schema)
        expected_path = ('boundary', 'metric')
        assert path == expected_path
