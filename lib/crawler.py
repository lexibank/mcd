import io

import requests

from lxml.etree import HTMLParser, parse


def crawl(d):
    def get(url):
        p = d / url
        if not p.exists():
            p.write_text(requests.get('https://www.trussel2.com/MCD/' + url).text, encoding='utf8')
        return parse(io.StringIO(p.read_text(encoding='utf8')), HTMLParser())

    def pagename(href):
        href = href.partition('#')[0]
        if href.startswith('pmc'):
            return href

    get('pmc-intro.htm')
    seen = {p.name for p in d.glob('pmc-*')}
    while True:
        new = set()
        for p in d.glob('pmc*'):
            res = get(p.name)
            if res:
                for a in res.findall('.//a[@href]'):
                    page = pagename(a.attrib['href'])
                    if page and page not in seen:
                        if get(page):
                            new.add(page)
                            seen.add(page)
        if not new:
            break
