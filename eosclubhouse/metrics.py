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


from gi.repository import EosMetrics

from eosclubhouse import config
from eosclubhouse.utils import convert_variant_arg


# Metrics event ids
CLUBHOUSE_NEWS_QUEST_LINK_EVENT = 'ebffecb9-7b31-4c30-a9a0-f896aaaa5b4f'
CLUBHOUSE_SET_PAGE_EVENT = '2c765b36-a4c9-40ee-b313-dc73c4fa1f0d'
CLUBHOUSE_PATHWAY_ENTER_EVENT = '600c1cae-b391-4cb4-9930-ea284792fdfb'

# Libquest event ids
QUEST_EVENT = '50aebb1b-7a93-4caf-8698-3a601a0fc0f6'
PROGRESS_UPDATE_EVENT = '3a037364-9164-4b42-8c07-73bcc00902de'

# Achievements event ids
ACHIEVEMENT_POINTS_EVENT = '86521913-bfa3-4d13-b511-a03d4e339d2f'
ACHIEVEMENT_EVENT = '62ce2e93-bfdc-4cae-af4c-54068abfaf02'


def record(event, payload):
    if config.USE_EOSMETRICS:
        record_eosmetrics(event, payload)
    # TODO: implement matomo metrics record


def record_start(event, key, payload):
    if config.USE_EOSMETRICS:
        record_eosmetrics_start(event, key, payload)
    # TODO: implement matomo metrics record


def record_stop(event, key, payload):
    if config.USE_EOSMETRICS:
        record_eosmetrics_stop(event, key, payload)
    # TODO: implement matomo metrics record


# eos-metrics

def record_eosmetrics(event, payload):
    recorder = EosMetrics.EventRecorder.get_default()
    variant = convert_variant_arg(payload)
    recorder.record_event(event, variant)


def record_eosmetrics_start(event, key, payload):
    recorder = EosMetrics.EventRecorder.get_default()
    key = convert_variant_arg(key)
    variant = convert_variant_arg(payload)
    recorder.record_start(event, key, variant)


def record_eosmetrics_stop(event, key, payload):
    recorder = EosMetrics.EventRecorder.get_default()
    key = convert_variant_arg(key)
    variant = convert_variant_arg(payload)
    recorder.record_stop(event, key, variant)
