import os
from datetime import datetime
from decimal import Decimal
from itertools import chain
from concurrent.futures import ThreadPoolExecutor

from web3.middleware.filter import get_logs_multipart
from web3._utils.events import get_event_data, construct_event_topic_set
from eth_utils import encode_hex
from termcolor import colored

from lto_bridge.entities import Bridge, db_session

if os.environ.get('WEB3_INFURA_PROJECT_ID'):
    os.environ['WEB3_INFURA_SCHEME'] = 'https'  # websocket impl. is buggy
    from web3.auto.infura import w3
else:
    from web3.auto import w3

LTO_TOKEN = '0x3DB6Ba6ab6F95efed1a6E794caD492fAAabF294D'
ZERO_ADDRESS = '0x0000000000000000000000000000000000000000'
LTO_BLOCK = 7059695
ABI = {
    'anonymous': False,
    'inputs': [
        {'indexed': True, 'name': 'from', 'type': 'address'},
        {'indexed': True, 'name': 'to', 'type': 'address'},
        {'indexed': False, 'name': 'value', 'type': 'uint256'},
    ],
    'name': 'Transfer',
    'type': 'event',
}
TOPICS_IN = construct_event_topic_set(ABI, {'from': ZERO_ADDRESS})
TOPICS_OUT = construct_event_topic_set(ABI, {'to': ZERO_ADDRESS})

ts_cache = {}
pool = ThreadPoolExecutor(10)
label = colored('Ethereum', 'blue')


def fetch():
    start = Bridge.last_block('ethereum') or LTO_BLOCK
    print(label, 'fetching since', start)
    end = w3.eth.blockNumber
    txs = []
    logs_in = get_logs_multipart(w3, start, end, LTO_TOKEN, TOPICS_IN, 10000)
    logs_out = get_logs_multipart(w3, start, end, LTO_TOKEN, TOPICS_OUT, 10000)
    for batch in chain.from_iterable(zip(logs_in, logs_out)):
        # fetch timestamps concurrently
        list(pool.map(timestamp, {tx['blockNumber'] for tx in batch}))
        txs = [prepare(tx) for tx in batch]
        inserted = write(txs)
        if inserted:
            pos = batch[-1]['blockNumber']
            progress = (pos - start) / (end - start) * 100
            print(label, f'{progress:.2f}%', timestamp(pos), len(inserted), 'events inserted.')


def prepare(tx):
    tx = get_event_data(ABI, tx)
    return dict(
        network='ethereum',
        direction='in' if tx.args['from'] == ZERO_ADDRESS else 'out',
        tx=encode_hex(tx.transactionHash),
        value=Decimal(tx.args.value) / 10 ** 8,
        block=tx.blockNumber,
        ts=timestamp(tx.blockNumber),
    )


def timestamp(block_number):
    if block_number not in ts_cache:
        block = w3.eth.getBlock(block_number)
        ts_cache[block_number] = datetime.fromtimestamp(block.timestamp)
    return ts_cache[block_number]


@db_session
def write(txs):
    inserted = []
    for prepared in txs:
        if Bridge.exists(tx=prepared['tx']):
            continue
        inserted.append(Bridge(**prepared))
    return inserted
