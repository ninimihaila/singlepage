# coding: utf-8
import base64
import requests
import argparse
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup


parser = argparse.ArgumentParser(description='Save a webpage as a single file.')
parser.add_argument('source',  type=str,
                    help='the source page to save')
parser.add_argument('-o', type=str, dest='out', default='out.html',
                    help='the output file')

args = parser.parse_args()
page = args.source
out = args.out


def inline_scripts(html):
    for el in html.find_all('script'):
        url = el.get('src')
        if url:
            try:
                content = requests.get(url).text
            except Exception as e:
                url = urljoin(page, url)
                content = requests.get(url).text

            el.string = content
            del el['src']


def inline_style(html):
    for el in html.find_all('link'):
        url = el.get('href')
        if url:
            try:
                content = requests.get(url).text
            except Exception as e:
                url = urljoin(page, url)
                content = requests.get(url).text

            el.string = content
            el.name = 'style'
            del el['href']

def inline_images(html):
    for el in html.find_all('img'):
        url = el.get('src')
        if url:
            try:
                content = requests.get(url).content
            except Exception as e:
                url = urljoin(page, url)
                content = requests.get(url).content

            el['src'] = 'data:image/png;base64, ' + base64.b64encode(content).decode('utf-8')


if __name__ == "__main__":
    html = requests.get(page).text
    soup = BeautifulSoup(html, 'html5lib')

    inline_scripts(soup)
    inline_style(soup)
    inline_images(soup)

    with open(out, 'w+') as file:
        file.write(str(soup))

