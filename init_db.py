import os
import sqlite3
from collections import namedtuple

# DB configurations
db_config = namedtuple('DBConfig', ['path', 'q_init'])
db_configs = []
db_configs.append(db_config('rsc_users.db',
                            '''
                            CREATE TABLE wanted (
                            name TEXT,
                            crew TEXT,
                            crew_tag TEXT,
                            KDR REAL,
                            status INTEGER,
                            unique (name)
                            )
                            '''
                           )
                 )

db_configs.append(db_config('discord_users.db',
                            '''CREATE TABLE id_timestamp(
                            id INTEGER,
                            timestamp REAL
                            )'''
                           )
                 )

for dbc in db_configs:
    if not os.path.exists(dbc.path):
        conn = sqlite3.connect(dbc.path, timeout=5)
        c = conn.cursor()
        c.execute(dbc.q_init)
        conn.commit()
        conn.close()