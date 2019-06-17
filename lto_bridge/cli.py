"""
LTO Bridge

Usage:
  lto-bridge [--fetch] [--solve] [--post]
  lto-bridge dropdb

Options:
  -f --fetch  fetch new events
  -s --solve  match bridge events
  -p --post   post to telegram
"""
import docopt

from lto_bridge import binance, ethereum, lto, puzzle, telegram, entities


def main():
    opts = docopt.docopt(__doc__)
    if opts['dropdb']:
        entities.db.drop_all_tables(with_all_data=True)
        print('database cleared.')
    if opts['--fetch']:
        binance.fetch()
        ethereum.fetch()
        lto.fetch()
    if opts['--solve']:
        messages = list(puzzle.solve())
        telegram.publish(messages, opts['--post'])


if __name__ == "__main__":
    main()
