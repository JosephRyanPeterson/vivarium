"""
==========================================
Process and Compartment Classes
==========================================
"""

from __future__ import absolute_import, division, print_function

import copy

import numpy as np

from vivarium.library.units import Quantity
from vivarium.core.registry import process_registry, serializer_registry
from vivarium.library.dict_utils import deep_merge

DEFAULT_TIME_STEP = 1.0



def serialize_dictionary(d):
    serialized = {}
    for key, value in d.items():
        if isinstance(key, tuple):
            key = str(key)

        if isinstance(value, dict):
            serialized[key] = serialize_dictionary(value)
        elif isinstance(value, np.ndarray):
            serialized[key] = serializer_registry.access('numpy').serialize(value)
        elif isinstance(value, Quantity):
            serialized[key] = serializer_registry.access('units').serialize(value)
        elif callable(value):
            serialized[key] = serializer_registry.access('function').serialize(value)
        elif isinstance(value, Process):
            serialized[key] = serialize_dictionary(serializer_registry.access('process').serialize(value))
        elif isinstance(value, Generator):
            serialized[key] = serialize_dictionary(serializer_registry.access('compartment').serialize(value))
        else:
            serialized[key] = value
    return serialized


def assoc_in(d, path, value):
    if path:
        return dict(d, **{path[0]: assoc_in(d.get(path[0], {}), path[1:], value)})
    else:
        return value


def generate_derivers(processes, topology):
    deriver_processes = {}
    deriver_topology = {}
    for process_key, node in processes.items():
        subtopology = topology[process_key]
        if isinstance(node, Process):
            for deriver_key, config in node.derivers().items():
                if deriver_key not in deriver_processes:
                    # generate deriver process
                    deriver_config = config.get('config', {})
                    generate = config['deriver']
                    if isinstance(generate, str):
                        generate = process_registry.access(generate)

                    deriver = generate(deriver_config)
                    deriver_processes[deriver_key] = deriver

                    # generate deriver topology
                    deriver_topology[deriver_key] = {}
                    for target, source in config.get('port_mapping', {}).items():
                        path = subtopology[source]
                        deriver_topology[deriver_key][target] = path
        else:
            subderivers = generate_derivers(node, subtopology)
            deriver_processes[process_key] = subderivers['processes']
            deriver_topology[process_key] = subderivers['topology']
    return {
        'processes': deriver_processes,
        'topology': deriver_topology}


class Generator(object):
    """Generator parent class

    All :term:`compartment` classes must inherit from this class.
    """
    def __init__(self, config):
        self.config = config

    def generate_processes(self, config):
        """Generate processes dictionary

        Every subclass must override this method.

        Arguments:
            config (dict): A dictionary of configuration options. All
                subclass implementation must accept this parameter, but
                some may ignore it.

        Returns:
            dict: Subclass implementations must return a dictionary
            mapping process names to instantiated and configured process
            objects.
        """
        return {}

    def generate_topology(self, config):
        """Generate topology dictionary

        Every subclass must override this method.

        Arguments:
            config (dict): A dictionary of configuration options. All
                subclass implementation must accept this parameter, but
                some may ignore it.

        Returns:
            dict: Subclass implementations must return a :term:`topology`
            dictionary.
        """
        return {}

    def generate(self, config=None, path=tuple()):
        '''Generate processes and topology dictionaries for the compartment

        Arguments:
            config (dict): Updates values in the configuration declared
                in the constructor
            path (tuple): Tuple with ('path', 'to', 'level') associates
                the processes and topology at this level

        Returns:
            dict: Dictionary with two keys: ``processes``, which has a
            value of a processes dictionary, and ``topology``, which has
            a value of a topology dictionary. Both are suitable to be
            passed to the constructor for
            :py:class:`vivarium.core.experiment.Experiment`.
        '''

        # merge config with self.config
        if config is None:
            config = self.config
        else:
            default = copy.deepcopy(self.config)
            config = deep_merge(default, config)

        processes = self.generate_processes(config)
        topology = self.generate_topology(config)

        # add derivers
        derivers = generate_derivers(processes, topology)
        processes = deep_merge(derivers['processes'], processes)
        topology = deep_merge(derivers['topology'], topology)

        return {
            'processes': assoc_in({}, path, processes),
            'topology': assoc_in({}, path, topology)}

    def or_default(self, parameters, key):
        return parameters.get(key, self.defaults[key])

    def get_parameters(self):
        network = self.generate({})
        processes = network['processes']
        return {
            process_id: process.parameters
            for process_id, process in processes.items()}


class Process(Generator):

    name = 'process'
    defaults = {}

    def __init__(self, parameters=None):
        if parameters is None:
             parameters = {}
        self.parameters = copy.deepcopy(self.defaults)
        deep_merge(self.parameters, parameters)

        # register process repository
        process_registry.register(self.name, type(self))

    def generate_processes(self, config):
        return {'process': self}

    def generate_topology(self, config):
        ports_schema = self.ports_schema()
        topology = config.get('topology', {})
        return {
            'process': {
                port: topology.get(port, (port,)) for port in ports_schema().keys()}}

    def ports(self):
        ports_schema = self.ports_schema()
        return {
            port: list(states.keys())
            for port, states in ports_schema.items()}

    def local_timestep(self):
        '''
        Returns the favored timestep for this process.
        Meant to be overridden in subclasses, unless 1.0 is a happy value.
        '''
        return self.parameters.get('time_step', DEFAULT_TIME_STEP)

    def default_state(self):
        schema = self.ports_schema()
        state = {}
        for port, states in schema.items():
            for key, value in states.items():
                if '_default' in value:
                    if port not in state:
                        state[port] = {}
                    state[port][key] = value['_default']
        return state

    def is_deriver(self):
        return False

    def derivers(self):
        return {}

    def pull_data(self):
        return {}

    def ports_schema(self):
        '''
        ports_schema returns a dictionary that declares which states are expected by the processes,
        and how each state will behave.

        state keys can be assigned properties through schema_keys declared in Store:
            '_default'
            '_updater'
            '_divider'
            '_value'
            '_properties'
            '_emit'
            '_serializer'
        '''
        return {}

    def or_default(self, parameters, key):
        return parameters.get(key, self.defaults[key])

    def derive_defaults(self, original_key, derived_key, f):
        source = self.parameters.get(original_key)
        self.parameters[derived_key] = f(source)
        return self.parameters[derived_key]

    def next_update(self, timestep, states):
        '''
        Find the next update given the current states this process cares about.
        This is the main function a new process would override.'''

        return {
            port: {}
            for port, values in self.ports.items()}


class Deriver(Process):
    def is_deriver(self):
        return True
