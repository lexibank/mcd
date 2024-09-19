"""
Display a cognate set (a.k.a. etymon), i.e. a reconstruction and its supporting forms as in the MCD.
"""
import re
import collections

from termcolor import colored
from clldutils.clilib import Table, add_format
from clldutils.markup import MarkdownLink

from lexibank_mcd import Dataset, BRACKETS_IN_MARKDOWN_LINK


def register(parser):
    parser.add_argument('cset', help="Numeric cognateset ID or reconstructed proto-form.")
    parser.add_argument('--with-source', action='store_true', default=False)
    add_format(parser, 'plain')


def fmt_language(label, is_proto=False):
    return colored(label, 'red' if is_proto else 'green')


def fmt_form(label):
    return colored(label, 'red' if label.startswith('&ast;') or label.startswith('*') else 'blue')


def unmarkdown(s):
    def repl(mdl):
        def label(s):
            for k, v in BRACKETS_IN_MARKDOWN_LINK.items():
                s = s.replace(v, k)
            return s
        if mdl.parsed_url.path == 'LanguageTable':
            return fmt_language(label(mdl.label), 'is_proto' in mdl.parsed_url_query)
        if mdl.parsed_url.path == 'FormTable':
            return fmt_form(label(mdl.label))
        return colored(label(mdl.label), None, attrs=['underline'])

    return re.sub(
        r'_(?P<content>[a-zA-Z]+)_',
        lambda m: colored(m.group('content'), None, attrs=['reverse']),
        MarkdownLink.replace(s, repl).replace('&ast;', '*'))


def run(args):
    cldf = Dataset().cldf_reader()

    langs = {l['ID']: l for l in cldf.iter_rows('LanguageTable')}
    forms = {l['ID']: l for l in cldf.iter_rows('FormTable')}
    glosses = {l['ID']: l for l in cldf.iter_rows('ParameterTable')}

    for cs in cldf.iter_rows('CognatesetTable'):
        if cs['ID'] == args.cset or cs['Name'] == args.cset or cs['Name'].replace('*', '') == args.cset.replace('*', ''):
            print('\n{}\t{}\t{}\n'.format(
                colored(langs[cs['Language_ID']]['Name'] + (' (?)' if cs['doubt'] else ''), 'blue', attrs=['bold']),
                colored('*' + forms[cs['Form_ID']]['Value'].replace(' or ', ' or *'), 'red', attrs=['bold']),
                colored(glosses[forms[cs['Form_ID']]['Parameter_ID']]['Name'], 'black')
            ))
            break
    else:
        raise ValueError(args.cset)

    previous_lid = None
    cols = ['Language', 'Form', 'Meaning', 'Comment']
    if args.with_source:
        cols.append('Source')
    with Table(args, *cols, headers=()) as witnesses:
        for cog in cldf.iter_rows('CognateTable'):
            if cog['Cognateset_ID'] == cs['ID']:
                form = forms[cog['Form_ID']]
                is_proto = langs[form['Language_ID']]['Is_Proto']
                if form['Language_ID'] != cs['Language_ID']:
                    cols = [
                        fmt_language(
                            langs[form['Language_ID']]['Name']
                            if previous_lid != form['Language_ID'] else '',
                            is_proto),
                        fmt_form(('*' if is_proto else '') + form['Value']),
                        glosses[form['Parameter_ID']]['Name'],
                        unmarkdown(form['Comment'] or ''),
                    ]
                    if args.with_source:
                        cols.append('; '.join(
                            cldf.sources[src.split('[')[0]].refkey(year_brackets=None)
                            for src in set(form['Source'] + cog['Source'])))
                    witnesses.append(cols)
                    previous_lid = form['Language_ID']

    cf_members = collections.defaultdict(list)
    for cfitem in cldf.iter_rows('cfitems.csv'):
        cf_members[cfitem['Cfset_ID']].append(cfitem)

    for cf in cldf.iter_rows('cf.csv'):
        if cf['Cognateset_ID'] == cs['ID']:
            print('\n--- {} ---'.format(cf['Name']))
            cols = ['Language', 'Form', 'Meaning']
            if args.with_source:
                cols.append('Source')
            with Table(args, *cols, headers=()) as witnesses:
                for cfitem in cf_members[cf['ID']]:
                    form = forms[cfitem['Form_ID']]
                    if form['Language_ID'] != cs['Language_ID']:
                        is_proto = langs[form['Language_ID']]['Is_Proto']
                        cols = [
                            fmt_language(langs[form['Language_ID']]['Name'], is_proto),
                            fmt_form(('*' if is_proto else '') + form['Value']),
                            glosses[form['Parameter_ID']]['Name'],
                        ]
                        if args.with_source:
                            cols.append(
                                cldf.sources[cfitem['Source'][0].split('[')[0]].refkey(year_brackets=None)
                                if cfitem['Source'] else ''
                            )
                        witnesses.append(cols)
            if cf['Comment']:
                print(unmarkdown(cf['Comment']))
    if cs['Comment']:
        print('\n{}'.format(unmarkdown(cs['Comment'])))
