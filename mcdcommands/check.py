"""

"""
import re

from lexibank_mcd import Dataset


def run(args):
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
