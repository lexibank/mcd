import re
import functools
import itertools

import attr
from bs4 import Tag, NavigableString, BeautifulSoup as bs
from clldutils.misc import slug, lazyproperty

__all__ = ['LANGS', 'NORM_LANG', 'UNKNOWN_LANGS', 'EtymonParser', 'LanguageParser']


LANGS = {
    ("'Āre'āre", None, "’Āre’āre"),
    ('Fijian', 'Fij', None),
    ('Marshallese', 'Mrs', None),
    ('Mortlockese', 'Mtk', None),
    ('Samoan', 'Sam', None),
    ('Gilbertese', 'Kir', 'Kiribati'),
    ('Chuukese', 'Chk', 'Trukese'),
    ('Kosraean', 'Ksr', 'Kusaiean'),
    ('Pohnpeian', 'Pon', 'Ponapeian'),
    ('Lakalai', None, 'West Nakanai'),
    ('Pingilapese', 'Png', 'Pingelapese'),
    ('Saipan Carolinian', 'Crl', None),
    ('Saipan Carolinian·T', 'Crn', None),
    ('Sonsorolese', 'Sns', None),
    ('Tobi', 'Tob', None),
    ('Ulawan', 'Ula', None),
    ('Ulithian', 'Uli', None),
    ('Woleaian', 'Wol', None),
    ('Proto-Austronesian', 'PAN', None),
    ('Uraustronesisch', None, None),
    ('Proto-Central Micronesian', 'PCMc', 'Proto–Central Micronesian'),
    ('Proto-Western Micronesian', 'PWMc', 'Proto–Western Micronesian'),
    ('Proto-Eastern Oceanic', 'PEO', 'Proto–Eastern Oceanic'),
    ('Proto-Chuukic', 'PCk', None),
    ('Proto-Eastern Oceanic', 'EOc', 'Proto–Eastern Oceanic'),
    ('Proto-Kimbe', None, None),
    ('Proto-Lakalai', None, None),
    ('Proto-Micronesian', 'PMc', None),
    ('Proto-Malayo-Polynesian', None, 'Proto–Malayo-Polynesian'),
    ('Proto-Nakanai', 'PNk', None),
    ('Proto-Oceanic', 'POc', None),
    ('Proto-Pohnpeic', 'PPon', None),
    ('Proto-Pohnpeic-Chuukic', None, 'Proto–Pohnpeic-Chuukic'),
    ('Proto-Polynesian', None, None),
    ('Proto-Western-Malayo-Polynesian', 'PWMP', None),
    ('Proto-Willaumez', None, None),
}
UNKNOWN_LANGS = ['Bau', 'Tik', 'Haw', 'Fiji', 'Micronesian']
NORM_LANG = {abbr: name for name, abbr, _ in LANGS if abbr}
for name, _, alias in LANGS:
    NORM_LANG[name] = name
    if alias:
        NORM_LANG[alias] = name

MULTIREFS = {
    "Blust 1980:39, Blust and Trussel 2010/14": [
        dict(label='Blust 1980:39'),
        dict(label='Blust and Trussel 2010/14'),
    ],
    "Blust 1989:123, Blust and Trussel 2010/14": [
        dict(label='Blust 1989:123'),
        dict(label='Blust and Trussel 2010/14'),
    ],
    "Goodenough (1992 fn. 6, 1997)": [
        dict(label='Goodenough 1992 fn. 6'),
        dict(label='Goodenough 1997'),
    ],
    "Blust 1984/85, Blust and Trussel 2010/14": [
        dict(label='Blust 1984/85'),
        dict(label='Blust and Trussel 2010/14'),
    ],
    "Blust 1989:160, Blust and Trussel 2010/14": [
        dict(label='lust 1989:160'),
        dict(label='Blust and Trussel 2010/14'),
    ],
    "Blust 1983/84:93, Blust and Trussel 2010/14": [
        dict(label='Blust 1983/84:93'),
        dict(label='Blust and Trussel 2010/14'),
    ],
    "Geraghty 1983, 1990": [
        dict(label='Geraghty 1983'),
        dict(label='Geraghty 1990'),
    ],
    "Blust 1980:123, 1983/84:93": [
        dict(label='Blust 1980:123'),
        dict(label='Blust 1983/84:93'),
    ],
    "Jackson (1983:384;1986:229 fn. 4)": [
        dict(label='Jackson 1983:384'),
        dict(label='Jackson 1986:229 fn. 4'),
    ],
    'Goodenough and Sugita 1980, 1990': [
        dict(label='Goodenough and Sugita 1980'),
        dict(label='Goodenough and Sugita 1990'),
    ],
    'Goodenough 1963, 1992': [
        dict(label='Goodenough 1963'),
        dict(label='Goodenough 1992'),
    ]
}


