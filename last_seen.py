from datetime import datetime, timedelta, timezone
from io import BytesIO
from PIL import Image
import pytz
import sqlite3
import sys

import discord
from discord.ext import tasks
from discord.utils import get as d_get

from recon import ProfileImg
from utils import parse_dt, add_reactions

# TODO multiserver: db for each guild
conn = sqlite3.connect('discord_users.db', timeout=5)
c = conn.cursor()
q_update = """
UPDATE id_timestamp
SET timestamp = ?
WHERE id = ?"""

rdb_conn = sqlite3.connect('rsc_users.db', timeout=5)
rdbc = rdb_conn.cursor()
q_add_player = """
REPLACE INTO wanted (name, crew_tag, status)
VALUES (?,?,?)"""
q_set_status = """
UPDATE wanted
SET status = ? 
WHERE name = ?"""

# TODO command for add new channel with calendar
# with arbitrary planning days, timezone
CALENDAR_CH = 'ready4gta'
WANTED_CH = 'debug'
d_fmt = '%d.%m.%Y MSC'
WEEKDAY_NAMES = ['Понедельник', 
                 'Вторник', 
                 'Среда', 
                 'Четверг', 
                 'Пятница',
                 'Суббота',
                 'Воскресенье']

if sys.argv[-1] == '--debug':
    QUIT_MSG = '!x'
else:
    QUIT_MSG = '!quit'

# unicode digit emojis
# digits from '0' to '9'
zero_digit_code = zd = 48
# excluded digits
excl_digits = [2, 4, 5, 7]
# unicode digit keycap
udkc = '\U0000fe0f\U000020e3'
emoji_codes = [chr(i) + udkc for i in range(zd, zd + 10)
               if i - zd not in excl_digits]
# number '10' emoji
emoji_codes.append('\U0001f51f')

# custom emojis from '11' to '23'
custom_emoji_codes = [str(i) for i in range(11, 24)]

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
    is_dm = message.channel.type == discord.ChannelType.private
    dev_msg = message.author.id == dev_id
    
    # allow auto-reaction flag
    if is_dm:
        aar_flag = False
    else:
        # TODO extend auto-reaction conditions
        aar_flag = message.channel.name == CALENDAR_CH
    
    # auto-reactions
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
    
    # help
    bot_call = '!lastseen'
    help_str = f"""
    LastSeen commands:
    `{bot_call} help` - show available commands.
    `{bot_call} #1111` - show when username#1111 was online.
    """
    
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
            resp = f"""
            Unknown command.
            `{bot_call} help` for awailable commands."""
            
        await message.channel.send(resp)
    
# recon
    atts = message.attachments
    
    # test
    # TODO
    #is_wanted_ch = msg.channel.name == WANTED_CH
    if atts and is_dm:
        img = await atts[0].read()
        img = Image.open(BytesIO(img)).convert('RGB')
        img = ProfileImg(img)
        player = img.recon_player()
        # TODO as embed
        resp = (f'Name: **{player.name}**\n'
                f'Crew tag: {player.crew_tag}')
        await message.channel.send(resp)

    if text == QUIT_MSG and is_dm and dev_msg:
        await client.close()
        
# recon confirmation
#@client.event
#async def on_reaction_add(reaction, user):
#    msg = reaction.message
#    bot_msg = msg.author == client.user
#    is_wanted_ch = msg.channel.name == WANTED_CH
#    if bot_msg and is_wanted_ch:
#    # add default reactions: 'plus', 'minus'
#    
#    # add to DB
#        name = msg.embed.title
#        crew_tag = d_get(msg.fields, name='crew_tag').value
#        rdbc.execute(q_add_player, (name, crew_tag, 1))
#        rdb_conn.commit()
#    
#    # set status
#        if reaction.emoji ==# plus
#            on = # plus_count > minus_count
#            if on:
#                rdbc.execute(q_set_status, (1, name))
#            
#        if reaction.emoji ==# minus
#            off = # minus_count > plus_count
#            if off:
#                rdbc.execute(q_set_status, (0, name))
        
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
    ch = d_get(guild.text_channels, name=CALENDAR_CH)
    today = datetime.now().date()
    # TODO add dates manually
    expected_dates = set(today + timedelta(days=i)
                         for i in range(0, 8))
    av_dates = set()
    async for msg in ch.history(limit=8):
        if msg.author == client.user and msg.embeds:
            title = msg.embeds[0].title
            dt = parse_dt(title, d_fmt)
            
            if dt:
                av_dates.add(dt.date())
                
    na_dates = expected_dates.difference(av_dates)
    for d in sorted(na_dates):
        emb = discord.Embed(title=d.strftime(d_fmt),
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