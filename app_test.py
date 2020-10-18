from functools import partial
from io import BytesIO
from PIL import Image

import discord
from discord.utils import get as d_get
from discord.utils import escape_markdown as esc_md

import emoji_utils
import bot_messages
from recon import ProfileImg
from utils import (RSCDB,
                   add_calendar_reactions,
                   add_wanted_reactions,
                   check_reaction,
                   edit_wanted_embed,
                   ChannelIdentifier,
                   get_emoji_count,
                   handle_status)

rscdb = RSCDB('rsc_users.db')

edit_commands = ['!name', '!tag']

text_channel_names = {'wanted' : 'debug',
                      'calendar' : 'ready4gta'}

QUIT_MSG = '!x'

client = discord.Client()

@client.event
async def on_ready():
    guild = d_get(client.guilds, id=guild_id)
    print(guild.name)
        
@client.event
async def on_message(message):
    text = message.content
    dev_msg = message.author.id == dev_id
    bot_msg = message.author == client.user
    
    chid = ChannelIdentifier(message, text_channel_names)
    
    if bot_msg and chid.allow_ar:
        if chid.calendar:
            await add_calendar_reactions(message)
        elif chid.wanted:
            await add_wanted_reactions(message)
    elif bot_msg:
        return
    
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
        
    if text == QUIT_MSG and chid.is_dm and dev_msg:
        await client.close()

@client.event
async def on_raw_reaction_add(payload):
    
    # ignore bot reactions
    if payload.user_id == client.user.id:
        return
    
    guild = d_get(client.guilds, id=payload.guild_id)
    ch = d_get(guild.channels, id=payload.channel_id)
    msg = await ch.fetch_message(payload.message_id)
    bot_msg = msg.author == client.user
    chid = ChannelIdentifier(msg, text_channel_names)
    embs = msg.embeds
    # TODO more specific condition than just embed
    # like embed field name
    wanted_reactions = bot_msg and chid.wanted and embs
    
    if wanted_reactions:
        emojis = (r.emoji for r in msg.reactions)
        initial_recon = emoji_utils.edit in emojis
        is_edit = payload.emoji == emoji_utils.edit
        
        is_plus = is_minus = False
        if isinstance(payload.emoji, discord.PartialEmoji):
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
    chid = ChannelIdentifier(msg, text_channel_names)
    embs = msg.embeds
    # TODO more specific condition than just embed
    # like embed field name
    wanted_reactions = bot_msg and chid.wanted and embs
    
    if wanted_reactions:
        is_vote = False
        if isinstance(payload.emoji, discord.PartialEmoji):
            is_vote = any(payload.emoji.name == r
                          for r in emoji_utils.vote)
        name = embs[0].title.replace('\\', '')
        is_edit = payload.emoji == emoji_utils.edit
        
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
        
with open('token.txt') as file:
    token = file.read()
    
with open('guild.txt') as file:
    guild_id = int(file.read())
    
with open('dev_id.txt') as file:
    dev_id = int(file.read())

client.run(token)