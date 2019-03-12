import os
import re
import sys
from os.path import abspath, join, pardir, isfile

"""
required packages
numpy
six
(llvmlite, numba)


these packages have to be installed in virtual environment in use:

for testing:
pip-tools
rstcheck
pytest

for uploading:
twine

--cov-config=tox.ini

pip-tools package:
TODO write bash script for this
its important to pin requirements to get reproducible errors!
compile a new requirements file (with the latest versions)
source activate tzEnv
pip-compile --upgrade
same as?!:
pip-compile --output-file requirements.txt requirements.in
pip-compile --output-file requirements_numba.txt requirements_numba.in
only update the flask package:
pip-compile --upgrade-package flask
compile a new requirements file (with versions currently used in the virtual env )
pip-compile --generate-hashes requirements_numba.in

do NOT sync. will install ONLY the packages specified! (no more tox etc. installed!)
pip-sync

commands
tox -r to rebuild your tox virtualenvs when you've made changes to requirements setup
rstcheck *.rst
tox -r -e py36-codestyle
tox -r -e py36
tox -r -e py36-numba
"""


def get_version(package):
    """
    Return package version as listed in `__version__` in `__init__.py`.
    """
    init_py = open(join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


def set_version(new_version_number=None, old_version_number=''):
    """
    Set package version as listed in `__version__` in `__init__.py`.
    """
    if new_version_number is None:
        return ValueError

    import fileinput
    import sys

    file = join('timezonefinder', '__init__.py')

    for line in fileinput.input(file, inplace=1):
        if old_version_number in line:
            line = line.replace(old_version_number, new_version_number)
        sys.stdout.write(line)


def convert_version(new_version_input='', old_version='1.0.0'):
    new_version_input = re.search('\d\.\d\.\d+', new_version_input)

    if new_version_input is None:
        return None
    else:
        new_version_input = new_version_input.group()

    # print(new_version_input)

    split_new_version = [int(x) for x in new_version_input.split('.')]
    # print(split_new_version)
    split_old_version = [int(x) for x in old_version.split('.')]
    # print(split_old_version)

    for i in range(3):
        if split_new_version[i] > split_old_version[i]:
            break
        if split_new_version[i] < split_old_version[i]:
            return None

    return new_version_input


def routine(cmd=None, message='', option1='next', option2='exit'):
    while 1:
        print(message)

        if cmd:
            print('running command:', cmd)
            os.system(cmd)

        print('__________\nDone. Options:')
        print('1)', option1)
        print('2)', option2)
        print('anything else to repeat this step.')
        try:
            inp = int(input())

            if inp == 1:
                print('==============')
                break
            if inp == 2:
                sys.exit()

        except ValueError:
            pass
        print('================')


if __name__ == "__main__":

    print('Do you want to switch to the "dev" branch? Commit before switching branch!')
    print('1) yes, change now.')
    print('2) no, exit')
    print('anything else skip.')
    try:
        inp = int(input())
        if inp == 1:
            os.system('git checkout dev')
            print('==============')
        if inp == 2:
            sys.exit()
    except ValueError:
        pass

    # TODO run authors tests

    old_version = get_version('timezonefinder')

    print('The actual version number is:', old_version)
    print('Enter new version number:')
    version_input = None
    while 1:
        try:
            version_input = input()
        except ValueError:
            pass

        version_number = convert_version(version_input, old_version)
        if version_number is not None:
            set_version(version_number, old_version, )
            break

        print('Invalid version input. Should be of format "x.x.xxx" and higher than the old version.')

    version = get_version('timezonefinder')
    print('version number has been set to:', version)
    print('=====================')

    routine(None, 'Remember to keep helpers.py and helpers_numba.py consistent!', 'OK. Continue', 'Exit')
    routine(None, 'Are all .bin files listed in the package data in setup.py?!', 'OK. Continue', 'Exit')
    routine(None, 'Are all dependencies written in setup.py, requirements_numba.in/.txt and the Readme?',
            'OK. Continue',
            'Exit')
    routine(None, 'Remember to write a changelog now for version %s' % version, 'Done. Continue', 'Exit')
    routine(None,
            'Maybe update test routine (requirements.txt) with pip-compile!'
            ' Commands are written in the beginning of this script',
            'Done. Run tests', 'Exit')

    # print('Enter virtual env name:')
    # virtual env has to be given!
    # virt_env_name = input()
    virt_env_name = 'tzEnv'
    virt_env_act_command = 'source activate ' + virt_env_name.strip() + '; '

    print('___________')
    print('Running TESTS:')

    # routine(virt_env_act_command + "pip-compile requirements_numba.in;pip-sync",
    #      'pinning the requirements.txt and bringing virtualEnv to exactly the specified state:', 'next: build check')

    routine(virt_env_act_command + "rstcheck *.rst", 'checking syntax of all .rst files:', 'next: build check')

    # IMPORTANT: -r flag to rebuild tox virtual env
    # only when dependencies have changed!
    rebuild_flag = ''
    print('when the dependencies (in requirements.txt) have changed enter 1 (-> rebuild tox)')
    try:
        inp = int(input())
        if inp == 1:
            rebuild_flag = ' -r'
    except ValueError:
        pass

    # routine(virt_env_act_command + "tox" + rebuild_flag, 'checking syntax, codestyle and imports', 'continue')
    routine(virt_env_act_command + "tox" + rebuild_flag + " -e py36-codestyle",
            'checking syntax, codestyle and imports', 'continue')
    routine(virt_env_act_command + "tox" + rebuild_flag + " -e py36", 'build tests py3', 'continue')
    routine(virt_env_act_command + "tox" + rebuild_flag + " -e py36-numba",
            'build tests with numba installed', 'continue')

    print('Tests finished.')

    routine(None,
            'Please commit your changes, push and wait if Travis tests build successfully. '
            'Only then merge them into the master.',
            'Build successful. Publish and upload now.', 'Exit.')

    # TODO do this automatically, problem are the commit messages (often the same as changelog)
    # git commit --message
    # git push dev

    # if not in master

    # TODO ask to push in master
    # git merge ...

    # TODO switching to master

    # TODO wait for Travis to finish

    print('=================')
    print('PUBLISHING:')

    # routine("python3 setup.py sdist bdist_wheel upload", 'Uploading the package now.') # deprecated
    # new twine publishing routine:
    # https://packaging.python.org/tutorials/packaging-projects/
    routine("python3 setup.py sdist bdist_wheel", 'building the package now.')

    path = abspath(join(__file__, pardir, 'dist'))
    all_archives_this_version = [f for f in os.listdir(path) if isfile(join(path, f)) and version_number in f]
    paths2archives = [abspath(join(path, f)) for f in all_archives_this_version]
    command = "twine upload --repository-url https://test.pypi.org/legacy/ " + ' '.join(paths2archives)

    # upload all archives of this version
    routine(virt_env_act_command + command, 'testing if upload works.')

    command = "twine upload " + ' '.join(paths2archives)
    routine(virt_env_act_command + command, 'real upload to PyPI.')

    # tag erstellen
    routine(None, 'Do you want to create a git release tag?', 'Yes', 'No')

    routine("git tag -a v%s -m 'Version %s'" % (version, version), 'Creating tag', 'Continue')

    routine(None, 'Do you want to push the git release tag?', 'Yes', 'No')
    # in den master pushen
    os.system("git push --tags")

    print('______________')
    print('Publishing Done.')
    print('now run:')
    print('(only when the upload didnt work) python3 setup.py bdist_wheel upload')
    print('sudo -H pip3 install timezonefinder --upgrade')
