from setuptools import setup,find_packages

setup(
    name = 'hftools',
    version = '0.0.3',
    packages = find_packages(),
    author = 'Lukas Heinrich',
    author_email = 'lukas.heinrich@cern.ch',
    description = 'simple tools to extract to do post-processing on HistFactory configurations / workspaces (e.g. extract data for HepData, simple stacked plots etc.)',
    install_requires = [
        'click',
        'pyyaml',
        'numpy',
        'brewer2mpl',
    ],
    entry_points = {
        'console_scripts': [
            'hfquickplot = hftools.plotting.quickplot:toplevel',
            'hfhdrootcnv = hftools.hepdata.rootcnv.cli:converter'
      ]
    },
)
