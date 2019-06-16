import datetime
from decimal import Decimal
from itertools import count

import requests
from termcolor import colored

from lto_bridge.entities import Bridge, db_session

BINANCE_BRIDGE = 'bnb1esdfkkddv0sa5w7njk080rwuda47k3me3nxk75'
label = colored('Binance', 'yellow')


def fetch():
    last_block = Bridge.last_block('binance')
    print(label, 'fetching since', last_block or 'beginning')
    txs = []
    for page in count(1):
        print(label, 'page', page)
        r = requests.get(
            'https://explorer.binance.org/api/v1/txs',
            params=dict(page=page, rows=100, address=BINANCE_BRIDGE, txType='TRANSFER'),
        )
        r.raise_for_status()
        data = r.json(parse_float=Decimal)
        txs.extend(data['txArray'])
        already_indexed = last_block and data['txArray'][0]['blockHeight'] <= last_block
        if len(txs) == data['txNums'] or not data['txArray'] or already_indexed:
            break

    txs = [prepare(tx) for tx in txs if tx['txAsset'] == 'LTO-BDF']
    write(txs)


def prepare(tx):
    return dict(
        network='binance',
        direction='in' if tx['fromAddr'] == BINANCE_BRIDGE else 'out',
        tx=tx['txHash'],
        value=tx['value'],
        block=tx['blockHeight'],
        ts=datetime.datetime.fromtimestamp(tx['timeStamp'] / 1000),
    )


@db_session
def write(txs):
    inserted = []
    for prepared in txs:
        if Bridge.exists(tx=prepared['tx']):
            continue
        inserted.append(Bridge(**prepared))
    print(label, len(inserted), 'events inserted.')
