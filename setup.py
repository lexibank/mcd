from setuptools import setup, find_packages
import json


with open('metadata.json', encoding='utf-8') as fp:
    metadata = json.load(fp)


setup(
    name='lexibank_mcd',
    description=metadata['title'],
    license=metadata.get('license', ''),
    url=metadata.get('url', ''),
    py_modules=['lexibank_mcd'],
    packages=find_packages(where='.'),
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'lexibank.dataset': [
            'mcd=lexibank_mcd:Dataset',
        ],
    },
    install_requires=[
        'termcolor',
        'requests',
        'lxml',
        'attrs',
        'clldutils',
        'beautifulsoup4',
        'pylexibank>=3.4.1.dev0',
        'pyetymdict',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
