
from arpeggio import (
    RegExMatch,
    ParserPython,
    OneOrMore,
)



# parsing expression grammar for agents
def agent_type(): return RegExMatch(r'[a-zA-Z0-9.\-\_]+')
def number(): return RegExMatch(r'[0-9]+')
def specification(): return agent_type, number
def rule(): return OneOrMore(specification)
agent_parser = ParserPython(rule)
def parse_agents_string(agents_string):
    all_agents = agent_parser.parse(agents_string)
    agents_config = []
    for idx, agent_specs in enumerate(all_agents):
        agents_config.append(make_agent_config(agent_specs))
    return agents_config

def make_dir(out_dir):
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

class ExperimentControl():
    def add_arguments():
        parser = argparse.ArgumentParser(description='chemotaxis control')
        parser.add_argument(
            '--agents', '-a',
            type=str,
            nargs='+',
            default='"minimal 1"',
            help='A list of agent types and numbers in the format "agent_type1 number1 agent_type2 number2"')
        parser.add_argument(
            '--environment', '-v',
            type=str,
            default='exponential',
            help='the environment type ("linear" or "exponential")')
        parser.add_argument(
            '--time', '-t',
            type=int,
            default=10,
            help='total simulation time, in seconds')
        parser.add_argument(
            '--emit', '-m',
            type=int,
            default=1,
            help='emit interval, in seconds')
        parser.add_argument(
            '--experiment', '-e',
            type=str,
            default=None,
            help='preconfigured experiments')
        return parser.parse_args()


    def execute(out_dir):

        args = add_arguments()

        if args.experiment:
            # get a preset experiment
            # make a directory for this experiment
            experiment_name = str(args.experiment)
            control_out_dir = os.path.join(out_dir, experiment_name)
            make_dir(control_out_dir)

            experiment_config = preset_experiments[experiment_name]
            agents_config = experiment_config['agents_config']
            environment_config = experiment_config['environment_config']
            simulation_settings = experiment_config['simulation_settings']

        else:
            # make a directory for this experiment
            experiment_name = '_'.join(args.agents)
            control_out_dir = os.path.join(out_dir, experiment_name)
            make_dir(control_out_dir)

            # configure the agents
            agents_config = []
            if args.agents:
                agents_string = ' '.join(args.agents)
                agents_config = parse_agents_string(agents_string)

            # configure the environment
            if args.environment == 'linear':
                env_config = get_linear_env_config()
            else:
                env_config = get_exponential_env_config()
            environment_config = {
                'type': DEFAULT_ENVIRONMENT_TYPE,
                'config': env_config,
            }

            # configure the simulation
            total_time = args.time
            emit_step = args.emit
            simulation_settings = {
                'total_time': total_time,
                'emit_step': emit_step,
            }

        # simulate
        data = run_chemotaxis_experiment(
            agents_config=agents_config,
            environment_config=environment_config,
            simulation_settings=simulation_settings,
        )

        return data
