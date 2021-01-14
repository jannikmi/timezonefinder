import os
import sys


PACKAGE = 'timezonefinder'
VERSION_FILE = 'VERSION'
VIRT_ENVS = ['APIenv']
VIRT_ENV_COMMAND = '. ~/miniconda3/etc/profile.d/conda.sh; conda activate {virt_env}; '
PY_VERSION_IDS = ['36', '37', '38']  # the supported python versions to create wheels for
PYTHON_TAG = '.'.join([f'py{v}' for v in PY_VERSION_IDS])

if __name__ == "__main__":

    print('building now:')
    # routine("python3 setup.py sdist bdist_wheel upload", 'Uploading the package now.') # deprecated
    # new twine publishing routine:
    # https://packaging.python.org/tutorials/packaging-projects/
    # delete the build folder before to get a fresh build
    # TODO do not remove dist in the future
    os.system('rm -r -f build')
    os.system('rm -r -f dist')

    build_cmd = f"python setup.py sdist bdist_wheel --python-tag {PYTHON_TAG}"
    os.system(build_cmd)

    # in all specified virtual environments
    for virt_env in VIRT_ENVS:
        virt_env_cmd = VIRT_ENV_COMMAND.format(virt_env=virt_env)
        install_cmd = f'{virt_env_cmd} python setup.py install'
        os.system(install_cmd)

    # routine(build_cmd, 'building the package now.',
    #         'build done. check the included files! installing package in virtual environment next.')
    # routine(install_cmd)
    os.system('rm -r -f build')
