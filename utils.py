from datetime import datetime
import sqlite3

import discord
from discord.utils import get as d_get

import emoji_utils

def parse_dt(s, fmt):
    try:
        dt = datetime.strptime(s, fmt)
        return dt
    except ValueError:
        return False
    
async def add_reactions(message, emoji_codes, custom_emoji_codes):
    for ec in emoji_codes:
        await message.add_reaction(ec)
                
    guild = message.channel.guild
    custom_emojis = [d_get(guild.emojis, name=i)
                     for i in custom_emoji_codes]
    for ce in custom_emojis:
        await message.add_reaction(ce)

async def add_calendar_reactions(message):
    '''
    Check message and add reactions if applicable.
    '''
    embs = message.embeds
    if embs:
        title = embs[0].title
        date = parse_dt(title, d_fmt)

        if date:
            await add_reactions(message,
                                emoji_utils.hours_0_9,
                                emoji_utils.hours_11_23
                               )

async def add_wanted_reactions(message):
    '''
    Check message and add reactions if applicable.
    '''
    # TODO more specific condition than just embed
    # like embed field name
    embs = message.embeds
    if embs:
        await add_reactions(message,
                            [emoji_utils.edit],
                            emoji_utils.vote
                           )

class RSCDB:
    '''
    API for Rockstar Social Club database.
    '''
    def __init__(self, db_path):
        self.conn = sqlite3.connect(db_path, timeout=5)
        self.c = self.conn.cursor()

        self.q_add_player = """
        REPLACE INTO wanted (name, crew_tag, status)
        VALUES (?,?,?)"""

        self.q_set_status = """
        UPDATE wanted
        SET status = ?
        WHERE name = ?"""

    def set_status(self, name, status):
        self.c.execute(self.q_set_status, (status, name))
        self.conn.commit()

    def add_player(self, name, crew_tag):
        self.c.execute(self.q_add_player, (name, crew_tag, 1))
        self.conn.commit()

def handle_status(db, name, plus_count, minus_count):
    prep = plus_count - minus_count
    if prep == 1:
        db.set_status(name, 1)
    elif prep == -1:
        db.set_status(name, 0)

async def check_reaction(message, emoji, user):
    reaction = d_get(message.reactions, emoji=emoji)
    if reaction is not None:
        users = await reaction.users().flatten()
        return user in users
    else:
        return False

async def edit_wanted_embed(message, command):
    emb = message.embeds[0]

    c = '!name'
    if command.startswith(c):
        emb.title = command[len(c) + 1 :]

    c = '!tag'
    #TODO elif
    if command.startswith(c):
        emb.set_field_at(0,
                         name='Crew tag',
                         value=command[len(c) + 1 :])

    await message.edit(embed=emb)

class ChannelIdentifier:
    '''
    Channel scope idetifier.

    Attributes
    ----------
    allow_ar : bool
    Allow auto-reaction
    '''
    def __init__(self, message, text_channel_names):
        '''
        Parameters
        ----------
        text_channel_names : dict
        {channel_attr : channel_name}
        '''
        self.is_dm = (message.channel.type ==
                      discord.ChannelType.private)
        for attr in text_channel_names.keys():
            setattr(self, attr, False)

        if not self.is_dm:
            for attr, name in text_channel_names.items():
                setattr(self, attr, message.channel.name == name)

        self.allow_ar = self.wanted or self.calendar

def get_emoji_count(message, emoji, custom=True):
    count = 0
    if custom:
        for r in message.reactions:
            if r.custom_emoji:
                if r.emoji.name == emoji:
                    count = r.count
    # TODO
    #else:
    return count