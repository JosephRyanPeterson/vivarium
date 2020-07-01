'''
====================
Colony Shape Deriver
====================
'''

from __future__ import absolute_import, division, print_function

import alphashape
from shapely.geometry.polygon import Polygon
from shapely.geometry.collection import GeometryCollection

from vivarium.core.process import Deriver
from vivarium.processes.derive_colony_metric import assert_no_divide
from vivarium.processes.multibody_physics import daughter_locations


class ColonyShapeDeriver(Deriver):
    '''Derives colony shape metrics from cell locations
    '''

    defaults = {
        'agents_path': tuple(),
        'alpha': 1.0,
    }

    def ports_schema(self):
        return {
            'agents': {
                '*': {
                    'boundary': {
                        'location': {
                            '_emit': True,
                            '_default': [0.5, 0.5],
                            '_updater': 'set',
                            '_divider': {
                                'divider': daughter_locations,
                                'topology': {
                                    'length': ('length',),
                                    'angle': ('angle',)
                                },
                            },
                        },
                    },
                },
            },
            'colony_global': {
                'surface_area': {
                    '_default': 0.0,
                    '_updater': 'set',
                    '_divider': assert_no_divide,
                    '_emit': True,
                },
            },
        }

    def next_update(self, timestep, states):
        agents = states['agents']
        points = [
            agent['boundary']['location']
            for agent in agents.values()
        ]
        alpha_shape = alphashape.alphashape(
            points, self.parameters['alpha'])
        area = 0
        if isinstance(alpha_shape, Polygon):
            area = alpha_shape.area
        else:
            assert isinstance(alpha_shape, GeometryCollection)
            for shape in alpha_shape:
                area += shape.area

        return {
            'colony_global': {
                'surface_area': area,
            }
        }


class TestDeriveColonyShape():

    def calc_shape_metrics(self, points, agents_path=None, alpha=None):
        config = {}
        if agents_path is not None:
            config['agents_path'] = agents_path
        if alpha is not None:
            config['alpha'] = alpha
        deriver = ColonyShapeDeriver(config)
        states = {
            'agents': {
                str(i): {
                    'boundary': {
                        'location': list(point),
                    },
                }
                for i, point in enumerate(points)
            },
            'colony_global': {
                'surface_area': 0.0,
            }
        }
        # Timestep does not matter
        update = deriver.next_update(-1, states)
        return update['colony_global']

    def test_convex(self):
        #    *
        #   / \
        #  * * *
        #   \ /
        #    *
        points = [
            (1, 2),
            (0, 1), (1, 1), (2, 1),
            (1, 0),
        ]
        metrics = self.calc_shape_metrics(points)
        expected_metrics = {
            'surface_area': 2
        }
        assert metrics == expected_metrics

    def test_concave(self):
        # *-*-*-*-*
        # |       |
        # * * *-*-*
        # |  /
        # * *
        # |  \
        # * * *-*-*
        # |       |
        # *-*-*-*-*
        points = (
            [(i, 4) for i in range(5)]
            + [(i, 3) for i in range(5)]
            + [(i, 2) for i in range(2)]
            + [(i, 1) for i in range(5)]
            + [(i, 0) for i in range(5)]
        )
        metrics = self.calc_shape_metrics(points)
        expected_metrics = {
            'surface_area': 11,
        }
        assert metrics == expected_metrics

    def test_ignore_outliers(self):
        #    *
        #   / \
        #  * * *            *
        #   \ /
        #    *
        points = [
            (1, 2),
            (0, 1), (1, 1), (2, 1), (10, 1),
            (1, 0),
        ]
        metrics = self.calc_shape_metrics(points)
        expected_metrics = {
            'surface_area': 2,
        }
        assert metrics == expected_metrics

    def test_colony_too_diffuse(self):
        #    *
        #
        #  *   *
        #
        #    *
        points = [
            (1, 2),
            (0, 1), (2, 1),
            (1, 0),
        ]
        metrics = self.calc_shape_metrics(points)
        expected_metrics = {
            'surface_area': 0,
        }
        assert metrics == expected_metrics

    def test_find_multiple_colonies(self):
        #    *          *
        #   / \        / \
        #  * * *      * * *
        #   \ /        \ /
        #    *          *
        points = [
            (1, 2),
            (0, 1), (1, 1), (2, 1), (10, 1), (11, 1), (12, 1),
            (1, 0),
        ]
        metrics = self.calc_shape_metrics(points)
        expected_metrics = {
            'surface_area': 2
        }
        assert metrics == expected_metrics
