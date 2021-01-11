#!/usr/bin/env python

"""Small static site generator.

"""


__author__ = "Bastian Venthur <venthur@debian.org>"


import argparse
import os
import shutil
import string
import codecs
import re
import logging
from datetime import datetime

import markdown
from jinja2 import Environment, FileSystemLoader
import feedgenerator

logger = logging.getLogger(__name__)
logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
)


def main(args=None):
    args = parse_args(args)
    args.func(args)


def parse_args(args):
    """Parse command line arguments.

    Paramters
    ---------
    args :
        optional parameters, used for testing

    Returns
    -------
    args

    """
    parser = argparse.ArgumentParser()

    commands = parser.add_subparsers(dest='command')
    commands.required = True

    build_parser = commands.add_parser('build')
    build_parser.set_defaults(func=build)
    build_parser.add_argument(
            '-i', '--input-dir',
            default='content',
            help='Input directory (default: content)',
    )
    build_parser.add_argument(
            '-o', '--output-dir',
            default='build',
            help='Ouptut directory (default: build)',
    )

    return parser.parse_args()


def build(args):
    os.makedirs(f'{args.output_dir}', exist_ok=True)
    convertibles = []
    for root, dirnames, filenames in os.walk(args.input_dir):
        for filename in filenames:
            relpath = os.path.relpath(f'{root}/{filename}', start=args.input_dir)
            abspath = os.path.abspath(f'{root}/{filename}')
            # all non-markdown files are just copied over, the markdown
            # files are converted to html
            if abspath.endswith('.md'):
                dstpath = os.path.abspath(f'{args.output_dir}/{relpath}')
                dstpath = dstpath[:-3] + '.html'
                convertibles.append((abspath, dstpath))
            else:
                shutil.copy(abspath, f'{args.output_dir}/{relpath}')
        for dirname in dirnames:
            # all directories are copied into the output directory
            path = os.path.relpath(f'{root}/{dirname}', start=args.input_dir)
            os.makedirs(f'{args.output_dir}/{path}', exist_ok=True)

    convert_to_html(convertibles)


def convert_to_html(convertibles):

    env = Environment(
            loader=FileSystemLoader(['templates']),
    )

    md = markdown.Markdown(
            extensions=['meta', 'fenced_code', 'codehilite'],
            output_format='html5',
    )

    pages = []
    articles = []

    for src, dst in convertibles:
        logger.debug(f'Processing {src}')
        with open(src, 'r') as fh:
            body = fh.read()
        md.reset()
        content = md.convert(body)
        meta = md.Meta
        # convert markdown's weird format to str or list[str]
        for key, value in meta.items():
            value = '\n'.join(value).split(',')
            value = [v.strip() for v in value]
            if len(value) == 1:
                value = value[0]
            meta[key] = value

        context = dict(content=content)
        context.update(meta)
        # for now, treat all pages as articles
        if not meta:
            pages.append((dst, context))
            #template = env.get_template('page.html')
        else:
            articles.append((dst, context))
            #template = env.get_template('article.html')
        template = env.get_template('article.html')
        result = template.render(context)
        with open(dst, 'w') as fh_dest:
            fh_dest.write(result)

    # generate feed
    feed = feedgenerator.Atom1Feed(
            link='https://venthur.de',
            title='my title',
            description='basti"s blag',
    )

    for dst, context in articles:
        feed.add_item(
            title=context['title'],
            link=dst,
            description=context['title'],
            content=context['content'],
            pubdate=datetime.fromisoformat(context['date']),
        )

    with open('atom.xml', 'w') as fh:
        feed.write(fh, encoding='utf8')
    # generate archive
    # generate tags

if __name__ == '__main__':
    main()
