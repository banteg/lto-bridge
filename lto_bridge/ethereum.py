from datetime import datetime
from decimal import Decimal

from web3.auto import w3
from web3.middleware.filter import get_logs_multipart
from web3._utils.events import get_event_data, construct_event_topic_set
from eth_utils import event_signature_to_log_topic, encode_hex

from lto_bridge.entities import Bridge, db_session

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
# lto -> ethereum
TOPICS = construct_event_topic_set(ABI, {'from': ZERO_ADDRESS})
ts_cache = {}


def fetch():
    start = Bridge.last_block('ethereum') or LTO_BLOCK
    txs = []
    for batch in get_logs_multipart(w3, start, w3.eth.blockNumber, LTO_TOKEN, TOPICS, 10000):
        if batch:
            print(f"ethereum block {batch[-1]['blockNumber']}")
        txs = [prepare(tx) for tx in batch]
        write(txs)


def prepare(tx):
    tx = get_event_data(ABI, tx)
    return dict(
        network='ethereum',
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
    for prepared in txs:
        if Bridge.exists(tx=prepared['tx']):
            continue
        inserted = Bridge(**prepared)
        print(inserted)
