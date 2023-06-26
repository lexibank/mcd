import re
import collections

from csvw.dsv import reader
from tqdm import tqdm

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
    "Fiji": "fijian",
    "Map": "oldmapian",  # 2
    "Mrs": "marshallese",  # 1
    "Ula": "ulawan",  # 1
    "Bug": "bugotu",  # 1
    "Lak": "lakalai",  # 1
    "PAn": "protoaustronesian",  # 1
    "PPC": "protopohnpeicchuukic",
    "PPon": "protopohnpeic",
    "Kir": "gilbertese",
    "Yap": "yapese",
    "Sam": "samoan",
    "Chm": "chamorro",
    "Cham": "chamorro",
    "Pal": "palauan",
    "PPn": "protopolynesian",
    "Rot": "rotuman",
    "Tbi": "tobi",
    "Aro": "arosi",
    "PKb": "protokimbe",
    "Lau": "lau",
    "PMP": "protomalayopolynesian",
    "Tonga": "tongan",
    "Ton": "tongan",
    "PWMP": "protowesternmalayopolynesian",
    "Gedaged": "gedaged",
    "Nguna": "nguna",
    "PMc": "protomicronesian",
    "PLk": "protolakalai",
}


def norm_gloss(g):
    return g.replace(SQUOTE, '').replace(EQUOTE, '')


def parse(raw_dir):
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
    fc, cogsets = collections.Counter(), []
    for i, row in tqdm(enumerate(reader(raw_dir / 'MCD_2_2023-04-27.csv', delimiter='\t'), start=1)):
        row = dict(zip(header, row))
        cmt = row['Seealso']
        if row['Notes']:
            cmt = '{}\n{}'.format(cmt, row['Notes']) if cmt else row['Notes']
        row['Comment'] = cmt
        row['Gloss'] = norm_gloss(row['Gloss'])
        row['Language'] = LANGS[row['Language']]
        row['Form'] = row['Form'].replace('*', '')
        cogs = row['Cognates'].strip()
        if cogs.endswith('.'):
            cogs = cogs[:-1].strip()
        if 1:
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
                #
                # FIXME: handle doubt!!!
                #
                cognates[LANGS[lg]] = []
                for m in re.finditer(wordp, forms):
                    form, gloss, wcomment = m.groups()
                    form = form.strip().lstrip(',').strip()
                    assert form, forms
                    mm = re.search(lcomment, form)
                    if mm:
                        nform = form[:mm.start()].strip()
                        assert not wcomment
                        wcomment = mm.groups()[0]
                        form = nform
                    assert '|' not in form, form
                    cognates[LANGS[lg]].append([form, gloss or row['Gloss'], wcomment])

                m = re.search(lcomment, forms)
                if m:
                    comment = m.groups()[0]
                    if cognates[LANGS[lg]][-1][2]:
                        cognates[LANGS[lg]][-1][2] = '{}; {}'.format(cognates[LANGS[lg]][-1][2], comment)
                    else:
                        cognates[LANGS[lg]][-1][2] = comment

        cftables = []
        if 1:
            cfs = row['Cftable']
            if cfs and cfs != '.':
                for t in cfs.split('@'):
                    items, comment = collections.OrderedDict(), None
                    bylang = {}
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
                        cog = tt.strip()
                        lg, forms = cog.split(maxsplit=1)
                        fc.update([lg])
                        if lg in bylang:
                            assert bylang[lg] == forms, tt
                        else:
                            bylang[lg] = forms
                        items[LANGS[lg]], comment = [], None
                        for m in re.finditer(wordp, forms):
                            form, gloss, wcomment = m.groups()
                            form = form.strip().lstrip(',').strip()
                            items[LANGS[lg]].append((form, gloss or row['Gloss'], wcomment))

                        m = re.search(lcomment, forms)
                        if m:
                            comment = m.groups()[0]
                    cftables.append((type_, items, comment))

        cogsets.append((row, cognates, cftables))

        #
        # FIXME: replace abbreviations in glosses!
        # 's.o.': 'someone'
        # 's.t.': 'something'
        # 'x.': <first word starting with x in row['Gloss']>
        #
    loans = []
    #
    # FIXME: add BorrowingsTable. target, but no source.
    #
    for i, row in tqdm(enumerate(reader(raw_dir / 'MCD_2_loans.tsv', delimiter='\t'), start=1)):
        cogs, comment = row[1:]
        forms = collections.OrderedDict()
        first_gloss = None
        for cog in cogs.split(';'):
            if not cog.strip():
                continue
            cf = False
            if cog.strip().startswith('Cf.'):
                cog = cog.replace('Cf.', '').strip()
                cf = True
            m = cogp.fullmatch(cog.strip())
            assert m, cog
            assert m.group('lg') in LANGS
            lid = LANGS[m.group('lg')]
            forms[lid] = []
            doubt, ff = False, cog
            #
            # FIXME: handle doubt!
            #
            if cog.startswith('?'):
                doubt = True
                ff = cog[1:].strip()
            ff = ' '.join(ff.split()[1:])
            for m in re.finditer(wordp, ff):
                form, gloss, wcomment = m.groups()
                if form == '.':
                    continue
                if not first_gloss:
                    first_gloss = gloss
                form = form.strip().lstrip(',').strip()
                assert form
                mm = re.search(lcomment, form)
                if mm:
                    nform = form[:mm.start()].strip()
                    assert not wcomment
                    wcomment = mm.groups()[0]
                    form = nform
                assert '|' not in form, form
                forms[lid].append([form, gloss or first_gloss, wcomment])

            #
            # FIXME: handle doubt! cog.startswith('?')!
            #
        loans.append((row[0], forms, comment))

    return cogsets, loans
