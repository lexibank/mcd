from setuptools import setup
import json


with open('metadata.json', encoding='utf-8') as fp:
    metadata = json.load(fp)


setup(
    name='lexibank_mcd',
    description=metadata['title'],
    license=metadata.get('license', ''),
    url=metadata.get('url', ''),
    py_modules=['lexibank_mcd'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'lexibank.dataset': [
            'mcd=lexibank_mcd:Dataset',
        ],
        'cldfbench.commands': [
            'mcd=mcdcommands',
        ]
    },
    install_requires=[
        'requests',
        'lxml',
        'attrs',
        'clldutils',
        'beautifulsoup4',
        'pylexibank>=3.4.1.dev0',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
