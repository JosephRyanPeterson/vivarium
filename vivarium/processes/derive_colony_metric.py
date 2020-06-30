'''
=====================
Colony Metric Deriver
=====================

This is used as the base class for other colony metric derivers.
'''


from __future__ import division, absolute_import, print_function

from vivarium.core.process import Deriver
from vivarium.core.experiment import get_in

def assert_no_divide(state):
    raise AssertionError('Colony mass cannot be divided!')


class ColonyMetricDeriver(Deriver):

    defaults = {}

    def __init__(self, parameters):
        required = (
            'metric_port', 'metric_port_schema', 'agent_metric_path',
            'variable_name'
        )
        for parameter in required:
            if parameter not in parameters:
                raise ValueError(
                    'ColonyMetricDeriver requires parameter {}'.format(
                        parameter
                    )
                )
        if 'metric_zero' not in parameters:
            parameters['metric_zero'] = parameters[
                'metric_port_schema']['_default']
        super(ColonyMetricDeriver, self).__init__(parameters)

    def ports_schema(self):
        return {
            'colony_global': {
                self.parameters['metric_port']: (
                    self.parameters['metric_port_schema'])
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
        metric = self.parameters['metric_zero']
        for agent, agent_state in agents.items():
            if agent.startswith('_'):
                # This is a special key like `_subschema`, not an agent
                continue
            agent_metric = get_in(
                agent_state, self.parameters['agent_metric_path'])
            if agent_metric:
                # Ignore agents that don't have the variable
                metric += agent_metric
        return {
            'colony_global': {
                self.parameters['variable_name']: metric,
            }
        }
