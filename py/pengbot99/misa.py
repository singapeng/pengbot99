import csv
import random


def load_quotes(path):
    """Loads Misa quotes from file."""
    name = "misa"
    quotes_path = "{0}/{1}.csv".format(path, name)
    with open(quotes_path, newline="") as fd:
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
