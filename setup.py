from setuptools import setup,find_packages

setup(
  name = 'hftools',
  version = '0.0.1',
  packages = find_packages(),
  author = 'Lukas Heinrich',
  author_email = 'lukas.heinrich@cern.ch',
  description = 'simple tools to extract to do post-processing on HistFactory configurations / workspaces (e.g. extract data for HepData, simple stacked plots etc.)',
)
