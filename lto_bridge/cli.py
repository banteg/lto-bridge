"""
LTO Bridge

Usage:
  lto-bridge [--fetch] [--solve]
  lto-bridge dropdb

Options:
  -f --fetch  fetch new events
  -s --solve  match bridge events
"""

import docopt

from lto_bridge import binance, ethereum, lto, puzzle, entities


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
        puzzle.solve()


if __name__ == "__main__":
    main()
