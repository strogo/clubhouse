#
# Copyright © 2020 Endless OS Foundation LLC.
#
# This file is part of clubhouse
# (see https://github.com/endlessm/clubhouse).
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#


import gi
gi.require_version('EosMetrics', '0')
from gi.repository import EosMetrics, GLib

from eosclubhouse import config
from eosclubhouse.utils import convert_variant_arg
from eosclubhouse.network import NetworkManager

import datetime
import json
import os
import persistqueue
import random
import string
import threading
import urllib
import urllib.parse

from http import client

import logging
_logger = logging.getLogger(__name__)


UNIQUE_VISITOR_ID = None
UNIQUE_VISITOR_ID_LOCK = threading.Lock()


Events = {
    # Metrics event ids
    'CLUBHOUSE_NEWS_QUEST_LINK': 'ebffecb9-7b31-4c30-a9a0-f896aaaa5b4f',
    'CLUBHOUSE_SET_PAGE': '2c765b36-a4c9-40ee-b313-dc73c4fa1f0d',
    'CLUBHOUSE_PATHWAY_ENTER': '600c1cae-b391-4cb4-9930-ea284792fdfb',

    # Libquest event ids
    'QUEST': '50aebb1b-7a93-4caf-8698-3a601a0fc0f6',
    'PROGRESS_UPDATE': '3a037364-9164-4b42-8c07-73bcc00902de',

    # Achievements event ids
    'ACHIEVEMENT_POINTS': '86521913-bfa3-4d13-b511-a03d4e339d2f',
    'ACHIEVEMENT': '62ce2e93-bfdc-4cae-af4c-54068abfaf02',
}


def record(event, payload):
    if config.USE_EOSMETRICS:
        record_eosmetrics(event, payload)
    else:
        record_matomo_metrics(event, payload)


def record_start(event, key, payload):
    if config.USE_EOSMETRICS:
        record_eosmetrics_start(event, key, payload)
    else:
        record_matomo_start(event, key, payload)


def record_stop(event, key, payload):
    if config.USE_EOSMETRICS:
        record_eosmetrics_stop(event, key, payload)
    else:
        record_matomo_stop(event, key, payload)


# eos-metrics

def record_eosmetrics(event, payload):
    recorder = EosMetrics.EventRecorder.get_default()
    variant = convert_variant_arg(payload)
    recorder.record_event(Events[event], variant)


def record_eosmetrics_start(event, key, payload):
    recorder = EosMetrics.EventRecorder.get_default()
    key = convert_variant_arg(key)
    variant = convert_variant_arg(payload)
    recorder.record_start(Events[event], key, variant)


def record_eosmetrics_stop(event, key, payload):
    recorder = EosMetrics.EventRecorder.get_default()
    key = convert_variant_arg(key)
    variant = convert_variant_arg(payload)
    recorder.record_stop(Events[event], key, variant)


# matomo metrics

def request(path, params, method='GET'):
    ''' Creates the http request to matomo server '''

    url = urllib.parse.urlparse(config.MATOMO)
    connection = client.HTTPConnection
    if url.scheme == 'https':
        connection = client.HTTPSConnection

    conn = connection(url.hostname, url.port)
    headers = {
        'User-Agent': 'clubhouse metrics',
    }
    params = urllib.parse.urlencode(params)
    path = f'{path}?{params}'
    conn.request(method, path, headers=headers)
    response = conn.getresponse()
    if response.status != 200:
        _logger.error('Error sending metrics: %s', response.reason)
        _logger.error('Error sending metrics: %s', response.read())
        return False

    return True


class Queue:
    @classmethod
    def _getq(klass):
        path = os.path.join(GLib.get_user_data_dir(), 'metrics.db')
        return persistqueue.SQLiteQueue(path, auto_commit=True)

    @classmethod
    def put(klass, data):
        q = klass._getq()
        q.put(data)

    @classmethod
    def get(klass):
        q = klass._getq()
        try:
            return q.get(block=False)
        except persistqueue.exceptions.Empty:
            return None

    @classmethod
    def dequeue(klass, callback):
        data = klass.get()
        while data:
            if not callback(data):
                return False
            data = klass.get()


def dequeue():
    ''' If there's connection tries to dequeue all records and send to matomo
    '''

    if not NetworkManager.is_connected():
        return
    threading.Thread(target=Queue.dequeue, args=(_record_matomo, )).start()


def _record_matomo(data):
    if not NetworkManager.is_connected():
        Queue.put(data)
        return False

    if not request('/matomo.php', data):
        Queue.put(data)
        return False

    # dequeue when this works, so we'll try to empty the queue after a
    # successful query
    dequeue()
    return True


def unique_visitor_id():
    ''' Get or generate a random unique visitor id

    This visitor id will be stored in the filesystem so it will be the same in
    the future.
    '''

    global UNIQUE_VISITOR_ID
    global UNIQUE_VISITOR_ID_LOCK

    if UNIQUE_VISITOR_ID:
        return UNIQUE_VISITOR_ID

    UNIQUE_VISITOR_ID_LOCK.acquire()
    id_path = os.path.join(GLib.get_user_data_dir(), 'clubhouse-user-id')
    if os.path.exists(id_path):
        with open(id_path) as f:
            UNIQUE_VISITOR_ID = f.read()
    else:
        with open(id_path, 'w') as f:
            UNIQUE_VISITOR_ID = ''.join(random.sample(string.ascii_letters, k=40))
            f.write(UNIQUE_VISITOR_ID)
    UNIQUE_VISITOR_ID_LOCK.release()

    return UNIQUE_VISITOR_ID


def _get_matomo_data():
    now = datetime.datetime.now()
    data = {
        'idsite': config.MATOMO_SITE_ID,
        'rec': '1',
        'apiv': '1',
        '_id': unique_visitor_id(),
        'rand': ''.join(random.sample(string.ascii_letters, k=20)),
        'h': now.hour,
        'm': now.minute,
        's': now.second,
    }
    return data


def _build_fake_url(data, base='https://hack-computer.com/'):
    if isinstance(data, tuple) or isinstance(data, list):
        values = [_build_fake_url(v, base='') for v in data]
        return base + '/'.join(values)

    if isinstance(data, dict):
        return base + '?' + urllib.parse.urlencode(data)

    return base + str(data)


def record_matomo_metrics(event, payload):
    base = f'https://hack-computer.com/{event}/'
    data = {
        **_get_matomo_data(),
        'action_name': event,
        'cvar': json.dumps(payload),
        'url': _build_fake_url(payload, base),
    }
    threading.Thread(target=_record_matomo, args=(data, )).start()


def record_matomo_start(event, key, payload):
    base = f'https://hack-computer.com/{event}/{key}/'
    data = {
        **_get_matomo_data(),
        'action_name': f'{event}_START',
        'cvar': json.dumps(payload),
        'url': _build_fake_url(payload, base=base),
    }
    threading.Thread(target=_record_matomo, args=(data, )).start()


def record_matomo_stop(event, key, payload):
    base = f'https://hack-computer.com/{event}/{key}/'
    data = {
        **_get_matomo_data(),
        'action_name': f'{event}_STOP',
        'cvar': json.dumps(payload),
        'url': _build_fake_url(payload, base=base),
    }
    threading.Thread(target=_record_matomo, args=(data, )).start()
