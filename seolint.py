import gevent
from gevent import monkey
monkey.patch_all()

import re
from urllib import urlopen
from argparse import ArgumentParser
from collections import defaultdict
from operator import itemgetter
from lxml.cssselect import CSSSelector
from lxml.html import parse
from lxml import etree
import logging

logger = logging.getLogger(__name__)

def extract_keywords(text):
    # We probably don't care about words shorter than 3 letters
    min_word_size = 3
    if text:
        #print text.encode("utf-8")
        re_search = re.compile(r'[^\w0-9\-\']', re.UNICODE)
        return [kw.lower()
                for kw in re.sub(re_search, ' ', text).split()
                    if kw not in get_stop_words() and len(kw) >= min_word_size]
    else:
        return []


def keywords_for_tag(tree, tag, attr=None):
    sel = CSSSelector(tag)
    keywords = []
    sel_tree = sel(tree)
    for e in sel_tree:
        if attr:
            text = e.get(attr, '')
            keywords.append(text)
        else:
            text = e.text
            keywords.extend(extract_keywords(text))
    keywords = " ".join(keywords)
    return len(sel_tree), keywords


def print_keywords(title, args_kw):
    count, kw = args_kw
    count_kw = len(kw)
    if kw:
        return {'keywords':{'tag': title, 'count':count, 'content':kw}}


def tags(tree):
    check_tags = ['title', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                  'strong', 'em', 'p', 'li']
    result =[]
    for tag in check_tags:
        res = print_keywords(tag, keywords_for_tag(tree, tag))
        result.append(res)

    check_attrs = [('img', 'alt'), ('img', 'title'), ('img', 'src')]
    for tag, attr in check_attrs:
        res = print_keywords("%s:%s" % (tag, attr),
                       keywords_for_tag(tree, tag, attr))
        result.append(res)
    return result


def count_keywords(tree):
    keywords = defaultdict(int)
    for e in tree.iter():
        if e.tag not in ('script', 'style'):
            for kw in extract_keywords(e.text):
                keywords[kw] += 1.0
    return (keywords.items(), sum(count for count in keywords.values()))


def frequency(tree, ngram_size=1):
    result = []
    if ngram_size == 1:
        keywords, total = count_keywords(tree)
    else:
        keywords, total = count_ngrams(tree, ngram_size)
    keywords.sort(key=itemgetter(1), reverse=True)
    for kw, count in keywords:
        if count > 1:
            res = {'times': count, 'kw': kw, 'rate':"%.2f%%" %  ((count / total) * 100)}
            result.append(res)
    return result


def count_ngrams(tree, size):
    text = []
    ngrams = defaultdict(int)
    for e in tree.iter():
        if e.tag not in ('script', 'style'):
            text.extend(extract_keywords(e.text))

    for ii in xrange(len(text)):
        ngram = text[ii:ii+size]
        ngrams[' '.join(ngram)] += 1.0

    return (ngrams.items(), sum(count for count in ngrams.values()))


def get_stop_words():
    return ('a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that',
            'the', 'to', 'was', 'were', 'will', 'with')


def get_http_status(url):
    if url.startswith('http'):
        return urlopen(url.encode("utf-8")).getcode()
    else:
        return 'UNKNOWN'

def check_links(url, tree, timeout=20):
    root = tree.getroot()
    root.make_links_absolute(url)
    urls = set()
    for el, attr, link, pos in root.iterlinks():
        urls.add(link)

    job_urls = {}
    jobs = []
    for url in urls:
        job = gevent.spawn(get_http_status, url)
        jobs.append(job)
        job_urls[job] = url

    results = []
    gevent.joinall(jobs, timeout=timeout)
    for job in jobs:
        url = job_urls[job]
        if job.value:
            status = job.value
        else:
            status = 'TIMEOUT'
        if status != 200:
            results.append({'url': url, 'status':status})
    return results

def url_open(url):
    print url
    webf = urlopen(url)
    tree = parse(webf)
    return tree

def main():
    p = ArgumentParser(description='Checks on-page factors. Very basic.')
    p.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                   help='print detailed output')
    p.add_argument('-t', '--timeout', dest='timeout', type=int,
                   default=20,
                   help='timeout in seconds (default 20)')
    p.add_argument('action', type=str,
                   choices=('tags', 'frequency', 'digrams', 'trigrams',
                            'check-links')),
    p.add_argument('url', type=str,
                   help='url to check')
    args = p.parse_args()
#    webf = urlopen(args.url)
#    tree = parse(webf)
    tree = url_open(args.url)

    if args.action == 'tags':
        return tags(tree)
    elif args.action == 'frequency':
        return frequency(tree)
    elif args.action == 'digrams':
        return frequency(tree, ngram_size=2)
    elif args.action == 'trigrams':
        return frequency(tree, ngram_size=3)
    elif args.action == 'check-links':
        return check_links(args.url, tree, timeout=args.timeout)


if __name__ == '__main__':
    import json
    print json.dumps(main())
