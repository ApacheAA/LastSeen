from datetime import datetime, timedelta

import discord
from discord.ext import tasks
d_get = discord.utils.get

from utils import parse_dt, add_reactions

# TODO command for add new channel with calendar
# with arbitrary planning days
CALENDAR_CH = 'ready4gta'
d_fmt = '%d.%m.%Y MSC'

#digits emoji
# digits from '0' to '9'
zero_digit_code = zd = 48
# excluded digits
excl_digits = [2, 4, 5, 7]
# unicode digit keycap
udkc = '\U0000fe0f\U000020e3'
emoji_codes = [chr(i) + udkc for i in range(zd, zd + 10)
               if i - zd not in excl_digits]
# number '10'
emoji_codes.append('\U0001f51f')

# digits from 11 to 23
custom_emoji_codes = [str(i) for i in range(11, 24)]


client = discord.Client()

@client.event
async def on_ready():
    guild = d_get(client.guilds, id=guild_id)
    print(guild.name)
        
@client.event
async def on_message(message):
    text = message.content
    is_dm = message.channel.type == discord.ChannelType.private
    # allow autoreaction flag
    if is_dm:
        aar_flag = False
    else:
        # TODO extend autoreaction conditions
        aar_flag = message.channel.name == CALENDAR_CH

    if message.author == client.user:
        if aar_flag and message.embeds:
            title = message.embeds[0].title
            date = parse_dt(title, d_fmt)
            
            if date:
                await add_reactions(message,
                                    emoji_codes,
                                    custom_emoji_codes
                                   )
        else:
            return
        
    if text == '!x' and is_dm:
        await client.close()

@tasks.loop(hours=24)
async def add_date():
    guild = d_get(client.guilds, id=guild_id)
    ch = d_get(guild.text_channels, name=CALENDAR_CH)
    today = datetime.now().date()
    expected_dates = set(today + timedelta(days=i)
                         for i in range(0, 8))
    av_dates = set()
    async for msg in ch.history():
        if msg.author == client.user and msg.embeds:
            title = msg.embeds[0].title
            dt = parse_dt(title, d_fmt)
            
            if dt:
                av_dates.add(dt.date())
                
    na_dates = expected_dates.difference(av_dates)
    for d in sorted(na_dates):
        emb = discord.Embed(title=d.strftime(d_fmt))
        await ch.send('_\n\n_', embed=emb)
        
@add_date.before_loop
async def before():
    await client.wait_until_ready()
        
with open('token.txt') as file:
    token = file.read()
    
with open('guild.txt') as file:
    guild_id = int(file.read())

add_date.start()
client.run(token)