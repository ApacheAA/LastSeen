from datetime import datetime, timedelta

import discord
from discord.ext import tasks
d_get = discord.utils.get

from utils import parse_dt, add_reactions

QUIT_MSG = '!x'

# TODO command for add new channel with calendar
# with arbitrary planning days
CALENDAR_CH = 'ready4gta'
d_fmt = '%d.%m.%Y MSC'
WEEKDAY_NAMES = ['Понедельник', 
                 'Вторник', 
                 'Среда', 
                 'Четверг', 
                 'Пятница',
                 'Суббота',
                 'Воскресенье']

client = discord.Client()

@client.event
async def on_ready():
    guild = d_get(client.guilds, id=guild_id)
    print(guild.name)
    ch = d_get(guild.text_channels, name=CALENDAR_CH)
    async for msg in ch.history():
        emb = msg.embeds[0]
        d = parse_dt(emb.title, d_fmt)
        upd_emb = discord.Embed(title=emb.title,
                                description=WEEKDAY_NAMES[d.weekday()])

        await msg.edit(embed=upd_emb)
    await client.close()

with open('token.txt') as file:
    token = file.read()
    
with open('guild.txt') as file:
    guild_id = int(file.read())

client.run(token)