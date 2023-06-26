import re
import pathlib
import collections

import attr
import pylexibank
from clldutils.misc import slug
from clldutils.markup import MarkdownLink
from pycldf.sources import Sources

from lib.parser import EtymonParser, LanguageParser, LANGS, UNKNOWN_LANGS, is_proto
from lib import part2

# Disambiguation markers for homonyms:
DIS = {'₁': '1', '₂': '2', '₃': '3'}
SIC = re.compile(r'\s+(\[sic])|(\(sic\))')


def extract_sic(form):
    sic = False
    match = SIC.search(form)
    if match:
        sic = True
        form = SIC.sub('', form).strip()
    return form, sic


@attr.s
class Witness(pylexibank.Cognate):
    Comment = attr.ib(default=None)


@attr.s
class Form(pylexibank.Lexeme):
    Comment = attr.ib(default=None)
    sic = attr.ib(
        default=False,
        metadata={'dc:description': "For a form that differs from the expected reflex in some way "
                                    "this flag asserts that a copying mistake has not occurred."}
    )


@attr.s
class Gloss(pylexibank.Concept):
    Description = attr.ib(default=None)


@attr.s
class Language(pylexibank.Language):
    Abbr = attr.ib(default=None)
    Source = attr.ib(
        default=attr.Factory(list),
        metadata=dict(separator=';', propertyUrl="http://cldf.clld.org/v1.0/terms.rdf#source")
    )
    is_proto = attr.ib(
        default=False,
        metadata=dict(datatype='boolean')
    )
    Local_ID = attr.ib(default=None)


