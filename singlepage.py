# coding: utf-8
import base64
import requests
import argparse
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup


def inline(html, tag, src, get_content, replace):
    for el in html.find_all(tag):
        url = el.get(src)
        if url:
            if not urlparse(url).netloc:
                # we have a relative path
                url = urljoin(page, url)

            response = requests.get(url)
            content = get_content(response)

            replace(el, content)


def inline_scripts(html, page):
    def replace(el, content):
        el.string = content
        del el['src']

    inline(html, 'script', 'src', lambda r: r.text, replace)


def inline_style(html, page):
    def replace(el, content):
        el.string = content
        el.name = 'style'
        del el['href']

    inline(html, 'link', 'href', lambda r: r.text, replace)


def inline_images(html, page):
    def replace(el, content):
        el['src'] = 'data:image/png;base64, ' + base64.b64encode(content).decode('utf-8')

    inline(html, 'img', 'src', lambda r: r.content, replace)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Save a webpage as a single file.')
    parser.add_argument('source',  type=str,
                        help='the source page to save')
    parser.add_argument('-o', type=str, dest='out', default='out.html',
                        help='the output file')

    args = parser.parse_args()
    page = args.source
    out = args.out

    html = requests.get(page).text
    soup = BeautifulSoup(html, 'html5lib')

    inline_scripts(soup, page)
    inline_style(soup, page)
    inline_images(soup, page)

    with open(out, 'w+') as file:
        file.write(str(soup))

