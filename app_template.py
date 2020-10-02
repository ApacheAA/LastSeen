import discord

client = discord.Client()

@client.event
async def on_ready():
    guild = discord.utils.get(client.guilds, id=guild_id)
    print(guild.name)
        
@client.event
async def on_message(message):
    is_dm = message.channel.type == discord.ChannelType.private
    
    if message.author == client.user:
        return
    
    text = message.content    
    if text == '!x' and is_dm:
        await client.close()       
        
with open('token.txt') as file:
    token = file.read()
    
with open('guild.txt') as file:
    guild_id = int(file.read())

client.run(token)