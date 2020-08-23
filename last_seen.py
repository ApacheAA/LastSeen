import asyncio
from datetime import datetime, timezone
import pytz
import sqlite3

import discord

conn = sqlite3.connect('users_online.db', timeout=5)
c = conn.cursor()
q_update = """
UPDATE id_timestamp
SET timestamp = ?
WHERE id = ?"""

on = discord.Status.online
listening_type = discord.ActivityType.listening
bot_activity = discord.Activity(name='!lastseen help',
                                type=listening_type)
client = discord.Client(activity=bot_activity)

@client.event
async def on_ready():
    guild = discord.utils.get(client.guilds, name=guild_name)
    print(guild.name)
    
    while True:
        ct = datetime.now().timestamp()
        cur_online = ((ct, member.id) for member in guild.members 
                      if member.status == discord.Status.online
                     )
        c.executemany(q_update, cur_online)
        conn.commit()
            
        await asyncio.sleep(10)

@client.event
async def on_typing(channel, user, naive_dt):
    if channel.type != discord.ChannelType.private:
        if user.status != on:
            aware_dt = naive_dt.replace(tzinfo=timezone.utc)
            c.execute(q_update, (aware_dt.timestamp(), user.id))
            conn.commit()
    # TODO use private channel to check online
    # else:
        
@client.event
async def on_member_join(user):
    q_newid = """
    INSERT INTO id_timestamp
    VALUES (?, ?)"""
    c.execute(q_newid,
              (user.id,
               datetime.now().timestamp()
              )
             )
    conn.commit()        

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    bot_call = '!lastseen'
    help_str = f"""
    LastSeen commands:
    `{bot_call} help` - show available commands.
    `{bot_call} #1111` - show when username#1111 was online.
    """
    
    text = message.content
    if text.startswith(bot_call):
        c_start = len(bot_call) + 1
        command = text[c_start:]
        
        if command.startswith('heartbeat'):
            resp = 'staying alive'
            
        elif command.startswith('help'):
            resp = help_str
            
        elif command.startswith('#'):
            guild = discord.utils.get(client.guilds, name=guild_name)
            d = command[1:5]
            # TODO choice for same discriminator
            req_ms = [member for member in guild.members
                     if member.discriminator == d]
            if req_ms:
                req_m = req_ms[0]
                q_get = '''
                SELECT timestamp FROM id_timestamp
                WHERE id = ?'''
                res = c.execute(q_get, (req_m.id,))
                ls_ts = res.fetchone()[0]
                
                if ls_ts == -1:
                    resp = f'Bot has never seen {req_m.name} online'
                else:    
                    # TODO user timezone
                    msc_tz = pytz.timezone('Europe/Moscow')
                    ls_dt = datetime.fromtimestamp(ls_ts, msc_tz)
                
                    resp = (f'{req_m.name} was online '
                    f'{ls_dt:%Y-%m-%d %H:%M} MSC')
            else:
                resp = f'User with #{d} not found'
        
        # TODO
        #elif command.startswith('MAU'):
        # TODO 
        #def last_period_count(timestamps, per)
        #per = 30
        #per_start = datetime.now() - timedelta(days=per)
        #per_count = sum(ts > per_start for ts in timestamps)
        #elif command.startswith('DAU'):
        
        else:
            resp = f"""
            Unknown command.
            `{bot_call} help` for awailable commands."""
            
        await message.channel.send(resp)

#@client.event
#async def on_member_update(before, after):
    # TODO 
    #elif command.startswith('callme #'):
    #
    #if before.status != on and after.status == on:
    #await message.channel.send(resp)        
        
with open('token.txt') as file:
    token = file.read()
    
with open('guild.txt') as file:
    guild_name = file.read()

client.run(token)

#user identifiers
# member.id
# str(member),
# member.name,
# member.discriminator,
# member.nick,
# member.display_name