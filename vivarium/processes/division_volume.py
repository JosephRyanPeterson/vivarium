from __future__ import absolute_import, division, print_function

from vivarium.utils.units import units
from vivarium.core.process import Process



class DivisionVolume(Process):

    defaults = {
        'initial_state': {},
        'division_volume': 2.4 * units.fL,  # fL
    }

    def __init__(self, initial_parameters={}):
        self.division = 0
        division_volume = initial_parameters.get('division_volume', self.defaults['division_volume'])

        ports = {
            'global': [
                'volume',
                'division']}

        parameters = {
            'division_volume': division_volume}  # TODO -- make division at 2X initial_volume?  Pass this in from initial_parameters

        super(DivisionVolume, self).__init__(ports, parameters)

    def ports_schema(self):
        return {
            'global': {
                'division': {
                    '_default': 0,
                    '_emit': True,
                    '_updater': 'set',
                    '_divider': 'zero'},
                'volume': {
                    '_default': 1.2 * units.fL}}}

    def next_update(self, timestep, states):
        volume = states['global']['volume']
        if volume >= self.parameters['division_volume']:
            self.division = 1
            return {'global': {'division': self.division}}
        else:
            return {}
