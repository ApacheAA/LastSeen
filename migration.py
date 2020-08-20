import json
import sqlite3

import discord

client = discord.Client()

@client.event
async def on_ready():
    guild = discord.utils.get(client.guilds, name=guild_name)
    print(guild.name)

    with open(bd_path, 'r') as file:
        users_online = json.load(file)
    users_online = {int(k) : v for k, v in users_online.items()}
    uids = set(member.id for member in guild.members)
    rest_uids = uids.difference(set(users_online.keys()))
    rest_users = {uid : -1.0 for uid in rest_uids}
    users_online.update(rest_users)
    
    q_newid = """
    INSERT INTO id_timestamp
    VALUES (?, ?)"""
    c.executemany(q_newid, users_online.items()
                 )
    conn.commit()
    await client.close()
    
with open('token.txt') as file:
    token = file.read()
    
with open('guild.txt') as file:
    guild_name = file.read()

bd_path = 'users_online.json'

conn = sqlite3.connect('users_online.db', timeout=5)
c = conn.cursor()
c.execute('''
CREATE TABLE id_timestamp
(id INTEGER, timestamp REAL)''')
conn.commit()

client.run(token)