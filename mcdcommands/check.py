"""

"""
import re

from lexibank_mcd import Dataset


def run(args):
    from csvw.dsv import reader
    import re

    cogp = re.compile(r'[A-Z][a-zA-Z]{2}\s+([^‘]+)(‘([^’]+)’)?(,\s*([^‘]+)‘([^’]+)’)*')  # Gloss is optional (take over from reconstruction if missing)

    header = [
        'Language',  # PCk PPC PPon
        'Form',  # Most common: *kurupwu (2x)  *riciŋa (2x)  *-ali (1x), may have leading "? "
        'Gloss',  # Contains 15 cases with "lit." mixed in gloss -> separate out into form comment.
        'Cognates',  # ;-separated
        'Cftable',  # If there are multiple such tables, they are separated by "@". I attempted to mark any internal comments or references by "|", though it's probably not too useful.
        'Seealso',  # "see also"-like notes with cross-references to other protoforms in the MCD itself,
        'Notes',  # notes
    ]
    for row in reader(Dataset().dir / 'MCD_2_2023-04-27.csv', delimiter='\t'):
        row = dict(zip(header, row))
        cogs = row['Cognates'].strip()
        if cogs.endswith('.'):
            cogs = cogs[:-1].strip()
        for cog in cogs.split(';'):
            if not cogp.fullmatch(cog.strip()):
                print(row['Cognates'])
                print(cog)
                break


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
