import discord
d_get = discord.utils.get

client = discord.Client()

@client.event
async def on_ready():
    guild = d_get(client.guilds, id=guild_id)
    print(guild.name)
    
        
@client.event
async def on_message(message):
    text = message.content
    is_dm = message.channel.type == discord.ChannelType.private
    
    if message.author == client.user:
        return
    
    if text == '!x' and is_dm:
        await client.close()
        
    if text == '!c' and is_dm:
        breakpoint()
        
with open('token.txt') as file:
    token = file.read()
    
with open('guild.txt') as file:
    guild_id = int(file.read())

client.run(token)