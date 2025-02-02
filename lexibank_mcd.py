import re
import pathlib
import functools
import itertools
import collections

import pylexibank
from clldutils.misc import slug
from clldutils.markup import MarkdownLink
from pycldf.sources import Sources
from pyetymdict.dataset import Dataset as BaseDataset

from lib.parser import EtymonParser, LanguageParser
from lib import part2

# Disambiguation markers for homonyms:
DIS = {'₁': '1', '₂': '2', '₃': '3'}
SIC = re.compile(r'\s+(\[sic])|(\(sic\))')
BRACKETS_IN_MARKDOWN_LINK = {'[': '\u23a3', ']': '\u23a6'}
UNKNOWN_LANGS = [
    # Three language identifiers in part 1 are not listed under "Languages". The corresponding forms
    # are ignored.
    'Tik',  # Tikopia? - one form: kainaŋa  https://www.trussel2.com/MCD/pmc-sets-k.htm#3242
    'Haw',  # Probably Hawaiian - one form: ‘ainana  https://www.trussel2.com/MCD/pmc-sets-k.htm#3242
    'Fiji',  # Probably Fijian - one form: cina  https://www.trussel2.com/MCD/pmc-sets-s1.htm#3711
]
DIFF = {  # Difference between number of word parsed and number of words as stated.
    'saipancaroliniant': 17,  # Variety forms mixed into Saipan Carolinian vocabulary.
    'arosi': -2,  # A duplicate: aŋa-’i
    'bugotu': -3,  # Duplicates, listed in cf sets of different etyma: ula‘tendon, sinew, vein’; vaŋato eat, vegetable food; tanoearth, ground
    'chuukese': -3,
    'kosraean': -4,
    'kwaio': -3,
    'lau': 1,
    'fijian': -2,
    'gilbertese': -5,
    'marshallese': -2,
    'mokilese': -2,  # 559/561
    'mortlockese': -1,  # 370/371
    'ngatchikese': 1,  # 2/1
    'pingilapese': 5,  # Five words listed in the Mokilese wordlist.
    'pohnpeian': -3,  # 816/819
    'puloannan': -3,  # 531/534
    'puluwatese': -1,  # 840/841
    'sonsorolese': 1,  # 76/75
    'ulawan': 2,  # 32/30
    'woleaian': -1,  # 995/996
}


def extract_sic(form):
    sic = False
    match = SIC.search(form)
    if match:
        sic = True
        form = SIC.sub('', form).strip()
    return form, sic


