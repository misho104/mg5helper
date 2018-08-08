#!env python
from setuptools import setup
import ast
import pathlib
import re


with (pathlib.Path('mg5helper') / '__init__.py').open('rb') as f:
    version_match = re.search(r'__version__\s+=\s+(.*)', f.read().decode('utf-8'))
    version = str(ast.literal_eval(version_match.group(1))) if version_match else '0.0.0'

setup(
    name='mg5helper',
    version=version,
    author='Sho Iwamoto / Misho',
    author_email='webmaster@misho-web.com',
    url='https://github.com/misho104/mg5helper',
    description='A wrapper module of MadGraph5.',
    python_requires='>=3.4',
    license='MIT',
    packages=['mg5helper'],
    zip_safe=True,
    package_data={
        'mg5helper': [
        ]},
    install_requires=[
        'typing;python_version<"3.5"',
    ],
    tests_require=['nose', 'coverage', 'mypy', 'flake8'],
    test_suite='nose.collector',
)
