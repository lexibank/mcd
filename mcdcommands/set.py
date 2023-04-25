"""

"""
import collections

from clldutils.clilib import Table, add_format
from clldutils.markup import MarkdownLink

from lexibank_mcd import Dataset


def register(parser):
    parser.add_argument('cset_id', type=int)
    add_format(parser, 'simple')


def unmarkdown(s):
    return MarkdownLink.replace(s, lambda mdl: mdl.label).replace('&ast;', '*')


def run(args):
    cldf = Dataset().cldf_reader()

    langs = {l['ID']: l for l in cldf.iter_rows('LanguageTable')}
    forms = {l['ID']: l for l in cldf.iter_rows('FormTable')}
    glosses = {l['ID']: l for l in cldf.iter_rows('ParameterTable')}

    for cs in cldf.iter_rows('CognatesetTable'):
        if cs['ID'] == str(args.cset_id):
            print('{}\t*{}\t{}\n'.format(
                langs[cs['Language_ID']]['Name'],
                forms[cs['Form_ID']]['Form'].replace(' or ', ' or *'),
                glosses[forms[cs['Form_ID']]['Parameter_ID']]['Name']
            ))
            break
    else:
        raise ValueError

    with Table(args, 'Language', 'Form', 'Meaning', 'Comment', 'Source') as witnesses:
        for cog in cldf.iter_rows('CognateTable'):
            if cog['Cognateset_ID'] == cs['ID']:
                form = forms[cog['Form_ID']]
                if form['Language_ID'] != cs['Language_ID']:
                    witnesses.append([
                        langs[form['Language_ID']]['Name'],
                        form['Form'],
                        glosses[form['Parameter_ID']]['Name'],
                        unmarkdown(form['Comment'] or ''),
                        cldf.sources[cog['Source'][0]].refkey(year_brackets=None) if cog['Source'] else ''
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
                            form['Form'],
                            glosses[form['Parameter_ID']]['Name'],
                            cldf.sources[cfitem['Source'][0]].refkey(year_brackets=None) if cfitem['Source'] else ''
                        ])
            if cf['Comment']:
                print(unmarkdown(cf['Comment']))
    if cs['Comment']:
        print('\n{}'.format(unmarkdown(cs['Comment'])))
