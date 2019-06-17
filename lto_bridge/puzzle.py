"""
ERC20 -> Mainnet: 40 LTO for crossing the bridge. Given to mainnet nodes.
Mainnet -> ERC20: dynamic fee is taken and is forever burned.
Mainnet -> BEP2: dynamic fee is taken and is forever burned.
BEP2 -> Mainnet: 40 LTO for crossing the bridge. Given to mainnet nodes.
ERC20 -> BEP2: no fee, LTO Network pays the gas fees
BEP2 -> ERC20: not available
"""
from decimal import Decimal
from dataclasses import dataclass
from collections import defaultdict, deque

from termcolor import colored

from lto_bridge.entities import Bridge, db_session
from lto_bridge.telegram import construct_message


INITIAL_SUPPLY = Decimal('500_000_000')
CROWDSALE_BURNED = Decimal('39_267_891.52666322')

IGNORE = [
    '21vpVwiVFrsfJWgYPwTgvyBkGJYiDRsCJnd7SjALvT9A',  # 16_999_900
    '0x7891becc620f7804a9d1be55e96838d5bfc1db4d346716b57ed0c081ae69fb45',  # 97_500_000
    '0x233632c2a9ef5927b990279ab723d941e0ebd15ec441f934a9b71f9ea45cd215',  # 50_000_000
]

@dataclass
class Stats:
    supply: Decimal = INITIAL_SUPPLY - CROWDSALE_BURNED
    burned: Decimal = 0
    moved_in: Decimal = 0
    moved_out: Decimal = 0


@db_session
def solve():
    crossings = list(Bridge.select().order_by(Bridge.ts))

    # keep network-direction -> value -> txs mapping for lookups
    stacks = defaultdict(lambda: defaultdict(deque))
    for tx in crossings:
        key = tx_key(tx)
        value = tx.value + (tx.fees or 0)
        stacks[key][value].append(tx)

    incoming = [tx for tx in crossings if tx.direction == 'in' and tx.tx not in IGNORE]
    stats = Stats()
    for tx in incoming:
        if tx.direction != 'in':
            continue
        key = tx_key(tx)
        match = None
        if key == 'ethereum-in':
            match = maybe_pop(stacks, ['lto-out'], tx.value)
            if match:
                stats.burned += match.burned or 0
                stats.supply -= match.burned or 0
                stats.moved_out += tx.value
                yield tx, construct_message(match, tx, stats)
        if key == 'binance-in':
            match = maybe_pop(stacks, ['lto-out', 'ethereum-out'], tx.value)
            if match:
                stats.burned += match.burned or 0
                stats.supply -= match.burned or 0
                if match.network == 'lto':
                    stats.moved_out += tx.value
                yield tx, construct_message(match, tx, stats)
        if key == 'lto-in':
            match = maybe_pop(stacks, ['ethereum-out', 'binance-out'], tx.value + tx.fees)
            if match:
                stats.moved_in += tx.value
                yield tx, construct_message(match, tx, stats)


def tx_key(tx):
    return f'{tx.network}-{tx.direction}'


def maybe_pop(options, keys, value):
    for key in keys:
        if options[key][value]:
            return options[key][value].popleft()
