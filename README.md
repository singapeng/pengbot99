# pengbot99
A library and Discord bot for useful F-Zero 99 schedule info


## Setup

The files may be installed using pip. For example, from the source repository, simply run:
```
pip install .
```

You may then import the module in your Python environment.
```
>>> import pengbot99
```

You may want to use a virtual environment since pengbot99 has dependencies on third-party libraries (namely py-cord).
To create a virtual environment in a `venv` folder under the code location:

```
python -m venv venv
source venv/bin/activate
pip install .
```

Following this, you should be able to run a bot and/or import modules as above.


## Running the application

The application can be started through the `bot.py` module.
No assumption is made as to the target environment, therefore no shell script or similar is provided.
The main module implements a `__main__` function so it may be started using a Python 3.11+ executable.
```
python py/bot.py
```

## Running tests

For simplicity's sake, tests are written using Python's built-in unittest module. The tests currently shipped are minimal, only covering the dataloader module.
To run tests, we would ideally execute a test runner command sourcing tests from the `tests` folder at the root of the repository.
As there is a single test module, you may also run tests using a simple python command, i.e.:
```
> python tests/test_miniprix.py

...
----------------------------------------------------------------------
Ran 3 tests in 0.004s
OK
```

# Future improvements

- Refactor schedule manager to more elegantly manage rotations
- Bot Cogs


# References

