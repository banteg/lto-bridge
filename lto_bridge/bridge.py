from lto_bridge import binance, ethereum, lto, puzzle

if __name__ == "__main__":
    binance.fetch()
    ethereum.fetch()
    lto.fetch()
    puzzle.solve()
