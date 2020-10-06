from datetime import datetime
from discord.utils import get as d_get

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