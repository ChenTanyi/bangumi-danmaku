#!/usr/bin/env python3
import io
import os
import re
import sys
import json
import glob
import logging
import requests
import datetime

OUTPUT_FOLDER = ''
OUTPUT_FILTER = 'd:/movie/test/*[[]{:0>2s}[]]*.mkv'


def convert_to_ass(input_file, output_file):
    os.system(
        f'python danmaku2ass.py -s 1920x1080 -a 0.25 -dm 25 -ds 25 -o "{output_file}" "{input_file}"'
    )


class Bilibili():

    @staticmethod
    def comment_api(cid):
        return f'http://comment.bilibili.com/{cid}.xml'

    @staticmethod
    def bangumi_api(sid):
        return f'https://api.bilibili.com/pgc/review/user?media_id={sid}'

    @staticmethod
    def bangumi_list_api(sid):
        return f'https://api.bilibili.com/pgc/web/season/section?season_id={sid}'

    @staticmethod
    def request(uri):
        r = requests.get(uri)
        r.raise_for_status()
        if r.ok:
            return r.content
        else:
            raise Exception(
                f'Request error: status {r.status_code}, reason {r.reason}')

    def run(self, uri):
        m = re.match(r'https?://(?:www\.)?bilibili\.com/bangumi/media/md(\d+)',
                     uri)
        if m:
            return self.download_bangumi_list(m.group(1))
        m = re.match(r'https?://(?:www\.)?bilibili\.com/bangumi/play/ep(\d+)',
                     uri)
        if m:
            return self.download_bangumi(uri)

        logging.error(f'Unsupport uri: {uri}')

    def download_bangumi(self, uri):
        html_content = self.request(uri).decode()
        initial_state_match = re.search(
            r'__INITIAL_STATE__=(.*?);\(function\(\)', html_content)
        if not initial_state_match:
            logging.error('Cannot extra __INITIAL_STATE__')
            return
        initial_state = json.loads(initial_state_match.group(1))

        ep_len = len(initial_state['epList'])
        if ep_len > 1:
            logging.warning(f'This bangumi currently has {ep_len} videos.')

        ep_id = initial_state['mediaInfo']['id']
        bangumi_title = initial_state['mediaInfo']['title']

        now = datetime.datetime.now().strftime('%Y.%m.%d')
        cid = initial_state['epInfo']['cid']
        title = initial_state['epInfo']['longTitle']
        index = initial_state['epInfo']['title']

        filename = f'downloads/{ep_id}.{bangumi_title}/{cid}.{title}[{index:0>2s}].{now}.xml'
        self.download_comments(cid, filename, index)

    def download_bangumi_list(self, sid):
        bangumi = json.loads(self.request(self.bangumi_api(sid)))
        if bangumi.get('code') == 0 and bangumi.get('message') == 'success':
            bangumi_title = bangumi['result']['media']['title']
        else:
            logging.error(f'Get bangumi error: {bangumi}')
            return

        if bangumi['result'].get('media', dict()).get('season_id'):
            sid = bangumi['result']['media']['season_id']
        bangumi_list = json.loads(self.request(self.bangumi_list_api(sid)))
        if bangumi_list.get('code') == 0 and bangumi_list.get(
                'message') == 'success':
            now = datetime.datetime.now().strftime('%Y.%m.%d')
            for episode in bangumi_list['result']['main_section']['episodes']:
                title = episode['long_title']
                index = episode['title']
                cid = episode['cid']

                filename = f'downloads/{sid}.{bangumi_title}/{cid}.{title}[{index:0>2s}].{now}.xml'
                self.download_comments(cid, filename, index)
        else:
            logging.error(f'Get bangumi list error: {bangumi_list}')
            return

    def download_comments(self, cid, filename, index = None):
        global OUTPUT_FILTER, OUTPUT_FOLDER
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname, exist_ok = True)

        with open(filename, 'wb') as f:
            f.write(self.request(self.comment_api(cid)))

        convert_to_ass(filename, f'{filename}.danmaku.ass')

        cwd = os.curdir
        try:
            if 'OUTPUT_FOLDER' in globals() and OUTPUT_FOLDER:
                os.chdir(OUTPUT_FOLDER)

            if 'OUTPUT_FILTER' in globals() and OUTPUT_FILTER:
                try:
                    output_filter = OUTPUT_FILTER.format(index)
                except:
                    output_filter = OUTPUT_FILTER

                if os.path.exists(output_filter):
                    convert_to_ass(filename, f'{output_filter}.danmaku.ass')
                else:
                    for f in glob.glob(output_filter):
                        convert_to_ass(filename, f'{f}.danmaku.ass')
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    logging.basicConfig(format = '%(asctime)s %(levelname)s %(message)s')
    if len(sys.argv) > 2:
        OUTPUT_FILTER = sys.argv[2]

    if len(sys.argv) > 3:
        OUTPUT_FOLDER = sys.argv[3]

    if len(sys.argv) < 2:
        print(f'Usage: {sys.argv[0]} uri')
    else:
        Bilibili().run(sys.argv[1])
