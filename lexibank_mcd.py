import pathlib
import collections

import attr
import pylexibank
from clldutils.misc import slug
from clldutils.markup import MarkdownLink
from pycldf.sources import Sources

from crawler import crawl
from parser import EtymonParser, LanguageParser, LANGS, UNKNOWN_LANGS, is_proto


@attr.s
class Witness(pylexibank.Cognate):
    Comment = attr.ib(default=None)


@attr.s
class Form(pylexibank.Lexeme):
    Comment = attr.ib(default=None)


@attr.s
class Gloss(pylexibank.Concept):
    Description = attr.ib(default=None)


@attr.s
class Language(pylexibank.Language):
    is_proto = attr.ib(
        default=False,
        metadata=dict(datatype='boolean')
    )


class Dataset(pylexibank.Dataset):
    dir = pathlib.Path(__file__).parent
    id = "mcd"

    lexeme_class = Form
    cognate_class = Witness
    concept_class = Gloss
    language_class = Language

    # define the way in which forms should be handled
    form_spec = pylexibank.FormSpec(
        brackets={"(": ")"},  # characters that function as brackets
        separators=";/,",  # characters that split forms e.g. "a, b".
        missing_data=('?', '-'),  # characters that denote missing data.
        strip_inside_brackets=True   # do you want data removed in brackets or not?
    )

    def cmd_download(self, args):
        crawl(self.raw_dir)

    def cmd_makecldf(self, args):
        args.writer.cldf.add_component(
            'CognatesetTable',
            {'name': 'Language_ID', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#languageReference'},
            {'name': 'Form_ID', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#formReference'},
            {'name': 'Comment', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#comment'},
            {'name': 'doubt', 'datatype': 'boolean'},
        )
        args.writer.cldf.add_table(
            'cf.csv',
            {'name': 'ID', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#id'},
            {'name': 'Name', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#name'},
            {'name': 'Comment', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#comment'},
            {'name': 'Cognateset_ID', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#cognatesetReference'},
        )
        args.writer.cldf.add_table(
            'cfitems.csv',
            {'name': 'ID', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#id'},
            {'name': 'Cfset_ID'},
            {'name': 'Form_ID', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#formReference'},
            {'name': 'Source', 'separator': ';', 'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#source'},
        )

        cognates, langs = list(EtymonParser(self.raw_dir)), list(LanguageParser(self.raw_dir))
        args.writer.cldf.sources = Sources.from_file(self.etc_dir / 'sources.bib')
        smap = set(args.writer.cldf.sources.keys())
        l2gl = {l['ID']: l for l in self.languages}

        concepts = set()
        lmap = {}
        forms = collections.defaultdict(dict)
        for lang, _, _ in LANGS:
            if is_proto(lang):
                d = l2gl[slug(lang)]
                d['is_proto'] = True
                args.writer.add_language(**d)
                lmap[lang] = slug(lang)

        for lang in langs:
            assert all(ref.key in smap for ref in lang.refs)
            args.writer.add_language(**l2gl[str(lang.id)])
            lmap[lang.name] = str(lang.id)
            for form in lang.forms:
                cid = slug(form.gloss.markdown.replace('__language_', '')) or 'none'
                if cid not in concepts:
                    args.writer.add_concept(
                        ID=cid,
                        Name=form.gloss.markdown,
                        #Description=form.gloss.markdown,
                    )
                    concepts.add(cid)
                assert not form.gloss.comment
                lex = args.writer.add_form(
                    Language_ID=lang.id,
                    Parameter_ID=cid,
                    Value=form.form,
                    Form=form.form,
                    Comment=form.comment,
                    Source=[str(ref) for ref in lang.refs],
                )
                forms[lang.name][form.form, form.gloss.lookup] = lex

        for cset in cognates:
            cid = slug(cset.gloss) or 'none'
            if cid not in concepts:
                args.writer.add_concept(ID=cid, Name=cset.gloss)  # FIXME: Add tags from finder list!
                concepts.add(cid)
            # Add the reconstruction as form of the proto language:
            pform = args.writer.add_form(
                Language_ID=lmap[cset.proto_lang],
                Parameter_ID=cid,
                Value=cset.key,
                Form=cset.key,
            )
            forms[cset.proto_lang][cset.key, cid] = pform
            # And add this reconstruction to the cognate set:
            args.writer.add_cognate(lexeme=pform, Cognateset_ID=cset.id)

            args.writer.objects['CognatesetTable'].append(dict(
                ID=cset.id,
                Language_ID=lmap[cset.proto_lang],
                Form_ID=pform['ID'],
                Comment=cset.note.markdown if cset.note else None,
                doubt=cset.doubt,
            ))
            for form in cset.forms:
                if form.language in UNKNOWN_LANGS:
                    #print('+++', lname)
                    continue
                if form.is_proto:
                    cid = slug(form.gloss.markdown.replace('__language_', '')) or 'none'
                    if cid not in concepts:
                        args.writer.add_concept(
                            ID=cid,
                            Name=form.gloss.markdown,
                        )
                        concepts.add(cid)
                    lex = args.writer.add_form(
                        Language_ID=lmap[form.language],
                        Parameter_ID=cid,
                        Value=form.form,
                        Form=form.form,
                        Comment=form.comment,
                        Source=[str(ref) for ref in form.gloss.refs],
                    )
                    forms[form.language][form.form, form.gloss.lookup] = lex
                try:
                    cid = form.gloss.lookup
                    cid = {
                        'protonakanaimadiditoshakeasinepilepsycfsaaariritremblebugotuaririshakelauariribeshakenarosiariritremblekwaioalilitremble':
                            'protonakanaimadiditoshakeasinepilepsy',
                        'actofstrugglingasachildgreatactivityinworktostruggletofreeoneselftobeinspasmstostrikeagainandagainonashoaltopoundshowinglossoftbeforek':
                            'actofstrugglingasachildgreatactivityinworktostruggletofreeoneselftobeinspasmstostrikeagainandagainonashoaltopound',
                    }.get(cid, cid)
                    args.writer.add_cognate(
                        lexeme=forms[form.language][form.form, cid],
                        Cognateset_ID=cset.id,
                        Source=[str(ref) for ref in form.gloss.refs],
                        # Comment?
                    )
                except KeyError:
                    # If gloss contains brackets, try to match without brackets!
                    cid = slug(form.gloss.markdown.partition('(')[0].strip()) or 'none'
                    if (form.form, cid) in forms[form.language]:
                        args.writer.add_cognate(
                            lexeme=forms[form.language][form.form, cid],
                            Cognateset_ID=cset.id,
                            Source=[str(ref) for ref in form.gloss.refs if ref.key in smap],
                            Comment=form.gloss.markdown.partition('(')[2].replace(')', '').strip(),
                        )
                    else:
                        print('---', form.language, form.form, form.gloss.markdown, form.gloss.lookup)
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
                        cid = slug(form.gloss.markdown) or 'none'
                        if cid not in concepts:
                            args.writer.add_concept(
                                ID=cid,
                                Name=form.gloss.markdown,
                            )
                            concepts.add(cid)
                        lex = args.writer.add_form(
                            Language_ID=lmap[form.language],
                            Parameter_ID=cid,
                            Value=form.form,
                            Form=form.form,
                        )
                        forms[form.language][form.form, form.gloss.lookup] = lex
                    if (form.form, form.gloss.lookup) not in forms[form.language]:
                        print('+++', form.language, form.form, form.gloss.markdown, slug(form.gloss.markdown) or 'none')
                    else:
                        args.writer.objects['cfitems.csv'].append((dict(
                            ID='{}-{}'.format(cfid, idx + 1),
                            Cfset_ID=cfid,
                            Form_ID=forms[form.language][form.form, form.gloss.lookup]['ID'],
                            Source=[str(ref) for ref in form.gloss.refs if ref.key in smap],
                        )))

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
    """
    import re

    def repl(m):
        res = ''
        for lname, lid in sorted(lmap.items(), key=lambda i: -len(i[0])):
            if m.group('content').startswith(lname):
                res += '[{}](LanguageTable#cldf:{})'.format(lname, lid)
                rem = m.group('content')[len(lname):].strip().replace('&ast;', '').replace('*', '')
                doubt = rem.startswith('(?)')
                if doubt:
                    form = rem.replace('(?)', '').strip()
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
                    print(m.group('content'))
                    res += m.group('content')[len(lname):]
                break
        else:
            res = m.group('content')
        return res

    res = re.sub('__language__(?P<content>.*?)__', repl, s)

    def bib(md):
        if md.url.startswith('bib-'):
            bid = md.url.partition('-')[2]
            if bid not in sources:
                print('Missing source: {}; {}'.format(bid, md.label))
                return md.label
            md.url = 'Sources#cldf:{}'.format(bid)
        return md

    return MarkdownLink.replace(res, bib)
