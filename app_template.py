import discord
d_get = discord.utils.get

QUIT_MSG = '!x'
client = discord.Client()

@client.event
async def on_ready():
    guild = d_get(client.guilds, id=guild_id)
    print(guild.name)
    
        
@client.event
async def on_message(message):
    text = message.content
    is_dm = message.channel.type == discord.ChannelType.private
    dev_msg = message.author.id == dev_id
    
    if text == QUIT_MSG and is_dm and dev_msg:
        await client.close()
        
with open('token.txt') as file:
    token = file.read()
    
with open('guild.txt') as file:
    guild_id = int(file.read())
    
with open('dev_id.txt') as file:
    dev_id = int(file.read())

client.run(token)