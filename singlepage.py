# coding: utf-8
import base64
import requests
import argparse
import asyncio
import imghdr
from urllib.parse import urlparse, urljoin

import aiohttp
from bs4 import BeautifulSoup
import tqdm


#====== Async IO =======
async def aiohttp_get(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.read()

async def fetch_async(url):
    response = await aiohttp_get(url)
    return url, response

async def load_urls(urls, cache):
    tasks = [asyncio.ensure_future(fetch_async(url)) for url in urls]
    for future in tqdm.tqdm(asyncio.as_completed(tasks), total=len(tasks)):
        url, response = await future
        cache[url] = response
#=======================

def get_image_type(content):
    """
    Gets the image type of the file based on the header
    Returns 'jpeg' if the file is a jpeg, 'png' if it is a png, etc.
    For a list of all the values, see https://docs.python.org/3/library/imghdr.html
    """
    return imghdr.what('', content[:32])

def walk_dom(html, tag, attr):
    """
    An iterator over the elements that have the given attr
    """
    for el in html.find_all(tag):
        if el.has_attr(attr):
            yield el

def get_url(url, page):
    if not urlparse(url).netloc:
        # we have a relative path
        url = urljoin(page, url)
    return url

def aggregate_dom_links(html, tags, page):
    for tag, attr in tags:
        for el in walk_dom(html, tag, attr):
            yield get_url(el.get(attr), page)


def inline(html, tag, attr, cache, page, get_content, replace):
    for el in walk_dom(html, tag, attr):
        url = get_url(el.get(attr), page)

        response = cache.get(url)
        try:
            content = get_content(response)
        except Exception as e:
            print(f'WARNING: {e}')
            continue

        replace(el, content)


def inline_scripts(html, cache, page):
    def replace(el, content):
        el.string = content
        del el['src']

    inline(html, 'script', 'src', cache, page, lambda r: r.decode(), replace)


def inline_style(html, cache, page):
    def replace(el, content):
        el.string = content
        el.name = 'style'
        del el['href']

    inline(html, 'link', 'href', cache, page, lambda r: r.decode(), replace)


def inline_images(html, cache, page):
    def replace(el, content):
        image_type = get_image_type(content)
        el['src'] = f'data:image/{image_type};base64, ' + base64.b64encode(content).decode('utf-8')

    inline(html, 'img', 'src', cache, page, lambda r: r, replace)


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

    tags = [
        ('script', 'src'),
        ('link', 'href'),
        ('img', 'src'),
    ]

    # download
    cache = {}

    print('Downloading resources...')
    ioloop = asyncio.get_event_loop()
    ioloop.run_until_complete(load_urls(aggregate_dom_links(soup, tags, page), cache))

    # inline
    inline_scripts(soup, cache, page)
    inline_style(soup, cache, page)
    inline_images(soup, cache, page)

    with open(out, 'w+') as file:
        file.write(str(soup))

