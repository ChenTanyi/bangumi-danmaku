#!/usr/bin/env python3
import os
import re
import sys
import glob
import json
import hashlib
import logging
import requests


def convert_to_ass(input_file, output_file):
    os.system(
        f'python danmaku2ass.py -s 1920x1080 -a 0.25 -dm 25 -ds 25 -f Tudou2 -o "{output_file}" "{input_file}"'
    )


class Youku():

    @staticmethod
    def comment_api(mat, vid):
        return f'https://service.danmu.youku.com/list?mat={mat}&ct=1001&iid={vid}'

    def run(self, uri):
        resp = requests.get(uri)
        resp.raise_for_status()
        content = resp.text

        title = re.search(r'<title>(.*)</title>',
                          content).group(1).split('-')[0]
        vid = re.search(r'videoId: \'(\d*)\'', content).group(1)
        duration = float(re.search(r'seconds: \'(.*)\',', content).group(1))

        results = []
        for mat in range(int(duration) // 60 + 2):
            resp = requests.get(self.comment_api(mat, vid))
            resp.raise_for_status()
            results = results + resp.json().get('result', [])

        self.write_comment({'result': results}, f'downloads/{title}.json')

    def write_comment(self, comments, filename):
        global OUTPUT_FILTER
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok = True)

        with open(filename, 'w', encoding = 'utf-8') as fout:
            json.dump(comments, fout, ensure_ascii = False, indent = 2)

        if 'OUTPUT_FILTER' in globals() and OUTPUT_FILTER:
            if os.path.exists(OUTPUT_FILTER):
                convert_to_ass(filename, f'{OUTPUT_FILTER}.danmaku.ass')
            else:
                for f in glob.glob(OUTPUT_FILTER):
                    convert_to_ass(filename, f'{f}.danmaku.ass')
        else:
            convert_to_ass(filename, f'{filename}.danmaku.ass')


if __name__ == "__main__":
    logging.basicConfig(format = '%(asctime)s %(levelname)s %(message)s')
    if len(sys.argv) > 2:
        OUTPUT_FILTER = sys.argv[2]

    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} uri')
    else:
        Youku().run(sys.argv[1])