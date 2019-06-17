# lto bridge

monitor lto network's three-way bridge, match up transactions
and report them to [telegram channel](https://t.me/troll_bridge).

## installation

requires python 3.7, poetry and postgres.

```
createdb lto
poetry install
```

alternatively, you can `pip install` file from releases section.

set up these environment variables:
- `TELEGRAM_BOT_KEY` obtian from [bot father](https://t.me/BotFather)
- `TELEGRAM_CHAT_ID` chat id to report to
- `LTO_NODE` (optional) if you want to connect to a local lto node (default: `https://nodes.lto.network`)
- `WEB3_INFURA_PROJECT_ID` (optional) if you want to connect to a remote ethereum node (default: uses local node)
- `PGUSER` postgres user

## data sources

to set up local sources, set these environment variables:
- lto: set `LTO_NODE` to `http://127.0.0.1:6869`
- ethereum: unset `WEB3_INFURA_PROJECT_ID`, run `parity` or `get --rpc`
- binance chain: not available

to set up remote sources:
- lto: unset `LTO_NODE`
- ethereum: set `WEB3_INFURA_PROJECT_ID`
- binance chain: you are set

## usage

```
LTO Bridge

Usage:
  lto-bridge [--fetch] [--solve] [--post] [--daemon]
  lto-bridge dropdb

Options:
  -f --fetch   fetch new events
  -s --solve   match bridge events
  -p --post    post to telegram
  -d --daemon  operate in daemon mode
```