class LanguageMeta:
    """
    Class allowing programmatic access to the language metadata from etc/languages.csv
    """
    def __init__(self, langs):
        self.data = langs
        for v in self.data:
            v['Is_Proto'] = v['Is_Proto'] == '1'
            v['Source'] = v['Source'].split(';')
            v['Abbr'] = v['Abbr'].split(';')

    def items(self):
        return ((l['Local_ID'], l) for l in self.data)

    def language_and_form(self, text):
        """
        Detect "<language> <form>" pairs.
        """
        lg = None
        labelcomps, formcomps = text.split(), []
        while labelcomps:
            try:
                if labelcomps[0].startswith('&ast;') and labelcomps[0].replace('&ast;', '') in self:
                    lg = self[labelcomps[0].replace('&ast;', '')]
                else:
                    lg = self[' '.join(labelcomps)]
                break
            except KeyError:
                formcomps.append(labelcomps.pop())
        assert lg, "No (language, form) pair found in '{}'".format(text)
        return lg, ' '.join(formcomps)

    def __getitem__(self, item):
        for l in self.data:
            if l['ID'] == item:
                return l
            if l['Local_ID'] == item:
                return l
            if l['Name'] == item:
                return l
            if l['Alias'] and l['Alias'] == item:
                return l
            if l['Abbr'] and item in l['Abbr']:
                return l
        raise KeyError(item)

    def __contains__(self, item):
        try:
            self[item]
            return True
        except KeyError:
            return False


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "mcd"

    # define the way in which forms should be handled
    form_spec = pylexibank.FormSpec(
        brackets={"(": ")", "[": "]"},  # characters that function as brackets
        separators=";/,<",  # characters that split forms e.g. "a, b".
        missing_data=('?', '-'),  # characters that denote missing data.
        strip_inside_brackets=False,   # do you want data removed in brackets or not?
        first_form_only=True,
        replacements=[('[sic]', ''), ('(', ''), (')', '')] + [(m, '') for m in DIS],
    )

    @functools.cached_property
    def lmeta(self):
        return LanguageMeta(self.languages)

    def gloss_lookup(self, gloss):
        """
        To ensure correctness of our parsing, we check if forms listed as reflexes of
        reconstructions also appear on the "Languages" pages. Since glosses may be formatted
        slightly differently on these two types of pages, we have to construct a normalized gloss
        for comparison.
        """
        def repl_language(m):
            labelcomps = m.group('lg').split()
            while labelcomps:
                try:
                    return self.lmeta[' '.join(labelcomps)]['ID']
                except KeyError:
                    labelcomps.pop()
            if m.group('lg') in {'zuRi'}:
                return m.group('lg')
            raise KeyError(m.group('lg'))

        res = (
            slug(re.sub(
                r'\[[^]]+]\(bib-[^)]+\)',
                '',
                re.sub(
                    # __language__ID *form__
                    r'__language__(?P<lg>[^_]+)__',
                    repl_language,
                    gloss.lookup)))
            or (gloss.refs[0].label if gloss.refs else '') or 'none')
        return res.strip()

    def cmd_makecldf(self, args):
        self.schema(args.writer.cldf)

        args.writer.cldf['LanguageTable', 'Group'].common_props['dc:description'] = \
            "Subgroup of Oceanic - according to Glottolog - to which the language belongs."
        oceanic = {
            lg.id: list(itertools.takewhile(
                lambda i: i != 'Oceanic', [n[0] for n in reversed(lg.lineage)]))
            for lg in args.glottolog.api.languoids()
            if lg.lineage and 'ocea1241' in [gc for _, gc, _ in lg.lineage]}
        oceanic = {k: v[-1] for k, v in oceanic.items() if len(v) > 0}

        args.writer.cldf.sources = Sources.from_file(self.etc_dir / 'sources.bib')
        smap = set(args.writer.cldf.sources.keys())

        glangs = self.glottolog_cldf_languoids('../../glottolog/glottolog-cldf')
        l2src = {}
        for _, d in self.lmeta.items():
            dd = {k: v for k, v in d.items() if k not in ['Local_ID', 'Alias']}
            if dd['Glottocode']:
                if dd['Glottocode'] in oceanic:
                    dd['Group'] = oceanic[dd['Glottocode']]
                glang = glangs[dd['Glottocode']]
                dd['Latitude'], dd['Longitude'] = float(glang.cldf.latitude), float(glang.cldf.longitude)
            if dd['Abbr']:
                dd['Abbr'] = dd['Abbr'][0]
            l2src[dd['ID']] = dd['Source']
            args.writer.add_language(**dd)

        self.add_tree(
            args.writer,
            "((((PCk,PPon)PPC,Mrs)PWMc,Kir)PCMc,Ksr)PMc;",
            {r['Abbr']: r['ID'] for r in args.writer.objects['LanguageTable']})

        def add_concept(form):
            if isinstance(form, str):
                cid = slug(form) or 'none'
                name = form
            else:
                cid = form.gloss.cid
                name = form.gloss.markdown
            if cid not in concepts:
                args.writer.add_concept(ID=cid, Name=name)
                concepts.add(cid)
            return cid

        # Parse data of part 1 from HTML:
        cognates, langs = list(EtymonParser(self.raw_dir)), list(LanguageParser(self.raw_dir))
        concepts = set()
        forms = collections.defaultdict(dict)

        def add_form_part1(
                form=None, lid=None, pid=None, value=None, comment=None, source=None, lang=None, description=None):
            if form:  # From Form instance (and possibly Language instance)
                add_concept(form)
                lg = self.lmeta[str(lang.id) if lang else form.language]
                fform, sic = extract_sic(form.form)
                if lg['Is_Proto']:
                    if fform.startswith('*'):
                        fform = fform[1:]
                else:
                    if fform.startswith('*'):
                        assert fform in {
                            # samoan:
                            '*pia',
                            # pohnpeian:
                            '*mici-ki',
                            '*payipayi',
                            '*peine',
                            '*tara-wii',
                        }, '{} {}'.format(lg['ID'], fform)
                        fform = fform[1:]
                        form.form = form.form[1:]

                lex = args.writer.add_lexemes(
                    Language_ID=lg['ID'],
                    Parameter_ID=form.gloss.cid,
                    Description=form.gloss.markdown,
                    Value=fform,
                    Comment=form.comment,
                    Source=[str(ref) for ref in lang.refs] if lang else [str(ref) for ref in form.gloss.refs],
                    Sic=sic,
                    Doubt=getattr(form, 'doubt', False),
                )[0]
                forms[lg['ID']][form.form, self.gloss_lookup(form.gloss)] = lex
            else:
                value, sic = extract_sic(value)
                lex = args.writer.add_lexemes(
                    Language_ID=lid,
                    Parameter_ID=pid,
                    Value=value,
                    Comment=comment,
                    Source=source or [],
                    Sic=sic,
                    Description=description,
                )[0]
            return lex

        for lang in langs:  # Non-proto languages. The ones listed on language pages of MCD.
            assert all(ref.key in smap for ref in lang.refs)
            if lang.nwords == len(lang.forms):
                pass
            elif self.lmeta[lang.name]['ID'] in DIFF:
                assert DIFF[self.lmeta[lang.name]['ID']] + lang.nwords == len(lang.forms), \
                    '{}: {}/{}'.format(self.lmeta[lang.name]['ID'], len(lang.forms), DIFF[self.lmeta[lang.name]['ID']] + lang.nwords)
            else:
                raise ValueError
            for form in lang.forms:  # We add forms from the language page, not from the etyma.
                assert not form.gloss.comment
                add_form_part1(form=form, lang=lang)

        for cset in cognates:
            cid = add_concept(cset)
            # Add the reconstruction as form of the proto language:
            pform = add_form_part1(
                lid=self.lmeta[cset.proto_lang]['ID'],
                pid=cid,
                value=cset.key,
                comment=cset.gloss.comment or None,
                source=['pmr1'],
                description=cset.gloss.markdown,
            )
            forms[self.lmeta[cset.proto_lang]['ID']][cset.key, cid] = pform
            # And add this reconstruction to the cognate set:
            args.writer.add_cognate(lexeme=pform, Cognateset_ID=cset.id, Doubt=cset.doubt)

            args.writer.objects['CognatesetTable'].append(dict(
                ID=cset.id,
                Language_ID=self.lmeta[cset.proto_lang]['ID'],
                Form_ID=pform['ID'],
                Comment=cset.note.markdown if cset.note else None,
                Name=cset.reconstruction,
                Description=cset.gloss.markdown,
                Source=['pmr1'],
                Doubt=cset.doubt,
            ))
            for form in cset.forms:  # Now we lookup forms making up the cognate set.
                if form.language in UNKNOWN_LANGS:
                    continue
                if self.lmeta[form.language]['Is_Proto'] is True:
                    # The proto-form witnesses are not listed on language pages and must be added
                    # now.
                    add_form_part1(form=form)
                args.writer.add_cognate(
                    lexeme=forms[self.lmeta[form.language]['ID']][form.form, self.gloss_lookup(form.gloss)],
                    Cognateset_ID=cset.id,
                    Source=[str(ref) for ref in form.gloss.refs],
                    Doubt=form.doubt,
                )
            for j, (header, comment, fs) in enumerate(cset.cf_forms):
                cfid = '{}-{}'.format(cset.id, j + 1)
                args.writer.objects['cf.csv'].append((dict(
                    ID=cfid,
                    Name=header,
                    Comment=comment,
                    Cognateset_ID=cset.id,
                )))
                for idx, form in enumerate(fs):
                    if self.lmeta[form.language]['Is_Proto'] is True:
                        add_form_part1(form=form)
                    args.writer.objects['cfitems.csv'].append((dict(
                        ID='{}-{}'.format(cfid, idx + 1),
                        Cfset_ID=cfid,
                        Form_ID=forms[self.lmeta[form.language]['ID']][form.form, self.gloss_lookup(form.gloss)]['ID'],
                        Source=[str(ref) for ref in form.gloss.refs if ref.key in smap],
                    )))

        # Parse data of part 2 from CSV:
        def add_form_part2(form, gloss, lid, comment=None):
            form, sic = extract_sic(form)
            bibcomment = re.compile(r'\|?\(([^0-9]+[0-9]{4}[^)]*)\)')
            m = bibcomment.search(form)
            if m:
                form = re.sub(r'\s+', ' ', (form[:m.start()] + form[m.end():]).strip())
                assert not comment
                comment = m.groups()[0]
            form = form.replace(' and ', ', ')
            dis = {v: k for k, v in DIS.items()}
            if any(c in form for c in dis):
                for k, v in dis.items():
                    form = form.replace(k, v)
            forms.setdefault(lid, {})
            if '(lit.' in gloss:
                assert not comment
                gloss, _, comment = gloss.partition('(')
                gloss, comment = gloss.strip(), comment.strip()
            cid = add_concept(gloss)
            if (form, cid) in forms[lid]:
                # A form already known from the first part!
                #
                # FIXME: Is this an interesting fact/number to report in the paper?
                #
                #print(lid, form)
                f = forms[lid][(form, cid)]
            else:
                forms[lid][(form, cid)] = f = args.writer.add_lexemes(
                    Language_ID=lid,
                    Parameter_ID=cid,
                    Value=form,
                    Comment=comment,
                    Source=l2src[lid] or ['pmr2'],
                    Sic=sic,
                    Description=gloss,
                )[0]
            return f

        cogsets, loans = part2.parse(self.raw_dir)
        for i, (cs, cogs, cfs) in enumerate(cogsets, start=1):
            csid = 'P2-{}'.format(i)
            pform, doubt = cs['Form'].strip(), False
            if pform.startswith('?'):
                pform = pform[1:].strip()
                doubt = True
            args.writer.objects['CognatesetTable'].append(dict(
                ID=csid,
                Language_ID=cs['Language'],
                Form_ID=add_form_part2(pform, cs['Gloss'], cs['Language'])['ID'],
                Name=cs['Form'],
                Description=cs['Gloss'],
                Source=['pmr2'],
                Comment=cs['Comment'],
                Doubt=doubt,
            ))

            for lid, cognates in cogs.items():
                for form, gloss, wcomment in cognates:
                    args.writer.add_cognate(
                        lexeme=add_form_part2(form, gloss, lid, wcomment),
                        Cognateset_ID=csid,
                        Source=['pmr2'],#[str(ref) for ref in form.gloss.refs if ref.key in smap],
                        Doubt=cognates.doubt,
                    )
            # process cfs
            for i, (type, items, comment) in enumerate(cfs, start=1):
                cfid = '{}-{}'.format(csid, i)
                args.writer.objects['cf.csv'].append(dict(
                    ID=cfid,
                    Name=type,
                    Cognateset_ID=csid,
                    Comment=comment,
                ))
                wc = 0
                for lg, litems in items.items():
                    for form, gloss, wcomment in litems:
                        wc += 1
                        args.writer.objects['cfitems.csv'].append(dict(
                            ID='{}-{}'.format(cfid, wc),
                            Form_ID=add_form_part2(form, gloss, lg, wcomment)['ID'],
                            Cfset_ID=cfid,
                            Source=['pmr2'],#[str(ref) for ref in form.gloss.refs if ref.key in smap],
                        ))

        for lid, items, comment in loans:
            args.writer.objects['cf.csv'].append(dict(ID=lid, Description=comment, Category='loans'))
            i = 1
            for langid, lforms in items.items():
                for form, gloss, cmt in lforms:
                    args.writer.objects['BorrowingTable'].append(dict(
                        ID='{}-{}'.format(lid, i),
                        Target_Form_ID=add_form_part2(form, gloss or '', langid, cmt)['ID'],
                        Source=['pmr2'],
                        Cfset_ID=lid,
                    ))
                    i += 1

        form2id = collections.defaultdict(list)
        for lname, data in forms.items():
            for (form, _), lex in data.items():
                form2id[lname, form].append(lex['ID'])
                if ' or ' in form:
                    for ff in form.split(' or '):
                        form2id[lname, ff].append(lex['ID'])

        for cs in args.writer.objects['CognatesetTable']:
            if cs['Comment']:
                cs['Comment'] = cldf_markdown(cs['Comment'], self.lmeta, form2id, smap)

        for cs in args.writer.objects['FormTable']:
            if cs['Comment']:
                cs['Comment'] = cldf_markdown(cs['Comment'], self.lmeta, form2id, smap)


