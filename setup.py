#!/usr/bin/env python

from setuptools import find_packages, setup

setup(
    name='wagtail-review',
    version='0.3',
    description="Review workflow for Wagtail",
    author='Matthew Westcott',
    author_email='matthew.westcott@torchbox.com',
    url='https://github.com/wagtail/wagtail-review',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'wagtail>=7.4,<7.5',
        'swapper>=1.4,<2',
    ],
    extras_require={
        'testing': [
            'coverage>=7.15,<8',
            'pip-audit>=2.10,<3',
        ],
        'postgres': [
            'psycopg[binary]>=3.3,<4',
        ],
    },
    python_requires='>=3.12',
    project_urls={
        'Source': 'https://github.com/wagtail/wagtail-review',
    },
    license='BSD',
    long_description="An extension for Wagtail allowing pages to be submitted for review (including to non-Wagtail users) prior to publication",
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Framework :: Django',
        'Framework :: Wagtail',
        'Framework :: Wagtail :: 7',
    ],
)
