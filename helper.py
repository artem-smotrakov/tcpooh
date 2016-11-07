#!/usr/bin/python

# contains fuzzer configuration, parameters can be accessed as attributes
class Config:

    # read arguments returned by argparse.ArgumentParser
    def readargs(self, args):
        self.args = vars(args)

        if args.test:
            parts = args.test.split(':')
            if len(parts) == 1:
                self.args['start_test'] = int(parts[0])
                self.args['end_test'] = int(parts[0])
            elif len(parts) == 2:
                self.args['start_test'] = int(parts[0])
                if parts[1] == '' or parts[1] == 'infinite':
                    self.args['end_test'] = float('inf')
                else:
                    self.args['end_test'] = int(parts[1])
            else:
                raise Exception('Could not parse --test value, too many colons')
        else:
            self.args['start_test'] = 0
            self.args['end_test'] = float('inf')

        parts = args.ratio.split(':')
        if len(parts) == 1:
            self.args['min_ratio'] = float(parts[0])
            self.args['max_ratio'] = min_ratio
        elif len(parts) == 2:
            self.args['min_ratio'] = float(parts[0])
            self.args['max_ratio'] = float(parts[1])
        else:
            raise Exception('Could not parse --ratio value, too many colons')

    def __getattr__(self, name):
        return self.args[name]

config = Config()

def verbose(*args):
    if config.verbose:
        if len(args) == 0:
            return
        elif len(args) == 1:
            print(args[0])
        elif len(args) == 2:
            verbose_with_prefix(args[0], args[1])
        else:
            verbose_with_indent(args[0], args[1], args[2:])

def verbose_with_prefix(prefix, message):
    if config.verbose:
        print_with_prefix(prefix, message)

def verbose_with_indent(prefix, first_message, other_messages):
    if config.verbose:
        print_with_indent(prefix, first_message, other_messages)

def print_with_prefix(prefix, message):
    print('[{0:s}] {1}'.format(prefix, message))

def print_with_indent(prefix, first_message, other_messages):
    formatted_prefix = '[{0:s}] '.format(prefix)
    print('{0:s}{1}'.format(formatted_prefix, first_message))
    if len(other_messages) > 0:
        indent = ' ' * len(formatted_prefix)
        wrapper = textwrap.TextWrapper(
            initial_indent=indent, subsequent_indent=indent, width=70)
        for message in other_messages:
            print(wrapper.fill(message))
