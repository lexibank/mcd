"""

"""
import collections

from termcolor import colored
from clldutils.clilib import Table, add_format
from clldutils.markup import MarkdownLink

from lexibank_mcd import Dataset


def register(parser):
    parser.add_argument('cset')
    add_format(parser, 'simple')


def unmarkdown(s):
    return MarkdownLink.replace(s, lambda mdl: mdl.label).replace('&ast;', '*')


def run(args):
    cldf = Dataset().cldf_reader()

    langs = {l['ID']: l for l in cldf.iter_rows('LanguageTable')}
    forms = {l['ID']: l for l in cldf.iter_rows('FormTable')}
    glosses = {l['ID']: l for l in cldf.iter_rows('ParameterTable')}

    for cs in cldf.iter_rows('CognatesetTable'):
        if cs['ID'] == args.cset or cs['Name'] == args.cset or cs['Name'] == args.cset.replace('*', ''):
            print('\n{}\t{}\t{}\n'.format(
                colored(langs[cs['Language_ID']]['Name'] + (' (?)' if cs['doubt'] else ''), 'blue', attrs=['bold']),
                colored('*' + forms[cs['Form_ID']]['Value'].replace(' or ', ' or *'), 'red', attrs=['bold']),
                colored(glosses[forms[cs['Form_ID']]['Parameter_ID']]['Name'], 'black')
            ))
            break
    else:
        raise ValueError

    with Table(args, 'Language', 'Form', 'Meaning', 'Comment', 'Source') as witnesses:
        for cog in cldf.iter_rows('CognateTable'):
            if cog['Cognateset_ID'] == cs['ID']:
                form = forms[cog['Form_ID']]
                is_proto = langs[form['Language_ID']]['is_proto']
                if form['Language_ID'] != cs['Language_ID']:
                    witnesses.append([
                        colored(langs[form['Language_ID']]['Name'], 'red' if is_proto else 'green'),
                        colored(('*' if is_proto else '') + form['Value'], 'red' if is_proto else 'blue'),
                        glosses[form['Parameter_ID']]['Name'],
                        unmarkdown(form['Comment'] or ''),
                        '; '.join(cldf.sources[src.split('[')[0]].refkey(year_brackets=None) for src in form['Source'] + cog['Source']),
                    ])

    cf_members = collections.defaultdict(list)
    for cfitem in cldf.iter_rows('cfitems.csv'):
        cf_members[cfitem['Cfset_ID']].append(cfitem)

    for cf in cldf.iter_rows('cf.csv'):
        if cf['Cognateset_ID'] == cs['ID']:
            print('\n--- {} ---'.format(cf['Name']))
            with Table(args, 'Language', 'Form', 'Meaning', 'Source') as witnesses:
                for cfitem in cf_members[cf['ID']]:
                    form = forms[cfitem['Form_ID']]
                    if form['Language_ID'] != cs['Language_ID']:
                        witnesses.append([
                            langs[form['Language_ID']]['Name'],
                            form['Value'],
                            glosses[form['Parameter_ID']]['Name'],
                            cldf.sources[cfitem['Source'][0].split('[')[0]].refkey(year_brackets=None) if cfitem['Source'] else ''
                        ])
            if cf['Comment']:
                print(unmarkdown(cf['Comment']))
    if cs['Comment']:
        print('\n{}'.format(unmarkdown(cs['Comment'])))
