from lto_bridge.binance import Binance
from lto_bridge.ethereum import Ethereum

if __name__ == "__main__":
    b = Binance()
    b.write(b.fetch())
    e = Ethereum()
    e.write(e.fetch())
