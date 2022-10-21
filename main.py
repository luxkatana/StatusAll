import discord, asqlite, os, dotenv
from discord.ext import commands, tasks
dotenv.load_dotenv()
intents = discord.Intents.default()
intents.message_content = True
TOKEN = os.environ["TOKEN"]
bot = commands.Bot(command_prefix="./",
                   intents=intents,
                   activity=discord.Game("*listens*"))
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await change_channels.start()

@bot.slash_command(name="status", guild_ids=[])
@discord.option(name="switch", type=bool, description="on or off", required=True)
async def status_change(ctx: discord.ApplicationContext, switch: bool) -> None:
    async def change_bool(state: bool, guild_id: int) -> None:
        async with asqlite.connect("database.db")as conn:
            async with conn.cursor()as cursor:
                await cursor.execute("UPDATE servers set listen=? WHERE guildID=?;", (state, guild_id))
                await conn.commit()
    async def count() -> dict:
        bots = 0
        members = 0
        online = 0
        dont_disturb = 0
        for user in ctx.guild.members:
            if user.bot:
                bots += 1
            else:
                if user.status.value == "dnd":
                    dont_disturb +=1
                    members += 1
                elif user.status.value == "online":
                    online += 1
                    members += 1
        return {"members": members, "bots": bots, "dnd": dont_disturb, "online": online}
    async def already_exists(guild_id: int) -> bool:
        async with asqlite.connect("database.db")as conn:
            async with conn.cursor()as cursor:
                await cursor.execute("SELECT * FROM servers WHERE guildID=?;", (guild_id,))
                fetch = await cursor.fetchall()
                if fetch  == []:
                    return False
                else:
                    return True
    if switch == False:
        exists = await already_exists(ctx.guild.id)
        if exists == True:
            
            await change_bool(False, ctx.guild_id)
            await ctx.respond(embed=discord.Embed(title="Done!", description="It's successfully off now!", colour=discord.Color.green()))
        elif exists == False:
            await ctx.respond(embed=discord.Embed(title="Oh uh", description="it was never switched to on so... yeah", colour=discord.Color.green()))
    else: # if choosed for on
        exists = await already_exists(ctx.guild.id)
        if exists == False:
            for cate in ctx.guild.categories:
                if cate.name == "status":
                    await cate.delete(reason="No duplicates!")
                    break
            all_c = await count()
            category = await ctx.guild.create_category("status", reason=f"created by {ctx.author}", position=4)
            
            all_bots = await category.create_voice_channel(name="Bots: {}".format(all_c["bots"]))
            all_members = await category.create_voice_channel(name="Members: {}".format(all_c["members"]))
            status_replacements = {"dnd": "🔴", "online": "🟢"}
            total = await category.create_voice_channel(name="🟢: {} 🔴: {}".format(all_c["online"], all_c["dnd"]))
            async with asqlite.connect("./database.db") as conn:
                async with conn.cursor()as cursor:
                    await cursor.execute("INSERT INTO servers VALUES(?, ?, ?, ?, ?);", (ctx.guild.id, all_bots.id, all_members.id, total.id, True))
                    await conn.commit()
                    embed = discord.Embed(title="Created!", description="Successfully created a new category called **status**", colour=discord.Color.green())
                    await ctx.respond(embed=embed)

        else:
            await change_bool(True, ctx.guild.id)
            await ctx.respond(embed=discord.Embed(title="It's on!", description="It's succcessfully on!", colour=discord.Color.green()))

@tasks.loop(minutes=8)
async def change_channels() -> None:
    async with asqlite.connect("./database.db")as conn:
        async with conn.cursor()as cursor:
            await cursor.execute("SELECT * FROM servers;")
            
            fetch = await cursor.fetchall()
            if fetch == []:
                return
            fetch  = list(map(lambda victim: dict(victim), fetch))
            for i in fetch:
                if i["listen"] == 0:
                    continue
                bot_channel = bot.get_channel(i["bot_vc_id"])
                user_channel = bot.get_channel(i["user_vc_id"])
                total_channel = bot.get_channel(i["total_id"])
                if None in [bot_channel, user_channel, total_channel]:
                    continue
                online = 0
                bots = 0
                dnd = 0
                for j in bot_channel.guild.members:
                    if j.bot:
                        bots += 1
                    else:
                        match j.status.value:
                            case "dnd":
                                dnd += 1
                            case "online":
                                online += 1
                await bot_channel.edit(name="Bots: {}".format(bots))
                await user_channel.edit(name="Members: {}".format(bot_channel.guild.member_count))
                await total_channel.edit(name="🟢: {} 🔴: {}".format(online, dnd))
bot.run(TOKEN)