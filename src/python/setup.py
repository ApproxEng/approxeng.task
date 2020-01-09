__author__ = 'tom'

from setuptools import setup, find_packages

setup(
    name='approxeng.task',
    version='0.0.1',
    description='Simple Python task framework for robots',
    classifiers=['Programming Language :: Python :: 3.7'],
    url='https://github.com/ApproxEng/approxeng.task/',
    author='Tom Oinn',
    author_email='tomoinn@gmail.com',
    license='ASL2.0',
    packages=find_packages(),
    install_requires=['cachetools==4.0.0'],
    include_package_data=True,
    dependency_links=[],
    zip_safe=False)
