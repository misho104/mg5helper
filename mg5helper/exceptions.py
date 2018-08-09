class MG5BinNotFoundError(FileNotFoundError):
    def __init__(self):
        self.message = 'MG5 executable is not found. Set by hand or use ENV["HEP_MG5"].'


class MG5OutputNotFoundError(FileNotFoundError):
    def __init__(self, dir_name):
        self.message = 'Directory {} not found.'.format(dir_name)


class AbsolutePathSpecifiedError(ValueError):
    def __init__(self):
        self.message = 'Output directory must be a relative path for safety.'


class OutputNotPreparedError(FileNotFoundError):
    def __init__(self):
        self.message = 'Output directory is not found. Forget "output"?'
