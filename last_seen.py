from datetime import datetime, timedelta, timezone
from functools import partial
from io import BytesIO
from PIL import Image
import pytz
import sqlite3
import sys

import discord
from discord.ext import tasks
from discord.utils import get as d_get
from discord.utils import escape_markdown as esc_md

import emoji_utils
import bot_messages
from recon import ProfileImg
from utils import (parse_dt,
                   add_reactions,
                   RSCDB,
                   add_calendar_reactions,
                   add_wanted_reactions,
                   check_reaction,
                   edit_wanted_embed,
                   ChannelIdentifier,
                   get_emoji_count,
                   handle_status,
                   debug_channel_dialogue)

# TODO multiserver: db for each guild
# TODO class DUDB
conn = sqlite3.connect('discord_users.db', timeout=5)
c = conn.cursor()
q_update = """
UPDATE id_timestamp
SET timestamp = ?
WHERE id = ?"""

rscdb = RSCDB('rsc_users.db')
edit_commands = ['!name', '!tag']

# TODO command for add new channel with calendar
# with arbitrary planning days, timezone
# TODO use channel.id instead channel names
CH_NAMES = {'wanted' : 'wanted',
            'calendar' : 'ready4gta'}

DATE_FMT = '%d.%m.%Y MSC'
WEEKDAY_NAMES = ['Понедельник', 
                 'Вторник', 
                 'Среда', 
                 'Четверг', 
                 'Пятница',
                 'Суббота',
                 'Воскресенье']

if sys.argv[-1] == '--debug':
    debug_ch = debug_channel_dialogue(CH_NAMES)
    CH_NAMES[debug_ch] = 'debug'
    QUIT_MSG = '!x'
else:
    QUIT_MSG = '!quit'

on = discord.Status.online
listening_type = discord.ActivityType.listening
bot_activity = discord.Activity(name='!lastseen help',
                                type=listening_type)
client = discord.Client(activity=bot_activity)

@client.event
async def on_ready():
    guild = d_get(client.guilds, id=guild_id)
    print(guild.name)
        
@client.event
async def on_member_update(before, after):
    if before.status == on and after.status != on:
        ct = datetime.now().timestamp()
        c.execute(q_update, (ct, after.id))
        conn.commit()

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
    text = message.content
    dev_msg = message.author.id == dev_id
    bot_msg = message.author == client.user
    chid = ChannelIdentifier(message, CH_NAMES)

    if text == QUIT_MSG and chid.is_dm and dev_msg:
        await client.close()
    
    # auto-reactions
    if bot_msg and chid.allow_ar:
        if chid.calendar:
            await add_calendar_reactions(message, DATE_FMT)
        elif chid.wanted:
            await add_wanted_reactions(message)
    elif bot_msg:
        return
    
    # help
    #TODO move to bot_messages
    bot_call = '!lastseen'
    help_str = (f'LastSeen commands:\n'
                f'`{bot_call} help` - show available commands.\n'
                f'`{bot_call} #1111` - show when username#1111 '
                'was online.'
               )

    # commands
    if text.startswith(bot_call):
        c_start = len(bot_call) + 1
        command = text[c_start:]
        
        if command.startswith('heartbeat'):
            resp = 'staying alive'
            
        elif command.startswith('help'):
            resp = help_str
            
        elif command.startswith('#'):
            guild = d_get(client.guilds, id=guild_id)
            d = command[1:5]
            
            req_ms = [member for member in guild.members
                     if member.discriminator == d]
            if len(req_ms) == 1:
                req_m = req_ms[0]
                if req_m.status == on:
                    resp = f'{req_m.name} is online now'
                else:
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
                        
            elif len(req_ms) > 1:
                m_names = (f'{i + 1} : {m.name}'
                           for i, m in enumerate(req_ms)
                          )
                m_names_str = '\n'.join(m_names)
                resp = f'''Several users found:
                {m_names_str}'''
                # TODO choice for same discriminator
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
            resp = ('Unknown command.\n'
                    f'`{bot_call} help` for awailable commands.'
                   )

        await message.channel.send(resp)
    
    # recon
    atts = message.attachments
    
    if atts and chid.wanted:
        img = await atts[0].read()
        img = Image.open(BytesIO(img)).convert('RGB')
        img = ProfileImg(img)
        if img.name_box_found:
            player = img.recon_player()
            emb = discord.Embed(title=esc_md(player.name))
            emb.add_field(name='Crew tag',
                          value=esc_md(player.crew_tag),
                          inline=False)
            emb.add_field(name='Image ID',
                          value=str(message.id),
                          inline=False)
            await message.channel.send(embed=emb)
        else:
            await message.channel.send('Image was not recognized')

    # edit last recon message
    if chid.wanted:
        is_edit_command = any(text.startswith(c) for c in edit_commands)
        if is_edit_command:
            msgs = message.channel.history(limit=20)
            check_editor = partial(check_reaction,
                                   emoji=emoji_utils.edit,
                                   user=message.author)
            msg = await msgs.find(check_editor)
            if msg is not None:
                text = esc_md(text)
                await edit_wanted_embed(msg, text)
            else:
                ch = message.channel
                await ch.send('Message to edit was not selected')