def normalize_string(s):
    return re.sub('\s+', ' ', s.strip())


def parse_form(s, is_proto):
    s = re.sub(r'\s+', ' ', s.strip()).replace('(sic)', '[sic]')
    if is_proto and s.startswith('*'):
        return s[1:].strip()
    return s.replace("ʻ", "'").replace("’", "'")


def _tag(attr, e):
    n = getattr(e, attr)
    if n is None:
        return
    while not isinstance(n, Tag):
        n = getattr(n, attr)
        if n is None:
            return
    return n


next_tag = functools.partial(_tag, 'next_sibling')


def is_proto(name):
    name = NORM_LANG.get(name, name)
    return name.startswith('Proto-') or name == 'Uraustronesisch'


@attr.s
class Item:
    """
    An instance of a data type of the MCD, initialized from an HTML chunk.
    """
    html = attr.ib()

    @classmethod
    def match(cls, e):
        return True

    @classmethod
    def from_html(cls, e):
        if cls.match(e):
            return cls(e)


@attr.s
class FormLike:
    form = attr.ib(default=None)
    gloss = attr.ib(default=None)
    is_proto = attr.ib(default=False)
    comment = attr.ib(default=None)


@attr.s
class Ref(Item):
    key = attr.ib(default=None)
    label = attr.ib(default=None)
    year = attr.ib(default=None)
    pages = attr.ib(default=None)
    second = attr.ib(default=None)

    def __str__(self):
        res = self.key
        if self.pages:
            res += '[{}]'.format(self.pages)
        return res

    @classmethod
    def match(cls, e):
        return isinstance(e, Tag) and (
                ((e.name in {'span', 'a'}) and ('class' in e.attrs) and e.attrs['class'][0] == 'bib') or
                e.name == 'bib')

    def __attrs_post_init__(self):
        if self.label:
            pass
        elif self.html.name == 'bib':
            self.label = self.html.get_text()
        else:
            link = self.html if self.html.name == 'a' else self.html.find('a')
            self.label = link.text

        m = re.search('(?P<year>[0-9]{4}[a-z]?)', self.label)
        if m:
            self.year = m.group('year')
        if self.label.startswith('(') and self.label.endswith(')'):
            self.label = self.label[1:-1].strip()
        self.label = self.label\
            .replace('2010-12', '2010/14') \
            .replace('Ross 1983', 'Ross 1988')\
            .replace('-', '/')\
            .replace('–', '/')\
            .replace(' & ', ' and ') \
            .replace('Kubary 1989', 'Kubary 1889')\
            .replace('Gerahgty', 'Geraghty')
        if self.label == 'Dempwolff':
            self.label = 'Dempwolff 1938'
        if self.label == 'Dyen':
            self.label = 'Dyen 1951'
        if self.label == 'Bingham':
            self.label = 'Bingham 1908'
        if self.label == 'Eastman':
            self.label = 'Eastman 1948'

        if self.label in MULTIREFS:
            first, second = MULTIREFS[self.label]
            self.label = first['label']
            self.second = Ref(html=None, **second)

        if not self.key:
            self.key = self.label.split(':' if ':' in self.label else 'fn.')[0].strip()
        if "’s " in self.key:
            self.key = self.key.replace("’s ", '')
        self.key = self.key.replace('forthcoming', 'nd')
        if ':' in self.label:
            self.pages = self.label.partition(':')[2].strip()
        self.key = slug(self.key)


