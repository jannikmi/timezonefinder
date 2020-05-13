# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


# ATTENTION: all required packages must be configured to be installed during the online build!
# import timezonefinder  # needed for auto document


# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os
import sys

# Get the project root dir, which is the parent dir of this

cwd = os.getcwd()
project_root = os.path.dirname(cwd)

# Insert the project root dir as the first element in the PYTHONPATH.
# This ensures that the source package is importable
sys.path.insert(0, os.path.join(project_root))

import timezonefinder  # needed for auto document, ATTENTION: must then be installed during online build!

# -- Project information -----------------------------------------------------

project = 'timezonefinder'
copyright = '2016, Jannik Michelfeit'
author = 'Jannik Michelfeit'


def get_version():
    return open(os.path.join(project_root, 'VERSION')).read()


# The full version, including alpha/beta/rc tags.
release = get_version()

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',  # automatically document with docstring
    'sphinx.ext.viewcode',
    # 'sphinx.ext.intersphinx', # to auto  link to other online documentations
]

autodoc_default_options = {
    'members': '__all__',
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__',
    'show-inheritance': True,
    'inherited-members': True,
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# The reST default role (used for this markup: `text`) to use for all
# documents.
# default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
# add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
# add_module_names = False

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
# show_authors = False

# A list of ignored prefixes for module index sorting.
# modindex_common_prefix = ["multivar_horner."]

# If true, keep warnings as "system message" paragraphs in the built
# documents.
# keep_warnings = False

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# TODO https://github.com/adamchainz/django-mysql/blob/master/docs/conf.py
# -- Options for LaTeX output ------------------------------------------

# -- Options for manual page output ------------------------------------

# -- Options for Texinfo output ----------------------------------------
