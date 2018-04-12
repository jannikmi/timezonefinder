
import os
import sys
import re


def get_version(package):
    """
    Return package version as listed in `__version__` in `__init__.py`.
    """
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search("__version__ = ['\"]([^'\"]+)['\"]", init_py).group(1)


def set_version(new_version_number=None, old_version_number=''):
    """
    Set package version as listed in `__version__` in `__init__.py`.
    """
    if new_version_number is None:
        return ValueError

    import fileinput
    import sys

    file = os.path.join('timezonefinder', '__init__.py')

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


def routine(command=None, message='', option1='next', option2='exit'):
    while 1:
        print(message)

        if command:
            os.system(command)

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

    routine(None, 'Is the newest OSM data version in use? Does the readme show correct data version?', 'OK. Continue', 'Exit')
    routine(None, 'Remember to keep helpers.py and helpers_numba.py consistent!', 'OK. Continue', 'Exit')
    routine(None, 'Are all .bin files listed in the package data in setup.py?!', 'OK. Continue', 'Exit')
    routine(None, 'Remember to write a changelog now for version %s' % version, 'Done. Run tests', 'Exit')

    print('Enter virtual env name or press enter for running without virtual env:')
    virt_env_name = None
    virt_env_name = input()

    if virt_env_name == '':
        virt_env_act_command = ''
    else:
        virt_env_act_command = 'source activate ' + virt_env_name.strip() + ';'

    print('___________')
    print('Running TESTS:')


    routine(virt_env_act_command+"rstcheck *.rst", 'checking syntax of all .rst files:', 'next: build check')

    routine(virt_env_act_command+"tox -e py{27,35}-codestyle", 'checking syntax, codestyle and imports', 'continue')

    routine(virt_env_act_command+"tox -e py27", 'checking if package is building with tox', 'continue')

    print('Tests finished.')

    routine(None,
            'Please commit your changes, push and then merge them into the master. Then wait if Travis tests build successfully.',
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

    routine("python3 setup.py sdist bdist_wheel upload", 'Uploading the package now.')

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
