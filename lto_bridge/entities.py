import datetime
from decimal import Decimal

from pony.orm import *

db = Database()


class Bridge(db.Entity):
    network = Required(str)
    direction = Required(str)
    tx = Required(str)
    value = Required(Decimal, sql_type='numeric')
    burned = Optional(Decimal, sql_type='numeric')
    fees = Optional(Decimal, sql_type='numeric')
    block = Required(int)
    ts = Required(datetime.datetime)
    posted = Optional(datetime.datetime)

    @staticmethod
    @db_session
    def last_block(network):
        return select(max(x.block) for x in Bridge if x.network == network).first()

    @staticmethod
    @db_session
    def mark_posted():
        return db.execute("update bridge set posted = '1970-01-01' where direction = 'in'")


db.bind(provider='postgres', user='banteg', database='lto')
db.generate_mapping(create_tables=True)
