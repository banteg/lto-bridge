"""
ERC20 -> Mainnet: 40 LTO for crossing the bridge. Given to mainnet nodes.
Mainnet -> ERC20: dynamic fee is taken and is forever burned.
Mainnet -> BEP2: dynamic fee is taken and is forever burned.
BEP2 -> Mainnet: 40 LTO for crossing the bridge. Given to mainnet nodes.
ERC20 -> BEP2: no fee, LTO Network pays the gas fees
BEP2 -> ERC20: not available
"""
from collections import defaultdict, deque

from termcolor import colored

from lto_bridge.entities import Bridge, db_session


@db_session
def solve():
    crossings = list(Bridge.select().order_by(Bridge.ts))

    # keep network-direction -> value -> txs mapping for lookups
    stacks = defaultdict(lambda: defaultdict(deque))
    for tx in crossings:
        key = tx_key(tx)
        value = tx.value + (tx.fees or 0)
        stacks[key][value].append(tx)

    for tx in crossings:
        if tx.direction != 'in':
            continue
        key = tx_key(tx)
        match = None
        if key == 'ethereum-in':
            match = maybe_pop(stacks, ['lto-out'], tx.value)
            if match:
                print(f'🦄  {tx.value} moved from {match.network} to ethereum 🔥 {match.burned} burned')
        if key == 'binance-in':
            match = maybe_pop(stacks, ['lto-out', 'ethereum-out'], tx.value)
            if match:
                print(f'🐬  {tx.value} moved from {match.network} to binance chain 🔥 {match.burned} burned')
        if key == 'lto-in':
            match = maybe_pop(stacks, ['ethereum-out', 'binance-out'], tx.value + tx.fees)
            if match:
                print(f'🌝  {tx.value} moved to mainnet from {match.network}')


def tx_key(tx):
    return f'{tx.network}-{tx.direction}'


def maybe_pop(options, keys, value):
    for key in keys:
        if options[key][value]:
            return options[key][value].popleft()
