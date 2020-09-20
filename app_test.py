from datetime import datetime, timedelta
import re

import discord
from discord.ext import tasks

#TODO try intstead pattern
pat = '\\d{2}\.\\d{2}\.\\d{4} MSC'
d_fmt = '%d.%m.%Y MSC'

# unicode digit keycap
udkc = '\U0000fe0f\U000020e3'
emoji_codes = [chr(i) + udkc for i in range(48, 58)]
# 10 emoji
emoji_codes.append('\U0001f51f')

client = discord.Client()

@client.event
async def on_ready():
    guild = discord.utils.get(client.guilds, name=guild_name)
    print(guild.name)
        
@client.event
async def on_message(message):
    is_dm = message.channel.type == discord.ChannelType.private
    # TODO fix closing by DM
    if not is_dm:
        debug_mode = message.channel.name == 'debug'
    else:
        debug_mode = False
    text = message.content

    if message.author == client.user:
        contains_pat = re.search(pat, text) is not None
        if debug_mode and contains_pat:

            for ec in emoji_codes:
                await message.add_reaction(ec)
                
            guild = message.channel.guild
            custom_emoji_codes = ['PLUS',
                                  '14']
            custom_emojis = [discord.utils.get(guild.emojis,
                                               name=i)
                             for i in custom_emoji_codes]
            for ce in custom_emojis:
                await message.add_reaction(ce)
        else:
            return
        
    if text == '!x':
        await client.close()

@tasks.loop(seconds=10)
async def add_date():
    guild = discord.utils.get(client.guilds, name=guild_name)
    ch = discord.utils.get(guild.text_channels, name='debug')
    today = datetime.now().date()
    expected_dates = set(today + timedelta(days=i)
                         for i in range(0, 8))
    ch_dates = set()
    async for msg in ch.history():
        if msg.author == client.user:
            date_strings = re.findall(pat, msg.content)
            if date_strings:
                ds = date_strings[0]
                ch_dt = datetime.strptime(ds, d_fmt)
                ch_dates.add(ch_dt.date())
                
    na_dates = expected_dates.difference(ch_dates)
    for d in sorted(na_dates):
        await ch.send(d.strftime(d_fmt))
        
@add_date.before_loop
async def before():
    await client.wait_until_ready()
    
#@client.event
#async def on_reaction_add(reaction, user):
        
with open('token.txt') as file:
    token = file.read()
    
with open('guild.txt') as file:
    guild_name = file.read()

add_date.start()
client.run(token)