def norm_gloss(s):
    """
    If "’ (" appear in gloss:
    - split stuff in brackets off into comment on form
    - keep slug with comment for lookup
    """
    s = normalize_string(s).strip()
    s = re.sub(r'\s+\(\)', '', s)
    if s.startswith('·'):
        s = s[1:].strip()
    if s.endswith('.'):
        s = s[:-1].strip()
    if s.startswith('‘') and s.endswith('’'):
        s = s[1:-1].strip()
    return s


def markup(html, markdown='', refs=None):
    refs = [] if refs is None else refs
    skip_lg = False
    for c in html.contents:
        if isinstance(c, NavigableString):
            markdown += str(c)
        else:
            cls = c['class'][0] if 'class' in c.attrs else None
            assert c.name in ['bib', 'pwd', 'wd', 'span', 'i', 'a', 'lg', 'b', 'pn', 'br', 'plg', 'font', 'um', 'plgpn'], str(c)
            if c.name == 'span':
                if cls == 'note':
                    continue
                assert cls in (None, 'wd', 'pwd', 'lg', 'plg', 'bib', 'proto', 'note'), str(c)
            ref = Ref.from_html(c)
            if ref:
                refs.append(ref)
                markdown += '[{}](bib-{})'.format(ref.label, ref.key)
                if ref.second:
                    refs.append(ref.second)
                    markdown += ', [{}](bib-{})'.format(ref.second.label, ref.second.key)
            elif c.name == 'br':
                markdown += '\n\n'
            elif c.name == 'font':
                if 'which we presume to be loans' in c.get_text():
                    skip_lg = True
                    continue
                markdown, refs = markup(c, markdown, refs)
            elif c.name == 'b':
                markdown += '__{}__'.format(c.get_text())
            elif (cls in ('lg', 'plg')) or c.name in ('lg', 'plg', 'plgpn'):
                if skip_lg:
                    skip_lg = False
                    continue
                text = ' '.join(NORM_LANG.get(t, t) for t in c.get_text().split())
                markdown += '__language__{}__'.format(text)
            elif c.name == 'span' and cls is None:
                markdown += c.get_text()
            elif (cls in ('wd', 'pwd', 'proto')) or c.name in ('i', 'pwd', 'wd', 'ha', 'in', 'pn', 'um'):
                markdown += '_{}_'.format(c.text)
            else:
                raise ValueError(str(c))
    return markdown, refs


@attr.s
class Gloss(Item):
    """
    Glosses may contain markup such as refs.

    <span class="FormGloss">type of ocean fish (<span class="bib"><a class="bib" href="acd-bib.htm#Headland">Headland and Headland (1974)</a></span>), kind of marine eel (<span class="bib"><a class="bib" href="acd-bib.htm#Reid">Reid (1971:186)</a></span>)</span>
    """
    refs = attr.ib(default=attr.Factory(list))
    markdown = attr.ib(default='')
    lookup = attr.ib(default='')
    comment = attr.ib(default='')

    @lazyproperty
    def cid(self):
        return slug(self.markdown.replace('__language_', '')) or 'none'

    @classmethod
    def match(cls, e):
        return isinstance(e, Tag) and e.name == 'span' and \
               ('class' in e.attrs) and e['class'][0] == 'FormGloss'

    def __attrs_post_init__(self):
        # Strip refs and markup
        self.markdown, self.refs = markup(self.html)
        self.markdown = norm_gloss(self.markdown)
        self.lookup = slug(re.sub(r'\[[^]]+]\(bib-[^)]+\)', '', self.markdown.replace('__language_', ''))) or (self.refs[0].label if self.refs else '') or 'none'
        loss_of = '(showing loss of'
        if loss_of in self.markdown:
            self.markdown, _, self.comment = self.markdown.partition(loss_of)
            self.markdown = self.markdown.strip()
            self.comment = (loss_of[1:] + self.comment.replace(')', '')).strip()
        elif '_Cf._' in self.markdown:
            # <i>Cf.</i> introduces comment!
            self.markdown, _, self.comment = self.markdown.partition('_Cf._')
            self.markdown = self.markdown.strip()
            self.comment = self.comment.strip()
        elif '’ (' in self.markdown:
            self.markdown, _, self.comment = self.markdown.partition('’ (')
        elif '(bib-' in self.markdown:
            self.markdown, _, self.comment = self.markdown.partition('[')
            self.comment = '[' + self.comment
            self.markdown = self.markdown.strip()

        if self.comment:
            if self.comment.endswith(')'):
                self.comment = self.comment[:-1].strip()
            if self.markdown.startswith('‘'):
                self.markdown = self.markdown[1:].strip()
        #
        # FIXME: look for "loan(s) from" inside brackets!
        # (showing loss of ... -> comment!
        #


