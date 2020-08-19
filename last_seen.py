import asyncio
from datetime import datetime
import json
import os
import pytz

import discord

client = discord.Client()

@client.event
async def on_ready():
    guild = discord.utils.get(client.guilds, name=guild_name)
    print(guild.name)
    while True:
        #TODO sqlite instead json
        with open(bd_path, 'r') as file:
            users_online = json.load(file)
            ct = datetime.now().timestamp()
            cur_online = {str(member.id) : ct
                          for member in guild.members 
                          if member.status == discord.Status.online}
            users_online.update(cur_online)
        with open(bd_path, 'w') as file:
            json.dump(users_online, file)
            
        await asyncio.sleep(10)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    bot_call = '!lastseen'
    help_str = f'''LastSeen commands:
    {bot_call} help - show available commands.
    {bot_call} #1111 - show when username#1111 was online.
    '''
    
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
                with open(bd_path, 'r') as file:
                    users_online = json.load(file)
                msc_tz = pytz.timezone('Europe/Moscow')
                ts = datetime.fromtimestamp(users_online[str(req_m.id)],
                                            msc_tz)
                resp = f'{req_m.name} was online {ts:%Y-%m-%d %H:%M} MSC'
            else:
                resp = f'Bot has never seen online user with #{d}'
            
        else:
            resp = f"""Unknown command.
            '{bot_call} help' for awailable commands"""
            
        await message.channel.send(resp)
            
with open('token.txt') as file:
    token = file.read()
    
with open('guild.txt') as file:
    guild_name = file.read()

bd_path = 'users_online.json'
if not os.path.exists(bd_path):
    with open(bd_path, 'w') as file:
        json.dump({}, file)

client.run(token)

#user identifiers
# member.id
# str(member),
# member.name,
# member.discriminator,
# member.nick,
# member.display_name