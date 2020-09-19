from datetime import datetime, timezone
from io import BytesIO
from PIL import Image
import pytz
import sqlite3

import discord

from recon import ProfileImg

# TODO users_online -> discord_users
conn = sqlite3.connect('users_online.db', timeout=5)
c = conn.cursor()
q_update = """
UPDATE id_timestamp
SET timestamp = ?
WHERE id = ?"""

rdb_conn = sqlite3.connect('rsc_users.db', timeout=5)
rdbc = rdb_conn.cursor()
q_add_player = """
REPLACE INTO wanted (name, crew_tag)
VALUES (?,?)"""

on = discord.Status.online
listening_type = discord.ActivityType.listening
bot_activity = discord.Activity(name='!lastseen help',
                                type=listening_type)
client = discord.Client(activity=bot_activity)

@client.event
async def on_ready():
    guild = discord.utils.get(client.guilds, name=guild_name)
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
    is_dm = message.channel.type == discord.ChannelType.private
    
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
                        
            if len(req_ms) > 1:
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
        
    if text == '!x':
        await client.close()
    
    # recon
    #######
    atts = message.attachments
    
    # test
    if atts and is_dm:
        img = await atts[0].read()
        img = Image.open(BytesIO(img)).convert('RGB')
        img = ProfileImg(img)
        player = img.recon_player()
        resp = (f'Name: **{player.name}**\n'
                f'Crew tag: {player.crew_tag}')
        await message.channel.send(resp)
        
    # confirmation
    
    # add to DB
        
        
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