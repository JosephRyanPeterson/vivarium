from __future__ import absolute_import, division, print_function

import argparse
import csv
import os

from vivarium.plots.multibody_physics import (
    plot_snapshots,
    plot_tags,
)
from vivarium.core.composition import plot_agents_multigen
from vivarium.core.emitter import (
    get_atlas_client,
    get_local_client,
    data_from_database,
    SECRETS_PATH,
    timeseries_from_data,
    path_timeseries_from_embedded_timeseries,
)
from vivarium.plots.colonies import plot_colony_metrics


OUT_DIR = 'out'


class Analyzer:

    def __init__(
        self,
        snapshots_config=None,
        tags_config=None,
        timeseries_config=None,
    ):
        self.parser = self._get_parser()
        if snapshots_config is None:
            snapshots_config = {}
        if tags_config is None:
            tags_config = {}
        if timeseries_config is None:
            timeseries_config = {}
        self.snapshots_config = snapshots_config
        self.tags_config = tags_config
        self.timeseries_config = timeseries_config

    def run(self):
        args = self.parser.parse_args()
        self.plot(args)

    def get_data(self, args):
        if args.atlas:
            client = get_atlas_client(SECRETS_PATH)
        else:
            client = get_local_client(
                args.host, args.port, args.database_name)
        data, environment_config = data_from_database(
            args.experiment_id, client)
        del data[0]
        return data, environment_config

    def plot_snapshots(self, data, environment_config, out_dir):
        agents = {
            time: timepoint['agents']
            for time, timepoint in data.items()
        }
        fields = {
            time: timepoint['fields']
            for time, timepoint in data.items()
        }
        snapshots_data = {
            'agents': agents,
            'fields': fields,
            'config': environment_config,
        }
        plot_config = {
            'out_dir': out_dir,
        }
        plot_config.update(self.snapshots_config)
        plot_snapshots(snapshots_data, plot_config)

    def plot_tags(self, data, environment_config, tags_path, out_dir):
        agents = {
            time: timepoint['agents']
            for time, timepoint in data.items()
        }
        fields = {
            time: timepoint['fields']
            for time, timepoint in data.items()
        }
        with open(tags_path, 'r') as f:
            reader = csv.reader(f)
            molecules = [
                tuple(path) for path in reader
            ]
        tags_data = {
            'agents': agents,
            'config': environment_config,
        }
        plot_config = {
            'out_dir': out_dir,
            'tagged_molecules': molecules,
        }
        plot_config.update(self.tags_config)
        plot_tags(tags_data, plot_config)

    def plot_timeseries(self, data, out_dir):
        plot_settings = {
            'agents_key': 'agents',
            'title_size': 10,
            'tick_label_size': 10,
        }
        plot_settings.update(self.timeseries_config)
        plot_agents_multigen(data, plot_settings, out_dir)

    def plot_colony_metrics(self, data, out_dir):
        embedded_ts = timeseries_from_data(data)
        colony_metrics_ts = embedded_ts['colony_global']
        colony_metrics_ts['time'] = embedded_ts['time']
        path_ts = path_timeseries_from_embedded_timeseries(
            colony_metrics_ts)
        fig = plot_colony_metrics(path_ts)
        fig.savefig(os.path.join(out_dir, 'colonies'))

    def plot(self, args):
        data, environment_config = self.get_data(args)
        out_dir = os.path.join(OUT_DIR, args.experiment_id)
        if os.path.exists(out_dir):
            if not args.force:
                raise IOError('Directory {} already exists'.format(out_dir))
        else:
            os.makedirs(out_dir)

        if args.snapshots:
            self.plot_snapshots(data, environment_config, out_dir)
        if args.tags is not None:
            self.plot_tags(
                data, environment_config, args.tags, out_dir)
        if args.timeseries:
            self.plot_timeseries(data, out_dir)
        if args.colony_metrics:
            self.plot_colony_metrics(data, out_dir)

    def _get_parser(self):
        parser = argparse.ArgumentParser()
        parser.add_argument(
            'experiment_id',
            help='Experiment ID as recorded in the database',
        )
        parser.add_argument(
            '--snapshots', '-s',
            action='store_true',
            default=False,
            help='Plot snapshots',
        )
        parser.add_argument(
            '--tags', '-g',
            default=None,
            help=(
                'A path to a CSV file that lists the tagged molecules to '
                'plot. The first column should contain the name of the store '
                'under each agent boundary where the molecule is reported, '
                'and the second column should contain the name of the '
                'molecule. Setting this parameter causes a plot of the tagged '
                'molecules to be produced.'
            ),
        )
        parser.add_argument(
            '--timeseries', '-t',
            action='store_true',
            default=False,
            help='Generate line plot for each variable over time',
        )
        parser.add_argument(
            '--colony_metrics', '-c',
            action='store_true',
            default=False,
            help='Plot colony metrics',
        )
        parser.add_argument(
            '--force', '-f',
            action='store_true',
            default=False,
            help=(
                'Write plots even if output directory already exists. This '
                'could overwrite your existing plots'
            ),
        )
        parser.add_argument(
            '--atlas', '-a',
            action='store_true',
            default=False,
            help=(
                'Read data from an mongoDB Atlas instead of a local mongoDB. '
                'Credentials, cluster subdomain, and database name should be '
                'specified in {}.'.format(SECRETS_PATH)
            )
        )
        parser.add_argument(
            '--port', '-p',
            default=27017,
            type=int,
            help=(
                'Port at which to access local mongoDB instance. '
                'Defaults to "27017".'
            ),
        )
        parser.add_argument(
            '--host', '-o',
            default='localhost',
            type=str,
            help=(
                'Host at which to access local mongoDB instance. '
                'Defaults to "localhost".'
            ),
        )
        parser.add_argument(
            '--database_name', '-d',
            default='simulations',
            type=str,
            help=(
                'Name of database on local mongoDB instance to read from. '
                'Defaults to "simulations".'
            )
        )
        return parser


if __name__ == '__main__':
    analyzer = Analyzer()
    analyzer.run()
