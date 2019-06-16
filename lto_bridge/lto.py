import os
from operator import itemgetter
from datetime import datetime
from decimal import Decimal
from itertools import groupby, zip_longest
from collections import defaultdict

import requests

from lto_bridge.entities import Bridge, db_session, select

LTO_FEES = '3JrGV6TeEV3ovVjsh9SPqQL48EDLET47B9U'
LTO_BRIDGE = '3JugjxT51cTjWAsgnQK4SpmMqK6qua1VpXH'

LTO_NODE = 'http://127.0.0.1:6869'
LTO_API_KEY = os.environ['LTO_API_KEY']

stats = {'burn': 0}


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
    transactions = get_transactions(10000)
    for block, txs in groupby(transactions, itemgetter('height')):
        write(list(txs), last_block)


@db_session
def write(txs, last_block=None):
    # lto -> ethereum/binance
    lto_out = defaultdict(list)
    lto_burn = defaultdict(list)
    for tx in txs:
        if tx['recipient'] == LTO_BRIDGE:
            lto_out[tx['sender']].append(tx)
        if tx['recipient'] == LTO_FEES:
            lto_burn[tx['sender']].append(tx)
    # match out txs with burn amounts
    for sender in lto_out:
        rel_exits = sorted(lto_out[sender], key=itemgetter('amount'))
        rel_burns = sorted(lto_burn[sender], key=itemgetter('amount'))
        for tx, tx_burn in zip_longest(rel_exits, rel_burns):
            if Bridge.exists(lto_tx=tx['id']):
                continue
            print('exit', tx)
            print('burn', tx_burn)
            found = (
                select(
                    x
                    for x in Bridge
                    if x.value == tx_value(tx)
                    and x.ts >= tx_timestamp(tx)
                    and x.lto_tx == ''
                    and x.network != 'lto'
                )
                .order_by(Bridge.ts)
                .first()
            )
            print(found)
            if found:
                found.lto_tx = tx['id']
                if tx_burn:
                    found.burned = tx_value(tx_burn)
                    stats['burn'] += tx_value(tx_burn)
                    print(stats)

    for tx in txs:
        skip_block = last_block and tx['height'] < last_block
        skip_exists = Bridge.exists(tx=tx['id'])
        if skip_block or skip_exists:
            continue

        # ethereum/binance -> lto
        if tx['sender'] == LTO_BRIDGE:
            inserted = Bridge(
                network='lto',
                tx=tx['id'],
                value=tx_value(tx),
                block=tx['height'],
                ts=tx_timestamp(tx),
            )
            print(inserted)


def tx_value(tx):
    return Decimal(tx['amount']) / 10 ** 8


def tx_timestamp(tx):
    return datetime.fromtimestamp(Decimal(tx['timestamp']) / 1000)


def process_new(db, n):
    blocks = groupby(get_transactions(n), itemgetter('height'))
    messages = []
    for block, group in blocks:
        enters = {
            tx['recipient']: tokens(tx['amount']) for tx in txs if tx['sender'] == BRIDGE_TROLL
        }
        for addr in enters:
            db['mainnet'] += enters[addr]
            messages.append(
                f'🌝  {enters[addr]:,.0f} moved to mainnet, {db["mainnet"]:,.0f} total moved to mainnet'
            )
        exits = defaultdict(list)
        burned = defaultdict(list)
        for tx in txs:
            if tx['recipient'] == BRIDGE_TROLL:
                exits[tx['sender']].append(tokens(tx['amount']))
            if tx['recipient'] == BRIDGE_TROLL_FEES:
                burned[tx['sender']].append(tokens(tx['amount']))
        for addr in exits:
            # match exit with burn
            related = list(zip_longest(sorted(exits[addr]), sorted(burned[addr])))
            print(related)
            for addr_exit, addr_burn in related:
                parts = [f'🐬  {addr_exit:,.0f} moved to ethereum']
                if addr_burn:
                    db['burned'] += addr_burn
                    percent_burned = addr_burn / (addr_exit + addr_burn) * 100
                    parts.append(
                        f'🔥 {addr_burn:,.0f} burned ({percent_burned:.0f}%), {db["burned"]:,.0f} total burned'
                    )
                messages.append(' '.join(parts))
    return messages
