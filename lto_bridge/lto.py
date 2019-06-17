import os
from operator import itemgetter
from datetime import datetime, timedelta
from decimal import Decimal
from itertools import groupby, zip_longest
from collections import defaultdict

import requests
from termcolor import colored

from lto_bridge.entities import Bridge, db_session

LTO_FEES = '3JrGV6TeEV3ovVjsh9SPqQL48EDLET47B9U'
LTO_BRIDGE = '3JugjxT51cTjWAsgnQK4SpmMqK6qua1VpXH'

LTO_NODE = os.environ['LTO_NODE']

search_window = timedelta(days=1)
label = colored('LTO', 'magenta')


def lto(request):
    r = requests.get(f'{LTO_NODE}{request}')
    r.raise_for_status()
    return r.json()


def get_transactions(limit):
    bridge_txs = lto(f'/transactions/address/{LTO_BRIDGE}/limit/{limit}')[0]
    fees_txs = lto(f'/transactions/address/{LTO_FEES}/limit/{limit}')[0]
    return list(sorted(bridge_txs + fees_txs, key=itemgetter('height')))


def fetch():
    last_block = Bridge.last_block('lto')
    print(label, 'fetching since', last_block or 'beginning')
    transactions = get_transactions(10000)
    inserted = []
    for block, txs in groupby(transactions, itemgetter('height')):
        txs = [tx for tx in txs if not last_block or tx['height'] >= last_block]
        inserted.extend(write(txs))
    print(label, len(inserted), 'events inserted.')


@db_session
def write(txs):
    burns = merge_burns(txs)
    inserted = []
    for tx in txs:
        if Bridge.exists(tx=tx['id']):
            continue
        if LTO_BRIDGE in (tx['sender'], tx['recipient']):
            row = Bridge(
                    network='lto',
                    direction='in' if tx['sender'] == LTO_BRIDGE else 'out',
                    tx=tx['id'],
                    value=value(tx),
                    block=tx['height'],
                    ts=timestamp(tx),
            )
            if tx['sender'] == LTO_BRIDGE:
                row.fees = tx_fee(tx)
            elif tx['recipient'] == LTO_BRIDGE:
                row.burned = burns[tx['id']]
            inserted.append(row)
    return inserted


def merge_burns(txs):
    out = defaultdict(list)
    burn = defaultdict(list)
    for tx in txs:
        if tx['recipient'] == LTO_BRIDGE:
            out[tx['sender']].append(tx)
        if tx['recipient'] == LTO_FEES:
            burn[tx['sender']].append(tx)
    result = {}
    for sender in out:
        # assume that amount burned is proportional to tx amount
        exits = sorted(out[sender], key=itemgetter('amount'))
        burns = sorted(burn[sender], key=itemgetter('amount'))
        for tx, burn_tx in zip_longest(exits, burns):
            result[tx['id']] = value(burn_tx) if burn_tx else None
    return result


def value(tx):
    return Decimal(tx['amount']) / 10 ** 8


def timestamp(tx):
    return datetime.fromtimestamp(Decimal(tx['timestamp']) / 1000)


def tx_fee(tx):
    """Cost of moving ETH/BNB->LTO."""
    if tx['height'] <= 75650:
        return 100
    else:
        return 40