class Dataset(pylexibank.Dataset):
    dir = pathlib.Path(__file__).parent
    id = "mcd"

    lexeme_class = Form
    cognate_class = Witness
    concept_class = Gloss
    language_class = Language

    # define the way in which forms should be handled
    form_spec = pylexibank.FormSpec(
        brackets={"(": ")", "[": "]"},  # characters that function as brackets
        separators=";/,",  # characters that split forms e.g. "a, b".
        missing_data=('?', '-'),  # characters that denote missing data.
        strip_inside_brackets=False,   # do you want data removed in brackets or not?
        first_form_only=True,
        replacements=[('[sic]', ''), ('(', ''), (')', '')] + [(m, '') for m in DIS],
    )

    def cmd_download(self, args):
        raise NotImplementedError()

    def cmd_makecldf(self, args):
        self.schema(args)

        args.writer.cldf.sources = Sources.from_file(self.etc_dir / 'sources.bib')
        smap = set(args.writer.cldf.sources.keys())
        l2gl = {l['Local_ID']: l for l in self.languages}
        for v in l2gl.values():
            v['Source'] = v['Source'].split(';')

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

        lmap = {}
        forms = collections.defaultdict(dict)

        def add_form_part1(
                form=None, lid=None, pid=None, value=None, comment=None, source=None, lang=None):
            if form:  # From Form instance (and possibly Language instance)
                add_concept(form)
                fform, sic = extract_sic(form.form)
                lex = args.writer.add_lexemes(
                    Language_ID=l2gl[str(lang.id)]['ID'] if lang else lmap[form.language],
                    Parameter_ID=form.gloss.cid,
                    Value=fform,
                    Comment=form.comment,
                    Source=[str(ref) for ref in lang.refs] if lang else [str(ref) for ref in form.gloss.refs],
                    sic=sic,
                )[0]
                forms[lang.name if lang else form.language][form.form, form.gloss.lookup] = lex
            else:
                value, sic = extract_sic(value)
                lex = args.writer.add_lexemes(
                    Language_ID=lid,
                    Parameter_ID=pid,
                    Value=value,
                    Comment=comment,
                    Source=source or [],
                    sic=sic
                )[0]
            return lex

        for lang, abbr, alias in LANGS:
            if alias:
                lmap[alias] = slug(lang)
            if is_proto(lang):
                d = l2gl[slug(lang)]
                d['is_proto'] = True
                args.writer.add_language(**d)
                lmap[lang] = slug(lang)

        for lang in langs:
            assert all(ref.key in smap for ref in lang.refs)
            args.writer.add_language(**l2gl[str(lang.id)])
            lmap[lang.name] = l2gl[str(lang.id)]['ID']
            for form in lang.forms:
                assert not form.gloss.comment
                add_form_part1(form=form, lang=lang)

        lids = {lang['Local_ID'] for lang in args.writer.objects['LanguageTable']}
        for lid, l in l2gl.items():
            if lid not in lids:
                args.writer.add_language(**l)

        for cset in cognates:
            cid = add_concept(cset)
            # Add the reconstruction as form of the proto language:
            pform = add_form_part1(
                lid=lmap[cset.proto_lang],
                pid=cid,
                value=cset.key,
                comment=cset.gloss.comment or None,
                source=['mcd']
            )
            forms[cset.proto_lang][cset.key, cid] = pform
            # And add this reconstruction to the cognate set:
            args.writer.add_cognate(lexeme=pform, Cognateset_ID=cset.id, Doubt=cset.doubt)

            args.writer.objects['CognatesetTable'].append(dict(
                ID=cset.id,
                Language_ID=lmap[cset.proto_lang],
                Form_ID=pform['ID'],
                Comment=cset.note.markdown if cset.note else None,
                Name=cset.reconstruction,
                Description=cset.gloss,
                Source=['mcd'],
                doubt=cset.doubt,
            ))
            for form in cset.forms:  # Now we lookup forms making up the cognate set.
                if form.language in UNKNOWN_LANGS:
                    continue
                if form.is_proto:
                    add_form_part1(form=form)
                args.writer.add_cognate(
                    lexeme=forms[form.language][form.form, form.gloss.lookup],
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
                    if form.is_proto:
                        add_form_part1(form=form)
                    args.writer.objects['cfitems.csv'].append((dict(
                        ID='{}-{}'.format(cfid, idx + 1),
                        Cfset_ID=cfid,
                        Form_ID=forms[form.language][form.form, form.gloss.lookup]['ID'],
                        Source=[str(ref) for ref in form.gloss.refs if ref.key in smap],
                    )))

        forms = {lmap[lang]: items for lang, items in forms.items()}

        # Parse data of part 2 from CSV:
        def add_form_part2(form, gloss, lid, comment=None):
            form, sic = extract_sic(form)
            bibcomment = re.compile('\|?\(([^0-9]+[0-9]{4}[^)]*)\)')
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
                f = forms[lid][(form, cid)]
            else:
                forms[lid][(form, cid)] = f = args.writer.add_lexemes(
                    Language_ID=lid,
                    Parameter_ID=cid,
                    Value=form,
                    Comment=comment,
                    Source=['mcd2'],
                    sic=sic,
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
                Source=['mcd2'],
                Comment=cs['Comment'],
                doubt=doubt,
            ))

            for lid, cognates in cogs.items():
                for form, gloss, wcomment in cognates:
                    args.writer.add_cognate(
                        lexeme=add_form_part2(form, gloss, lid, wcomment),
                        Cognateset_ID=csid,
                        Source=['mcd2'],#[str(ref) for ref in form.gloss.refs if ref.key in smap],
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
                            Source=['mcd2'],#[str(ref) for ref in form.gloss.refs if ref.key in smap],
                        ))

        for lid, items, comment in loans:
            args.writer.objects['loansets.csv'].append(dict(ID=lid, Description=comment))
            i = 1
            for langid, lforms in items.items():
                for form, gloss, cmt in lforms:
                    args.writer.objects['BorrowingTable'].append(dict(
                        ID='{}-{}'.format(lid, i),
                        Target_Form_ID=add_form_part2(form, gloss or '', langid, cmt)['ID'],
                        Source=['mcd2'],
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
                cs['Comment'] = cldf_markdown(cs['Comment'], lmap, form2id, smap)

        for cs in args.writer.objects['FormTable']:
            if cs['Comment']:
                cs['Comment'] = cldf_markdown(cs['Comment'], lmap, form2id, smap)

    def schema(self, args):
        args.writer.cldf.add_component(
            'CognatesetTable',
            # Description: gloss
            # reconstruction
            {
                'name': 'Name',
                'dc:description': 'The reconstructed proto-form(s).',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#name'},
            {'name': 'Language_ID', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#languageReference'},
            {'name': 'Form_ID', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#formReference'},
            {'name': 'Comment', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#comment'},
            {
                'name': 'doubt',
                'dc:description': 'Flag indicating (un)certainty of the reconstruction.',
                'datatype': 'boolean'},
        )
        args.writer.cldf['CognatesetTable', 'Description'].common_props['dc:description'] = \
            'The reconstructed meaning.'
        t = args.writer.cldf.add_table(
            'cf.csv',
            {'name': 'ID', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#id'},
            {
                'name': 'Name',
                'dc:description': 'The title of a table of related forms.',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#name'},
            {'name': 'Comment', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#comment'},
            {'name': 'Cognateset_ID', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#cognatesetReference'},
        )
        t.common_props['dc:description'] = \
            'MCD does not categorize items which were considered but eventually excluded as witness ' \
            'for a reconstruction as ACD does (into loans, "noise" and "near" cognates). Instead, MCD ' \
            'lists such forms in (a series of) tables related to a cognate set. These tables are listed ' \
            'in `cf.csv`.'
        t = args.writer.cldf.add_table(
            'cfitems.csv',
            {'name': 'ID', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#id'},
            {'name': 'Cfset_ID'},
            {'name': 'Form_ID', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#formReference'},
            {'name': 'Comment', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#comment'},
            {'name': 'Source', 'separator': ';', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#source'},
        )
        args.writer.cldf.add_foreign_key('cfitems.csv', 'Cfset_ID', 'cf.csv', 'ID')
        t.common_props['dc:description'] = \
            'Items in tables related to cognate sets are listed here.'
        args.writer.cldf.add_component(
            'BorrowingTable',
            'Loanset_ID',
        )
        t = args.writer.cldf.add_table(
            'loansets.csv',
            {'name': 'ID', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#id'},
            {'name': 'Description', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#description'},
        )
        t.common_props['dc:description'] = \
            "Part 2 of the Micronesian Reconstructions contains a list of (sets of) loanwords. " \
            "Individual loanwords are listed in the BorrowingTable, linked to the 91 groups listed " \
            "in this table."
        args.writer.cldf.add_foreign_key('BorrowingTable', 'Loanset_ID', 'loansets.csv', 'ID')


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
        res = ''
        for lname, lid in sorted(lmap.items(), key=lambda i: -len(i[0])):
            if m.group('content').startswith(lname):
                res += '[{}](LanguageTable#cldf:{})'.format(lname, lid)
                rem = m.group('content')[len(lname):].strip().replace('&ast;', '').replace('*', '')
                doubt = rem.startswith('(?)') or rem.startswith('?')
                if doubt:
                    form = rem.replace('(?)', '').strip()
                    form = form[1:].strip() if form.startswith('?') else form
                else:
                    form = rem
                if (lname, form) in forms:
                    if doubt:
                        res += ' (?)'
                    assert len(forms[lname, form]) == 1
                    res += ' [{}{}](FormTable#cldf:{})'.format(
                        '&ast;' if is_proto(lname) else '',
                        form,
                        forms[lname, form][0],
                    )
                elif rem:
                    #print(m.group('content'))
                    #print(form, rem)
                    res += m.group('content')[len(lname):]
                break
        else:
            #print(m.group('content'))
            res = m.group('content')
        return res

    res = re.sub('__language__(?P<content>.*?)__', repl, s)

    def bib(md):
        if md.url.startswith('bib-'):
            bid = md.url.partition('-')[2]
            assert bid in sources, 'Missing source: {}; {}'.format(bid, md.label)
            md.url = 'Sources#cldf:{}'.format(bid)
        return md

    try:
        return MarkdownLink.replace(res, bib)
    except:
        print(s)
        raise