@attr.s
class Note(Item):
    refs = attr.ib(default=attr.Factory(list))
    markdown = attr.ib(default='')

    @classmethod
    def match(cls, e):
        return isinstance(e, Tag) and e.name == 'p' and (e['class'][0] == 'note')

    def __attrs_post_init__(self):
        html = self.html
        while True:
            self.markdown, self.refs = markup(html, self.markdown, self.refs)
            html = next_tag(html)
            if not Note.match(html):
                break
            self.markdown += '\n\n'
        self.markdown = self.markdown.strip().replace('*', '&ast;')


@attr.s
class Etymon(Item):
    id = attr.ib(default=None)
    reconstruction = attr.ib(default=None)
    key = attr.ib(default=None)
    gloss = attr.ib(default=None)
    proto_lang = attr.ib(default=None)
    forms = attr.ib(default=attr.Factory(list))
    note = attr.ib(default=None)
    cf_forms = attr.ib(default=attr.Factory(list))
    doubt = attr.ib(default=False)

    def __attrs_post_init__(self):
        p = self.html
        self.id = None
        while not self.id:
            p = p.previous_sibling
            if p.name == 'a':
                try:
                    self.id = int(p['name'])
                except ValueError:
                    pass
        assert self.id
        self.reconstruction = self.html.find('span', class_='pwd').get_text().strip()
        self.key = self.reconstruction.replace(' *', ' ')
        if self.key.startswith('*'):
            self.key = self.key[1:].strip()
        self.gloss = self.html.find('span', class_='mpgloss').get_text().strip()
        self.proto_lang = self.html.find('span', class_='mplang').get_text().strip()
        if '(?)' in self.proto_lang:
            self.proto_lang = self.proto_lang.replace('(?)', '').strip()
            self.doubt = True
        self.proto_lang = NORM_LANG[self.proto_lang]

        for p in self.html.find_all('p', class_=True):
            if 'note' in p.attrs['class']:
                self.note = Note.from_html(p)
                break

        lname = None
        forms = self.html.find('table', class_='forms')
        for tr in forms.find_all('tr'):
            self.forms.append(Form.from_html_and_language(tr, lname))
            ln = tr.find('td').get_text().strip()
            if ln:
                lname = NORM_LANG.get(ln, ln)

        for forms in self.html.find_all('table', class_='cf'):
            header, comment, fs = forms.find_previous_sibling('p').get_text(), None, []
            for tr in forms.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) == 1:
                    comment = tds[0].get_text()
                else:
                    fs.append(Form.from_html_and_language(tr, lname))
                    ln = tr.find('td').get_text().strip()
                    if ln:
                        lname = NORM_LANG.get(ln, ln)
            self.cf_forms.append((header.replace('—', '').strip(), comment, fs))

        return


@attr.s(auto_detect=True)
class LForm(Item, FormLike):
    def __attrs_post_init__(self):
        link = self.html.find('a', href=True)
        self.form = parse_form(link.text.strip(), True)
        self.gloss = Gloss(self.html.find('span', class_='formdef'))
        if self.gloss.comment:
            self.comment, self.gloss.comment = self.gloss.comment, ''


