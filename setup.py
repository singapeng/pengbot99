#!/usr/bin/env python
"""The setup script."""
from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

name = 'pengbot99'
author = 'Pengui'
author_email = 'pengui@gmail.com'
description = 'F-Zero 99 Schedule Discord Bot'
license = 'MIT'
long_description = readme
url = 'https://undefined'

source_dir = 'py'

requirements = [
        'py-cord>=2.5',
    ]
setup_requirements = []
test_requirements = []

setup(
    author=author,
    author_email=author_email,
    python_requires='>=3.11',
    classifiers=[
        'License :: MIT',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.11',
    ],
    description=description,
    entry_points={},
    install_requires=requirements,
    license=license,
    long_description=long_description,
    long_description_content_type='text/markdown',
    include_package_data=True,
    name=name,
    packages=find_packages(source_dir),
    package_dir={'': source_dir},
    setup_requires=setup_requirements,
    tests_require=test_requirements,
    url=url,
    zip_safe=False
)
