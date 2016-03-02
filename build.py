from pybuilder.core import use_plugin, init, Author


use_plugin("python.core")
use_plugin("copy_resources")
use_plugin("filter_resources")
use_plugin("python.unittest")
use_plugin("python.install_dependencies")
use_plugin("python.flake8")
#use_plugin("python.coverage")
use_plugin("python.distutils")


name = "mScale"
url = 'https://github.com/sushilks/mScale'
description = "Please visit {url}".format(url=url)

authors = [Author('Sushil Singh', 'sushilks@gmail.com')]
license = 'Apache 2.0'
summary = "A scale test infra using mesos and marathon."
version = '0.1.0'

default_task = "publish"


@init
def set_properties(project):
    project.build_depends_on('mockito')
    project.build_depends_on('pyzmq')
    project.build_depends_on('marathon')
    project.build_depends_on('netifaces')
    project.build_depends_on('logging')

    project.set_property('copy_resources_target', '$dir_dist')
    project.get_property('copy_resources_glob').append('LICENSE')
    project.get_property('copy_resources_glob').append('src/main/data/*')
#    project.get_property('copy_resources_glob').append('src/main/data/z')

#    project.include_file(name, 'LICENSE')
#    project.include_file(name, 'config/*.ini')
#    project.include_directory('src/main/data', ['*.ini'])
    project.set_property('flake8_verbose_output', True)
    project.set_property('flake8_break_build', True)
    project.set_property('flake8_include_test_sources', True)

    project.get_property('distutils_commands').append('bdist_wheel')
    project.set_property('distutils_classifiers', [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Software Development :: Testing',
        'Topic :: Software Development :: Quality Assurance'])

    pass
