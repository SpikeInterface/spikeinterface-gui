# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os

on_rtd = os.environ.get('READTHEDOCS') == 'True'
if on_rtd:
    # need a git config
    os.system('git config --global user.email "rtd@example.com"')
    os.system('git config --global user.name "RTD Almighty"')


project = 'SpikeInterface-GUI'
copyright = '2022-2025, SpikeInterface Team'
author = 'SpikeInterface Team'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
try:
    import sphinx_rtd_theme

    html_theme = "sphinx_rtd_theme"
except ImportError:
    print("RTD theme not installed, using default")
    html_theme = 'alabaster'

html_static_path = ['_static']

intersphinx_mapping = {
    "spikeinterface": ("https://spikeinterface.readthedocs.io/en/stable/", None),
}
