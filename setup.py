from distutils.core import setup

with open('README.md') as f:
    readme = f.read()

setup(
    name='timezonefinder',
    version='1.003',
    packages=['timezonefinder'],
    package_data={'timezonefinder': ['timezone_data.bin']},
    description='Python library to look up timezone from lat / long offline. Improved version of "pytzwhere".',
    author='J. Michelfeit',
    author_email='python@michelfe.it',
    license='MIT licence',
    url='https://github.com/MrMinimal64/timezonefinder',  # use the URL to the github repo
    download_url='https://github.com/MrMinimal64/timezonefinder/tarball/1.0',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Localization',
    ],
    long_description=readme,
    install_requires=[
        'numpy',
    ],
)
