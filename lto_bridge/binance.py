import datetime
from decimal import Decimal
from itertools import count

import requests

from lto_bridge.entities import Bridge, db_session

BINANCE_BRIDGE = 'bnb1esdfkkddv0sa5w7njk080rwuda47k3me3nxk75'


class Binance:
    def fetch(self):
        last_block = Bridge.last_block('binance')
        txs = []
        for page in count(1):
            print(f'binance page {page}')
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

        return [self.prepare(tx) for tx in txs if self.qualifies(tx)]

    def prepare(self, tx):
        return dict(
            network='binance',
            tx=tx['txHash'],
            value=tx['value'],
            block=tx['blockHeight'],
            ts=datetime.datetime.fromtimestamp(tx['timeStamp'] / 1000),
        )

    def qualifies(self, tx):
        return tx['fromAddr'] == BINANCE_BRIDGE and tx['txAsset'] == 'LTO-BDF'

    @db_session
    def write(self, txs):
        for prepared in txs:
            if Bridge.exists(tx=prepared['tx']):
                continue
            inserted = Bridge(**prepared)
            print(inserted)