def cldf_markdown(s, lmap, forms, sources):
    """
    In
    - Parameter.Description
    - Form.Comment
    - Cognateset.Comment

    __language__Proto-Chuukic__ _&ast;wudu_
    __language__Proto-Micronesian &ast;watu__
    __language__Proto-Micronesian (?) &ast;u[sS]a, u[sS]a-ni, u[sS]a-na__
    [Marck (1994:308)](bib-Marck (1994)

    "Cf. PCk *dili ‘a small fish’, PMc *mwonu ‘squirrel fish’."
    "Cf. PMc *ma-[sS]aLu, ma-[sS]aLu[sS]aLu ‘smooth (of surface) ’ posited by Goodenough (1995:77)"
    """
    #
    # FIXME: Must also detect plain text refs like "Ksr", "PMc *afaŋi", "Marck (1994:323)".
    # "Ksr ɛir, glossed as ‘north’ in dictionary, is a probable loan (see PMc *afaŋi ‘north’).
    # Marck (1994:323) reconstructs PMc *auru, including the Ksr forms whose r is unexpected.
    #

    def repl(m):
        def link_label(s):
            for k, v in BRACKETS_IN_MARKDOWN_LINK.items():
                s = s.replace(k, v)
            return s

        s = m.group('content')
        res = ''
        try:
            lg, form = lmap.language_and_form(s)
        except AssertionError:
            return s
        res += '[{}](LanguageTable{}#cldf:{})'.format(lg['Name'], '?is_proto' if lg['Is_Proto'] else '', lg['ID'])

        if form:
            form = form.replace('&ast;', '').replace('*', '')
            doubt = form.startswith('(?)') or form.startswith('?')
            if doubt:
                form = form.replace('(?)', '').strip()
                form = form[1:].strip() if form.startswith('?') else form
            if (lg['ID'], form) in forms:
                if doubt:
                    res += ' (?)'
                assert len(forms[lg['ID'], form]) == 1
                res += ' [{}{}](FormTable#cldf:{})'.format(
                    '&ast;' if lg['Is_Proto'] else '',
                    link_label(form),
                    forms[lg['ID'], form][0],
                )
            else:
                res += ' _{}_'.format(form)
        return res

    res = re.sub(r'__language__(?P<content>[^_]*)__', repl, s)

    def bib(md):
        if md.url.startswith('bib-'):
            bid = md.url.partition('-')[2]
            assert bid in sources, 'Missing source: {}; {}'.format(bid, md.label)
            md.url = 'Source#cldf:{}'.format(bid)
        return md

    return MarkdownLink.replace(res, bib)
