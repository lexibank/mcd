"""

"""
import re
import collections

from tqdm import tqdm
from lexibank_mcd import Dataset

SQUOTE = '‘'
EQUOTE = '’'

LANGS = {
    "Wol": "woleaian",  # 622
    "Chk": "chuukese",  # 600
    "Pul": "puluwatese",  # 505
    "Crl": "saipancarolinian",  # 468
    "PuA": "puloannan",  # 211
    "Crn": "saipancaroliniant",  # 187
    "Pon": "pohnpeian",  # 133
    "Stw": "satawalese",  # 116
    "Mrt": "mortlockese",  # 115
    "PCk": "protochuukic",  # 101
    "Mok": "mokilese",  # 65
    "Uli": "ulithian",  # 33
    "Sns": "sonsorolese",  # 24
    "Png": "pingilapese",  # 9
    "PEO": "protoeasternoceanic",  # 7
    "UAn": "uraustronesisch",  # 3
    "POc": "protooceanic",  # 2
    "Ksr": "kosraean",  # 2
    "Saa": "saa",  # 2
    "Kwa": "kwaio",  # 2
    "Fij": "fijian",  # 2
    "Map": "oldmapian",  # 2
    "Mrs": "marshallese",  # 1
    "Ula": "ulawan",  # 1
    "Bug": "bugotu",  # 1
    "Lak": "lakalai",  # 1
    "PAn": "protoaustronesian",  # 1
    "PPC": "protopohnpeicchuukic",
    "PPon": "protopohnpeic",
}


def forms_and_comment(forms):
    fs, comment = [], None
    if forms.endswith(')'):
        #
        # FIXME: If only one character is between braces, that's part of the form!
        #
        comment = forms.split('(')[-1][:-1].strip()
        forms = '('.join(forms.split('(')[:-1])

    form, gloss, in_gloss = '', '', False
    for c in forms:
        if c == SQUOTE:
            in_gloss = True
            continue
        elif c == EQUOTE:
            in_gloss = False
            continue
        if in_gloss:
            gloss += c
        else:
            if c == ',':
                if form.strip():
                    fs.append((form.strip().replace('*', ''), gloss.strip() or None))
                form, gloss = '', ''
            else:
                form += c
    if form.strip():
        fs.append((form.strip().replace('*', ''), gloss.strip() or None))

    return fs, comment


def norm_gloss(g):
    return g.replace(SQUOTE, '').replace(EQUOTE, '')


def run(args):
    from csvw.dsv import reader
    import re
    import collections

    wordp = r'([^‘]+)(?:‘([^’]+)’)?(?:\s+\(([^)|]+)\))?'  # form, gloss, comment
    lcomment = r'(?:\s*\|\s*(?:\(([^)]+)\)))'
    cogp = re.compile(
        r'(\?\s+)?(?P<lg>[A-Z][a-zA-Z]{2,3}|Tonga|Nguna|Gedaged|Fiji)\s+' +
        wordp +
        '(,\s*' + wordp + ')*' + lcomment + '?\.?')  # Gloss is optional (take over from reconstruction if missing)

    header = [
        'Language',  # PCk PPC PPon
        'Form',  # Most common: *kurupwu (2x)  *riciŋa (2x)  *-ali (1x), may have leading "? "
        'Gloss',  # Contains 15 cases with "lit." mixed in gloss -> separate out into form comment.
        'Cognates',  # ;-separated
        'Cftable',  # If there are multiple such tables, they are separated by "@". I attempted to mark any internal comments or references by "|", though it's probably not too useful.
        'Seealso',  # "see also"-like notes with cross-references to other protoforms in the MCD itself,
        'Notes',  # notes
    ]
    fc = collections.Counter()
    for i, row in tqdm(enumerate(reader(Dataset().raw_dir / 'MCD_2_2023-04-27.csv', delimiter='\t'), start=1)):
        row = dict(zip(header, row))
        row['Gloss'] = norm_gloss(row['Gloss'])
        row['Language'] = LANGS[row['Language']]
        row['Form'] = row['Form'].replace('*', '')
        cogs = row['Cognates'].strip()
        if cogs.endswith('.'):
            cogs = cogs[:-1].strip()
        if 1:
            #print('\n{}\t{}\t{}'.format(row['Language'], row['Form'], row['Gloss']))
            cognates = collections.OrderedDict()
            bylang = {}
            for cog in cogs.split(';'):
                assert cogp.fullmatch(cog.strip()), cog
                cog = cog.strip()
                lg, forms = cog.split(maxsplit=1)
                fc.update([lg])
                if lg in bylang:
                    assert bylang[lg] == forms, cogs
                else:
                    bylang[lg] = forms
                cognates[LANGS[lg]] = []
                #print('\t{}'.format(lg))
                for m in re.finditer(wordp, forms):
                    form, gloss, wcomment = m.groups()
                    form = form.strip().lstrip(',').strip()
                    #
                    # FIXME: check for lcomment in form, e.g. "uwwele |(<*wewele)"
                    #
                    #print('\t\t{}\t{}\t{}'.format(form, gloss, wcomment))
                    cognates[LANGS[lg]].append((form, gloss or row['Gloss'], wcomment))

                m = re.search(lcomment, forms)
                if m:
                    comment = m.groups()[0]
                    #print(comment)

            #yield row, cognates

        if 1:
            cfs = row['Cftable']
            if cfs and cfs != '.':
                for t in cfs.split('@'):
                    type_ = 'Cf.'
                    m = re.match('\s*(Cf\.|See|Note|cf\.)( also)?', t)
                    if not m:
                        assert t.startswith('PAn ')
                    else:
                        type_ = t[:m.end()]
                        t = t[m.end():].strip()

                    t = t.strip()
                    if t.endswith('.'):
                        t = t[:-1].strip()

                    for tt in t.split(';'):
                        mm = re.search('\|\(([^)]+)\)$', tt)
                        if mm:
                            comment = mm.groups()[0].replace('__', '(').replace('_/_', ')')
                            tt = tt[:mm.start()].strip()
                        #
                        # FIXME: match "|(src)"!
                        #
                        tt = tt.strip()
                        assert cogp.fullmatch(tt)

        #
        # FIXME: replace abbreviations in glosses!
        # 's.o.': 'someone'
        # 's.t.': 'something'
        # 'x.': <first word starting with x in row['Gloss']>
        #
    for i, row in tqdm(enumerate(reader(Dataset().raw_dir / 'MCD_2_loans.tsv', delimiter='\t'), start=1)):
        cogs, comment = row[1:]
        for cog in cogs.split(';'):
            if not cog.strip():
                continue
            cf = False
            if cog.strip().startswith('Cf.'):
                cog = cog.replace('Cf.', '').strip()
                cf = True
            assert cogp.fullmatch(cog.strip()), cog

    #for k, v in fc.most_common():
    #    print(k, v)


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