# recon confirmation
@client.event
async def on_raw_reaction_add(payload):

    # ignore bot reactions
    if payload.user_id == client.user.id:
        return

    guild = d_get(client.guilds, id=payload.guild_id)
    ch = d_get(guild.channels, id=payload.channel_id)
    msg = await ch.fetch_message(payload.message_id)
    bot_msg = msg.author == client.user
    chid = ChannelIdentifier(msg, CH_NAMES)
    embs = msg.embeds
    # TODO more specific condition than just embed
    # like embed field name
    wanted_reactions = bot_msg and chid.wanted and embs

    if wanted_reactions:
        emojis = (r.emoji for r in msg.reactions)
        initial_recon = emoji_utils.edit in emojis
        is_edit = payload.emoji.name == emoji_utils.edit

        is_plus, is_minus = (payload.emoji.name == r
                             for r in emoji_utils.vote)
        is_vote = is_plus or is_minus

        # remove dsicord markdown escape character
        name = embs[0].title.replace('\\', '')

        if initial_recon and is_plus:
            # add to DB
            # remove dsicord markdown escape character
            crew_tag = (d_get(embs[0].fields, name='Crew tag')
                        .value
                        .replace('\\', '')
                       )
            rscdb.add_player(name, crew_tag)
            # remove edit
            edit_r = d_get(msg.reactions, emoji=emoji_utils.edit)
            await edit_r.clear()

        elif initial_recon and is_minus:
            # remove image
            img_id = int(d_get(embs[0].fields, name='Image ID').value)
            img_msg = await ch.fetch_message(img_id)
            await img_msg.delete()

            # remove message
            await msg.delete()

        elif initial_recon and is_edit:
            resp = bot_messages.edit
            await msg.channel.send(resp)

        elif is_vote:
            plus_c, minus_c = (get_emoji_count(msg,
                                               emj,
                                               custom=True)
                               for emj in emoji_utils.vote)
            handle_status(rscdb, name, plus_c, minus_c)

@client.event
async def on_raw_reaction_remove(payload):

    # ignore bot reactions
    if payload.user_id == client.user.id:
        return

    guild = d_get(client.guilds, id=payload.guild_id)
    ch = d_get(guild.channels, id=payload.channel_id)
    msg = await ch.fetch_message(payload.message_id)
    bot_msg = msg.author == client.user
    chid = ChannelIdentifier(msg, CH_NAMES)
    embs = msg.embeds
    # TODO more specific condition than just embed
    # like embed field name
    wanted_reactions = bot_msg and chid.wanted and embs

    if wanted_reactions:
        is_vote = False
        is_vote = any(payload.emoji.name == r
                      for r in emoji_utils.vote)
        name = embs[0].title.replace('\\', '')
        is_edit = payload.emoji.name == emoji_utils.edit

        if is_vote:
            plus_c, minus_c = (get_emoji_count(msg,
                                               emj,
                                               custom=True)
                               for emj in emoji_utils.vote)
            handle_status(rscdb, name, plus_c, minus_c)

        #elif is_edit:
        # TODO remove edit commands
        #msgs = message.channel.history(limit=20)
        #for msg in msgs.filter(check_edit_commands):
        #    await msg.delete()
        
# callme        
#@client.event
#async def on_member_update(before, after):
    # TODO 
    #elif command.startswith('callme #'):
    #
    #if before.status != on and after.status == on:
    #await message.channel.send(resp)        

@tasks.loop(hours=24)
async def add_date():
    guild = d_get(client.guilds, id=guild_id)
    ch = d_get(guild.text_channels,
               name=CH_NAMES['calendar'])
    today = datetime.now().date()
    # TODO add dates manually
    expected_dates = set(today + timedelta(days=i)
                         for i in range(0, 8))
    av_dates = set()
    async for msg in ch.history(limit=8):
        if msg.author == client.user and msg.embeds:
            title = msg.embeds[0].title
            dt = parse_dt(title, DATE_FMT)
            
            if dt:
                av_dates.add(dt.date())
                
    na_dates = expected_dates.difference(av_dates)
    for d in sorted(na_dates):
        emb = discord.Embed(title=d.strftime(DATE_FMT),
                            description=WEEKDAY_NAMES[d.weekday()])
        await ch.send('_\n\n_', embed=emb)
        
@add_date.before_loop
async def before():
    await client.wait_until_ready() 

with open('token.txt') as file:
    token = file.read()

with open('guild.txt') as file:
    guild_id = int(file.read())

with open('dev_id.txt') as file:
    dev_id = int(file.read())

add_date.start()
client.run(token)