"""
ERC20 -> Mainnet: 40 LTO for crossing the bridge. Given to mainnet nodes.
Mainnet -> ERC20: dynamic fee is taken and is forever burned.
Mainnet -> BEP2: dynamic fee is taken and is forever burned.
BEP2 -> Mainnet: 40 LTO for crossing the bridge. Given to mainnet nodes.
ERC20 -> BEP2: no fee, LTO Network pays the gas fees
BEP2 -> ERC20: not available
"""
from decimal import Decimal
from collections import defaultdict, deque

from termcolor import colored

from lto_bridge.entities import Bridge, db_session


INITIAL_SUPPLY = Decimal('500_000_000')
CROWDSALE_BURNED = Decimal('39_267_891.52666322')

IGNORE = [
    '21vpVwiVFrsfJWgYPwTgvyBkGJYiDRsCJnd7SjALvT9A',  # 16_999_900
    '0x7891becc620f7804a9d1be55e96838d5bfc1db4d346716b57ed0c081ae69fb45',  # 97_500_000
    '0x233632c2a9ef5927b990279ab723d941e0ebd15ec441f934a9b71f9ea45cd215',  # 50_000_000
]

emojis = {'ethereum': '🦄', 'binance': '🐬', 'lto': '🌝'}
names = {'ethereum': 'ethereum', 'binance': 'binance chain', 'lto': 'mainnet'}


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
    total_moved = 0
    total_moved_away = 0
    total_burned = 0
    for tx in incoming:
        if tx.direction != 'in':
            continue
        key = tx_key(tx)
        match = None
        if key == 'ethereum-in':
            match = maybe_pop(stacks, ['lto-out'], tx.value)
            if match:
                total_burned += match.burned or 0
                total_moved_away += tx.value
                print(construct_message(match, tx, total_burned, total_moved, total_moved_away))
        if key == 'binance-in':
            match = maybe_pop(stacks, ['lto-out', 'ethereum-out'], tx.value)
            if match:
                total_burned += match.burned or 0
                if match.network == 'lto':
                    total_moved_away += tx.value
                print(construct_message(match, tx, total_burned, total_moved, total_moved_away))
        if key == 'lto-in':
            match = maybe_pop(stacks, ['ethereum-out', 'binance-out'], tx.value + tx.fees)
            if match:
                total_moved += tx.value
                print(construct_message(match, tx, total_burned, total_moved))


def construct_message(left, right, total_burned, total_moved, total_moved_away=None):
    total_supply = INITIAL_SUPPLY - CROWDSALE_BURNED - total_burned
    msg = (
        f'{emojis[left.network]}→{emojis[right.network]} '
        f'{right.value:,.2f} lto moved from {names[left.network]} to {names[right.network]}'
    )
    if tx_key(left) == 'lto-out' and tx_key(right) in ('ethereum-in', 'binance-in'):
        percent_burned = left.burned / (left.burned + right.value) * 100
        msg += (
            f' 🔥 {left.burned:,.2f} burned ({percent_burned:.1f}%)'
            f'\n{total_burned:,.0f} total burned'
            f'\n{total_moved_away:,.0f} total moved from mainnet'
            f'\n{total_supply:,.0f} supply remaining'
        )
    if tx_key(right) == 'lto-in':
        msg += (
            f'\n{total_moved:,.0f} total moved to mainnet'
        )
    msg += '\n'
    return msg


def tx_key(tx):
    return f'{tx.network}-{tx.direction}'


def maybe_pop(options, keys, value):
    for key in keys:
        if options[key][value]:
            return options[key][value].popleft()
