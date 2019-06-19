import os
from datetime import datetime

from termcolor import colored
from telegram import TelegramApi

from lto_bridge.entities import Bridge, db_session

t = TelegramApi(os.environ['TELEGRAM_BOT_KEY'])
chat_id = os.environ['TELEGRAM_CHAT_ID']

label = colored('Telegram', 'red')
emojis = {'ethereum': '🦄', 'binance': '🐬', 'lto': '🌝'}
names = {'ethereum': 'ethereum', 'binance': 'binance chain', 'lto': 'mainnet'}


def construct_message(left, right, stats):
    msg = (
        f'{emojis[left.network]}→{emojis[right.network]} '
        f'{fnum(right.value, 2)} lto moved from {names[left.network]} to {names[right.network]}'
    )
    if tx_key(left) == 'lto-out' and tx_key(right) in ('ethereum-in', 'binance-in'):
        percent_burned = left.burned / (left.burned + right.value)
        msg += (
            f' 🔥 {fnum(left.burned, 2)} burned ({percent_burned:.1%})'
            f'\n{fnum(stats.burned, 0)} total burned'
            f'\n{fnum(stats.moved_out, 0)} total moved from mainnet'
            f'\n{fnum(stats.supply, 0)} supply remaining'
        )
    if tx_key(right) == 'lto-in':
        msg += f'\n{fnum(stats.moved_in, 0)} total moved to mainnet'
    return msg


@db_session
def publish(messages, post=False):
    first_time = all([tx.posted is None for tx, msg in messages])
    if first_time:
        print(label, 'first time, marking everything as posted')
        Bridge.mark_posted()
    for orig, text in messages:
        tx = Bridge[orig.id]
        if tx.posted:
            continue
        tx.posted = datetime.utcnow()
        print(label, text, '\n')
        if post:
            t.send_message(chat_id=chat_id, text=text)


def tx_key(tx):
    return f'{tx.network}-{tx.direction}'


def fnum(number, decimals=6):
    return format(number, f',.{decimals}f').rstrip('0').rstrip('.')
