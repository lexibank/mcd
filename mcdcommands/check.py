"""

"""
import re

from lexibank_mcd import Dataset

SQUOTE = '‘'
EQUOTE = '’'


def forms_and_comment(forms):
    fs, comment = [], None
    if forms.endswith(')'):
        comment = forms.split('(')[-1][:-1].strip()
        forms = '('.join(forms.split('(')[:-1])

    rem = forms
    while SQUOTE in rem:
        form, _, rem = forms.partition(SQUOTE)
        gloss, _, rem = rem.partition(EQUOTE)
        fs.append((form, gloss))
    assert not rem.strip()
    return fs, comment


def run(args):
    from csvw.dsv import reader
    import re

    cogp = re.compile(r'(?P<lg>[A-Z][a-zA-Z]{2})\s+([^‘]+)(‘([^’]+)’)?(,\s*([^‘]+)‘([^’]+)’)*(\s*\([^)]+\))?')  # Gloss is optional (take over from reconstruction if missing)

    header = [
        'Language',  # PCk PPC PPon
        'Form',  # Most common: *kurupwu (2x)  *riciŋa (2x)  *-ali (1x), may have leading "? "
        'Gloss',  # Contains 15 cases with "lit." mixed in gloss -> separate out into form comment.
        'Cognates',  # ;-separated
        'Cftable',  # If there are multiple such tables, they are separated by "@". I attempted to mark any internal comments or references by "|", though it's probably not too useful.
        'Seealso',  # "see also"-like notes with cross-references to other protoforms in the MCD itself,
        'Notes',  # notes
    ]
    for i, row in enumerate(reader(Dataset().raw_dir / 'MCD_2_2023-04-27.csv', delimiter='\t'), start=1):
        if i > 396: break
        row = dict(zip(header, row))
        cogs = row['Cognates'].strip()
        if cogs.endswith('.'):
            cogs = cogs[:-1].strip()
        for cog in cogs.split(';'):
            if not cogp.fullmatch(cog.strip()):
                print(row['Cognates'])
                print(i, cog)
                break
            else:
                cog = cog.strip()
                lg, forms = cog.split(maxsplit=1)
                forms, comment = forms_and_comment(forms)
                for form, gloss in forms:
                    gloss = gloss or row['Gloss']
                    #re.sub('(^|[^a-zA-Z])([a-z])\.', lambda m: m, gloss)


        #
        # FIXME: replace abbreviations in glosses!
        # 's.o.': 'someone'
        # 's.t.': 'something'
        # 'x.': <first word starting with x in row['Gloss']>
        #


def run2(args):
    cldf = Dataset().cldf_reader()
    abbrs = {r['abbr'] for r in cldf.iter_rows('LanguageTable') if r['abbr']}
    for f in cldf.iter_rows('FormTable'):
        if any(abbr in f['Form'] for abbr in abbrs):
        #if re.search('(^|\s)[A-Z]', f['Form']):
            print(f['Form'])
            #
            # FIXME:
            # - separate forms
            # - create new form row (copying sources and parameter_id)
            # - add form to cognate sets the original form is linked to
            #
