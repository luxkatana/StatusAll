import discord, asqlite, os, dotenv
from discord.ext import commands, tasks
dotenv.load_dotenv()
intents = discord.Intents.all()
TOKEN = os.environ["TOKEN"]
GUILD_IDS = [941803156633956362]
bot = commands.Bot(command_prefix="./",
                   intents=intents,
                   activity=discord.Game("*listens*"))
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    await change_channels.start()
@bot.event
async def on_presence_update(before: discord.Member, after: discord.Member) -> None:
    if len(after.activities) == 0 or before.activities == after.activities:
        return
    async def get_date() -> bool | dict:
        async with asqlite.connect("./database.db")as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM statusrole WHERE guildID=?;", (after.guild.id,))
                fetch = await cursor.fetchall()
                if fetch  == []:
                    return False
                return dict(fetch[0])
    custom = list(filter(lambda j:isinstance(j, discord.CustomActivity), after.activities))
    if custom == []:
        return
    custom = custom[0]
    data = await get_date()
    if data == False or data["listen"] == 0:
        return
    if (text := data["statustext"]) == custom.name:
        channel = bot.get_channel(data["channelID"])
        ROLE = channel.guild.get_role(data["roleID"])
        await after.add_roles(ROLE)
        embedchannel = discord.Embed(title=after, description=f"Found someone with the status **{text}**", colour=discord.Color.green(), timestamp=discord.utils.utcnow())
        await channel.send(embed=embedchannel)
@bot.slash_command(name="status", guild_ids=GUILD_IDS)
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

@tasks.loop(seconds=8)
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


@bot.slash_command(name="statusrole", guild_ids=GUILD_IDS)
@discord.option(name="statustext", description="the text of the status",type=str , required=True)
@discord.option(name="logchannel", description="The channel to log each member", required=True, type=discord.TextChannel)
@discord.option(name="role", description="The role to role the member", required=True, type=discord.Role)
@discord.option(name="switch", description="Set on or off", required=True, choices=["on", "off"], type=str)
async def statusrole(
    ctx: discord.ApplicationContext,
    statustext: str,
    logchannel: discord.TextChannel,
    role: discord.Role,
    switch: str
) -> None:
    await ctx.defer()
    async def update_data() -> None:
        async with asqlite.connect("./database.db")as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("UPDATE statusrole SET roleID=?, channelID=?, statustext=? WHERE guildID=?;", (role.id, logchannel.id, statustext, ctx.guild.id))
                await conn.commit()
    async def create_new_shit() -> None:
        async with asqlite.connect("./database.db")as conn:
            async with conn.cursor()as cursor:
                await cursor.execute("INSERT INTO statusrole VALUES(?, ?, ?, ?, ?);", (ctx.guild.id, logchannel.id, True, role.id, statustext))
                await conn.commit()
                return
    async def validate_it() -> bool | dict:
        async with asqlite.connect("./database.db")as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT * FROM statusrole WHERE guildID=?;", (ctx.guild.id,))
                fetch = await cursor.fetchall()
                if fetch == []:
                    return False
                return dict(fetch[0])
    validation = await validate_it()
    if switch == "off":
        if isinstance(validation, bool):
            await ctx.respond(embed=discord.Embed(title="Nope", description="It was never on...", colour=discord.Color.red()))
            return
        async with asqlite.connect("./database.db")as conn:
            async with conn.cursor()as cursor:
                await cursor.execute("UPDATE statusrole SET listen=0 WHERE guildID=?;", (ctx.guild_id,))
                await conn.commit()
        await ctx.respond(embed=discord.Embed(title="Off", description="It's off now!"))
        return
    if logchannel.can_send() == False:
        embed = discord.Embed(title="Failed", description=f"I don't have permission to send messages in <#{logchannel.id}>")
        await ctx.respond(embed=embed)
        return
    else:
        # for each
        if role.is_assignable() ==  False:
            await ctx.respond(embed=discord.Embed(title="RIP", description=f"I cannot role people with the role <@&{role.id}>", colour=discord.Color.red()))
            return
        embed = discord.Embed(title="Started", description=f"Starting Roling people  and logging in <#{logchannel.id}>\nText: **{statustext}** ", colour=discord.Color.green())
        await ctx.respond(embed=embed)
        if isinstance(validation, bool):
            await create_new_shit()
        else:
            await update_data()
        for member in ctx.guild.members:
            custom_status = list(filter(lambda j: isinstance(j, discord.CustomActivity), member.activities))
            if custom_status == []:
                continue
            custom_status = custom_status[0]
            if custom_status.name == statustext:
                
                await member.add_roles(role)
                embedchannel = discord.Embed(title=f"{member}", description=f"Found someone with the status **{statustext}**", colour=discord.Color.green(), timestamp=discord.utils.utcnow())
                await logchannel.send(embed=embedchannel)


bot.run(TOKEN)
