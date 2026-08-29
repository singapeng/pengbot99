import csv
import random

# local imports
from pengbot99 import utils


def load_quotes(path):
    """Loads Misa quotes from file, or from the packaged copy if path is None."""
    with utils.open_data_file(path, "misa.csv", newline="") as fd:
        reader = csv.reader(fd, delimiter=";")
        quotes = list(reader)
    return quotes


class Quotes(object):
    def __init__(self, path):
        super().__init__()
        self.quotes = load_quotes(path)

    def misa(self):
        response = random.choice(self.quotes)
        if response:
            return 'Misa says: "*{0}*"'.format(response[0])
