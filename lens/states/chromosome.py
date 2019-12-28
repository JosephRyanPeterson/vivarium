import random

def first(l):
    if l:
        return l[0]

def first_value(d):
    if d:
        return d[list(d.keys())[0]]

def traverse(tree, key, f):
    node = tree[key]
    return f(node, [traverse(tree, child, f) for child in node.children])

class Datum(object):
    schema = {}

    def __init__(self, config, default):
        self.keys = list(set(list(config.keys()) + list(default.keys()))) # a dance
        for key in self.keys:
            value = config.get(key, default[key])
            if value and key in self.schema:
                realize = self.schema[key]
                if isinstance(value, list):
                    value = [realize(item) for item in value]
                elif isinstance(value, dict):
                    value = {inner: realize(item) for inner, item in value.items()}
                else:
                    value = realize(item)
            setattr(self, key, value)

    def to_dict(self):
        to = {}
        for key in self.keys:
            value = getattr(self, key)
            if isinstance(value, Datum):
                value = value.to_dict()
            elif value and isinstance(value, list) and isinstance(first(value), Datum):
                value = [datum.to_dict() for datum in value]
            elif value and isinstance(value, dict) and isinstance(first_value(value), Datum):
                value = {inner: datum.to_dict() for inner, datum in value.items()}
            to[key] = value
        return to

class Operon(Datum):
    defaults = {
        'id': '',
        'position': 0,
        'direction': 1,
        'length': 0,
        'genes': []}

    def __init__(self, config):
        super(Operon, self).__init__(config, self.defaults)

class Domain(Datum):
    defaults = {
        'id': 0,
        'lead': 0,
        'lag': 0,
        'children': []}

    def strand_position(self, strand, lead=0, lag=0):
        return self.lead + lead if strand == '+' else self.lag + lag

    def random_child(self):
        return random.choice(self.children)

    def __init__(self, config):
        super(Domain, self).__init__(config, self.defaults)

class TranscriptionFactor(Datum):
    defaults = {
        'protein': '',
        'domain': 0,
        'state': 0, # off
        'operon': ''}

    def __init__(self, config):
        super(TranscriptionFactor, self).__init__(config, self.defaults)

class Rnap(Datum):
    defaults = {
        'operon': '',
        'domain': 0,
        'position': 0}

    def __init__(self, config):
        super(Rnap, self).__init__(config, self.defaults)

class Chromosome(Datum):
    schema = {
        'domains': Domain,
        'operons': Operon,
        'transcription_factors': TranscriptionFactor,
        'rnaps': Rnap}

    defaults = {
        'sequence': {
            '+': '',
            '-': ''},
        'domains': {},
        'operons': {},
        'transcription_factors': {},
        'rnaps': []}

    def initiate_replication(self):
        leaves = [leaf for leaf in self.domains.values() if not leaf.children]
        next_id = max([leaf.id for leaf in leaves]) + 1
        for leaf in leaves:
            for child in [0, 1]:
                domain = Domain({'id': next_id + child})
                self.domains[domain.id] = domain
            leaf.children = [next_id, next_id + 1]
            next_id += 2

    def advance_replisomes(self, distances):
        '''
        distances is a dictionary of domain ids to tuples of how far each strand advances
        of the form (lead, lag)
        '''
        # TODO: stochastically transfer rnap and tf to new domains

        for domain_key, distance in distances.items():
            domain = self.domains[domain_key]
            lead, lag = distances[domain_key]

            for tf in self.transcription_factors.values():
                if tf.domain == domain_key:
                    strand, position = self.operons[tf.operon].position
                    if position >= domain.strand_position(strand) and position < domain.strand_position(strand, lead, lag):
                        tf.domain = domain.random_child()

            for rnap in self.rnaps:
                if rnap.domain == domain_key:
                    operon = self.operons[rnap.operon]
                    strand, position = operon.position
                    position += rnap.position * operon.direction
                    if position >= domain.strand_position(strand) and position < domain.strand_position(strand, lead, lag):
                        rnap.domain = domain.random_child()

            domain.lead += lead
            domain.lag += lag

    def terminate_replication(self):
        root = min(self.domains.keys())
        children = self.domains[root].children
        divided = [
            traverse(
                self.domains,
                child,
                self.divide_chromosome)
            for child in children]

        return [Chromosome(fork) for fork in divided]

    def divide_chromosome(self, domain, division):
        if not division:
            division = {
                'sequence': self.sequence,
                'domains': {domain.id: domain.to_dict()},
                'operons': {id: operon.to_dict() for id, operon in self.operons.items()},
                'transcription_factors': {
                    operon: tf.to_dict()
                    for operon, tf in self.transcription_factors.items()
                    if tf.domain == domain},
                'rnaps': [
                    rnap.to_dict()
                    for rnap in self.rnaps
                    if rnap.domain == domain]}

        else:
            division.domains[domain.id] = domain
            for operon, tf in self.transcription_factors.items():
                if tf.domain == domain:
                    division.transcription_factors[operon] = tf.to_dict()
            for rnap in self.rnaps.items():
                if rnap.domain == domain:
                    division.rnaps.append(rnap.to_dict())

        return division

    def __init__(self, config):
        super(Chromosome, self).__init__(config, self.defaults)


def test_chromosome():
    config = {
        'sequence': {
            '+': 'ATACGGCACGTG',
            '-': 'ACCGTCAACTTA'},
        'domains': {
            0: {
                'id': 0,
                'lead': 0,
                'lag': 0,
                'children': []}},
        'operons': {
            'A': {
                'id': 'A',
                'position': ('+', 0),
                'direction': 1,
                'length': 9,
                'genes': ['A', 'Z']},
            'B': {
                'id': 'B',
                'position': ('-', 11),
                'direction': -1,
                'length': 3,
                'genes': ['B']}},
        'transcription_factors': {
            'A': {
                'protein': 'B',
                'domain': 0,
                'state': 1, # on
                'operon': 'A'}},
        'rnaps': [
            {
                'operon': 'A',
                'domain': 0,
                'position': 3},
            {
                'operon': 'A',
                'domain': 0,
                'position': 6},
            {
                'operon': 'B',
                'domain': 0,
                'position': 11}]}

    chromosome = Chromosome(config)
    print(chromosome.transcription_factors['A'].state)
    print(chromosome.to_dict())

    assert chromosome.to_dict() == config

    chromosome.initiate_replication()

    print(chromosome.to_dict()['domains'])
    assert len(chromosome.domains) == 3

    chromosome.advance_replisomes({0: (5, 7)})
    print('replisomes:')
    print(chromosome.to_dict())

    children = chromosome.terminate_replication()
    print('termination:')
    print([child.to_dict() for child in children])


if __name__ == '__main__':
    test_chromosome()
