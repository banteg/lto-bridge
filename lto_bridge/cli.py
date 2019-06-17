"""
LTO Bridge

Usage:
  lto-bridge [--fetch] [--solve] [--post] [--daemon]
  lto-bridge dropdb

Options:
  -f --fetch   fetch new events
  -s --solve   match bridge events
  -p --post    post to telegram
  -d --daemon  operate in daemon mode
"""
from time import sleep

import docopt

from lto_bridge import binance, ethereum, lto, puzzle, telegram, entities


def once(opts):
    if opts['--fetch']:
        binance.fetch()
        ethereum.fetch()
        lto.fetch()
    if opts['--solve']:
        messages = list(puzzle.solve())
        telegram.publish(messages, opts['--post'])


def loop(opts):
    while True:
        once(opts)
        sleep(60)


def main():
    opts = docopt.docopt(__doc__)
    if opts['dropdb']:
        entities.db.drop_all_tables(with_all_data=True)
        print('database cleared.')
    if opts['--daemon']:
        loop(opts)
    else:
        once(opts)


if __name__ == "__main__":
    main()