@attr.s
class Language(Item):
    id = attr.ib(default=None)
    name = attr.ib(default=None)
    nwords = attr.ib(default=None)
    refs = attr.ib(default=attr.Factory(list))
    forms = attr.ib(default=attr.Factory(list))
    is_proto = attr.ib(default=False)

    def __attrs_post_init__(self):
        self.name = self.html.find('span', class_='langname').get_text()
        self.name = NORM_LANG.get(self.name, self.name)
        self.id = int(self.html.find('a')['name'])
        self.nwords = int(self.html.find('span', class_='langcount').text.replace('(', '').replace(')', ''))

        for e in self.html.find_all('a', class_='bib'):
            ref = Ref.from_html(e)
            if ref:
                self.refs.append(ref)

        form = next_tag(self.html)
        while (len(self.forms) < self.nwords) or \
                (form and form.name == 'p' and form['class'][0] == 'formline') or \
                (form and form.name == 'p' and form['class'][0] == 'lbreak'):
            if form is None or form.name != 'p':
                break
            if form['class'][0] == 'lbreak':
                form = next_tag(form)
            if form.name != 'p':
                break
            assert form['class'][0] == 'formline'
            self.forms.append(LForm(html=form, is_proto=self.is_proto))
            form = next_tag(form)

        assert self.nwords + 20 > len(self.forms) >= self.nwords
        # Merge forms:
        dedup = []
        for _, forms in itertools.groupby(
                sorted(self.forms, key=lambda f: (f.form, f.gloss.markdown)), lambda f: (f.form, f.gloss.markdown)
        ):
            for i, f in enumerate(forms):
                if i == 0:
                    form = f
                else:
                    assert f.gloss.markdown == form.gloss.markdown
            dedup.append(form)

        self.forms = dedup
        self.is_proto = is_proto(self.name)


@attr.s
class Form(Item, FormLike):
    """
    """
    language = attr.ib(default=None)
    doubt = attr.ib(default=False)

    @classmethod
    def from_html_and_language(cls, e, lname):
        res = cls.from_html(e)
        if lname and not res.language:
            res.language = lname
        return res

    def __attrs_post_init__(self):
        pollex_p = re.compile(r'http://pollex\.org\.nz/entry/(?P<entry>[^/]+)/')
        lg, form, gloss = self.html.find_all('td')
        self.gloss = Gloss(html=gloss)
        if self.gloss.comment:
            self.comment, self.gloss.comment = self.gloss.comment, ''
        for e in form.find_all('a', href=True):
            m = pollex_p.match(e.attrs['href'])
            if m:
                self.gloss.refs.append(Ref(html=None, label='POLLEX: {}'.format(m.group('entry'))))
                break
        self.language = NORM_LANG.get(lg.get_text().strip(), lg.get_text().strip())
        self.is_proto = is_proto(self.language)
        self.form = parse_form(form.get_text(), is_proto=self.language.startswith('Pr'))
        if self.form.startswith('(?)'):
            self.form, self.doubt = self.form.replace('(?)', '').strip(), True
        if self.form.startswith('*'):
            self.form = self.form[1:].strip()




class Parser:
    """
    A Parser is concerned with one main data type. As such it knows
    - how to select appropriate HTML input files
    - how to iterate over suitable HTML chunks, encoding the data of an object instance.
    """
    __tag__ = (None, None)
    __cls__ = None
    __glob__ = 'pmc-*.htm'

    def __init__(self, d):
        patterns = [self.__glob__] if isinstance(self.__glob__, str) else self.__glob__
        self.paths = list(itertools.chain(
            *[sorted(list(d.glob(g)), key=lambda p: p.name) for g in patterns]))

    @staticmethod
    def fix_html(s):
        for src, t in [
            ('<<', '&lt;<'),
            ('<!--/span-->', '</span>'),
        ]:
            s = s.replace(src, t)
        s = '\n'.join([l for l in s.split('\n') if 'p class="indexline2"' not in l])
        s = re.sub(r'<!--[^-]+-->', '', s)
        return s

    def iter_html(self):
        for p in self.paths:
            yield bs(self.fix_html(p.read_text(encoding='utf8')), 'lxml')

    def __iter__(self):
        seen = set()
        for html in self.iter_html():
            items = [
                i for i in html.find_all(self.__tag__[0], class_=True)
                if i.attrs['class'][0] == self.__tag__[1]]
            for e in items:
                o = self.__cls__.from_html(e)
                if o:
                    oid = getattr(o, 'id', None)
                    if not oid or (oid not in seen):
                        yield o
                    seen.add(oid)


class EtymonParser(Parser):
    __glob__ = 'pmc-sets-*.htm'
    __cls__ = Etymon
    __tag__ = ('table', 'main')


class LanguageParser(Parser):
    __glob__ = 'pmc-langs-*.htm'
    __cls__ = Language
    __tag__ = ('p', 'langline')
