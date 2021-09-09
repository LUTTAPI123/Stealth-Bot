import discord
import helpers
import datetime
import asyncio
import os
import typing
import traceback
from discord.ext import commands

class dev(commands.Cog):
    "<:earlybotdev:850843591756349450> Commands that only the developer of this client can use"
    def __init__(self, client):
        self.hidden = True
        self.client = client

    @commands.command(help="Updates the bot on github", aliases=['push'])
    @commands.is_owner()
    async def update(self, ctx, *, message=None):
        if message == None:
            message = "No message provided"
        prefix = await self.client.db.fetchval('SELECT prefix FROM guilds WHERE guild_id = $1', ctx.guild.id)
        prefix = prefix or 'sb!'
        await ctx.reply(f'''
```yaml
{prefix}jsk git add .
git commit -m "{message}"
git push origin main
```
        ''')

    @commands.command()
    @commands.is_owner()
    async def say(self, ctx, *, message):
        await ctx.send(message)

    @commands.command(aliases=['borgor', 'burgor'])
    async def burger(self, ctx):
        prefix = await self.client.db.fetchval('SELECT prefix FROM guilds WHERE guild_id = $1', ctx.guild.id)
        prefix = prefix or 'sb!'
        await ctx.reply(f"I couldn't find that command, do `{prefix}oof` to kill yourself.")

    @commands.command(aliases=['to_do'])
    @commands.is_owner()
    async def todo(self, ctx, *, text):
        channel = self.client.get_channel(881541529381007431)

        await channel.send(f"TO DO: {text}")

        embed = discord.Embed(title=f"Sent to do!", description=f"What was sent: {text}", timestamp=discord.utils.utcnow(), color=0x2F3136)
        embed.set_footer(text=f"Command requested by: {ctx.author}", icon_url=ctx.author.avatar.url)
        await ctx.reply(embed=embed)

    @commands.command(help="toggles no-prefix mode on or off", aliases=["no_prefix", "silentprefix", "silent_prefix"])
    @commands.is_owner()
    async def noprefix(self, ctx, state : str=None):
        if state == 'on':
            await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
            self.client.no_prefix = True
        elif state == 'off':
            await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
            self.client.no_prefix = False
        else:
            if self.client.no_prefix == False:
                await ctx.message.add_reaction('<:toggle_on:857842924729270282>')
                self.client.no_prefix = True
            elif self.client.no_prefix == True:
                await ctx.message.add_reaction('<:toggle_off:857842924544065536>')
                self.client.no_prefix = False


    @commands.command(help="Loads a cog", aliases=['le', 'lc', 'loadcog'])
    @commands.is_owner()
    async def load(self, ctx, extension):
        embed = discord.Embed(description=f"<a:loading:747680523459231834> Loading {extension}...")
        embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

        message = await ctx.reply(embed=embed)

        try:
            self.client.load_extension(f"cogs.{extension}")
            embed = discord.Embed(description=f":white_check_mark: {extension}", timestamp=discord.utils.utcnow(), color=0x2F3136)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotFound:
            embed = discord.Embed(description=":x: That cog doesn't exist.", timestamp=discord.utils.utcnow(), color=0x2F3136)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionAlreadyLoaded:
            embed = discord.Embed(description=":x: That cog is already loaded.", timestamp=discord.utils.utcnow(), color=0x2F3136)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await message.edit(embed=embed)

        except discord.ext.commands.NoEntryPointError:
            embed = discord.Embed(description=":x: That cog doesn't have a setup function.", timestamp=discord.utils.utcnow(), color=0x2F3136)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionFailed as e:
            traceback_string = "".join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))
            embed = discord.Embed(description=":x An error occurred while trying to load that cog.\n```{traceback_string}```", timestamp=discord.utils.utcnow(), color=0x2F3136)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            try:
                await message.edit(embed=embed)

            except:
                embed = discord.Embed(description=":x: An error occurred while trying to load that cog. ```\nError message is too long to send it here.\nPlease check the console\n```", timestamp=discord.utils.utcnow(), color=0x2F3136)
                embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

                await message.edit()
            raise e

    @commands.command(help="Unloads a cog", aliases=['unl', 'ue', 'uc'])
    @commands.is_owner()
    async def unload(self, ctx, extension):
        embed = discord.Embed(description=f"⬇ {extension}", timestamp=discord.utils.utcnow(), color=0x2F3136)
        message = await ctx.reply(embed=embed)

        try:
            self.client.unload_extension("cogs.{}".format(extension))
            embed = discord.Embed(description=f":white_check_mark: {extension}", timestamp=discord.utils.utcnow(), color=0x2F3136)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotFound:
            embed = discord.Embed(description=f":x: That cog doesn't exist.", timestamp=discord.utils.utcnow(), color=0x2F3136)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotLoaded:
            embed = discord.Embed(description = f":x: That cog isn't loaded.", timestamp=discord.utils.utcnow(), color=0x2F3136)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await message.edit(embed=embed)

    @commands.command(help="Reloads an cog", aliases=['rel', 'rc'])
    @commands.is_owner()
    async def reload(self, ctx, extension):
        embed = discord.Embed(description=f"<a:loading:747680523459231834> {extension}", timestamp=discord.utils.utcnow(), color=0x2F3136)
        message = await ctx.reply(embed=embed)

        try:
            self.client.reload_extension("cogs.{}".format(extension))
            embed = discord.Embed(description=f":white_check_mark: {extension}", timestamp=discord.utils.utcnow(), color=0x2F3136)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotLoaded:
            embed = discord.Embed(description=":x: That cog isn't loaded.", timestamp=discord.utils.utcnow(), color=0x2F3136)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionNotFound:
            embed = discord.Embed(description=":x: That cog doesn't exist.", timestamp=discord.utils.utcnow(), color=0x2F3136)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await message.edit(embed=embed)

        except discord.ext.commands.NoEntryPointError:
            embed = discord.Embed(description="x: That cog doesn't have a setup function", timestamp=discord.utils.utcnow(), color=0x2F3136)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await message.edit(embed=embed)

        except discord.ext.commands.ExtensionFailed as e:
            traceback_string = "".join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))
            embed = discord.Embed(description = f":x: An error occurred while trying to load that cog.\n```{traceback_string}```", timestamp=discord.utils.utcnow(), color=0x2F3136)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            try:
                await message.edit(embed=embed)

            except:
                embed = discord.Embed(description = f"An error occurred while trying to load that cog.\n``` error too long, check the console\n```", timestamp=discord.utils.utcnow(), color=0x2F3136)
                embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

                await message.edit()
            raise e

    @commands.command(help="Reloads all extensions", aliases=['relall', 'rall'], usage="[silent|channel]")
    @commands.is_owner()
    async def reloadall(self, ctx, argument: typing.Optional[str]):
        self.client.last_rall = discord.utils.utcnow()
        list = ""
        desc = ""
        err = False
        rerel = []
        if argument == 'silent' or argument == 's': silent = True
        else: silent = False
        if argument == 'channel' or argument == 'c': channel = True
        else: channel = False

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                list = f"{list} \n🔃 {filename[:-3]}"

        embed = discord.Embed(color=ctx.me.color, description = list)
        message = await ctx.send(embed=embed)

        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    self.client.reload_extension("cogs.{}".format(filename[:-3]))
                    desc = f"{desc} \n✅ {filename[:-3]}"
                except:
                    rerel.append(filename)

        for filename in rerel:
            try:
                self.client.reload_extension("cogs.{}".format(filename[:-3]))
                desc = f"{desc} \n✅ {filename[:-3]}"

            except discord.ext.commands.ExtensionNotLoaded:
                desc = f"{desc} \n❌ {filename[:-3]} - Not loaded"
            except discord.ext.commands.ExtensionNotFound:
                desc = f"{desc} \n❌ {filename[:-3]} - Not found"
            except discord.ext.commands.NoEntryPointError:
                desc = f"{desc} \n❌ {filename[:-3]} - No setup func"
            except discord.ext.commands.ExtensionFailed as e:
                traceback_string = "".join(traceback.format_exception(etype=None, value=e, tb=e.__traceback__))
                desc = f"{desc} \n❌ {filename[:-3]} - Execution error"
                embederr = discord.Embed(color=ctx.me.color, description = f"\n❌ {filename[:-3]} Execution error - Traceback\n```\n{traceback_string}\n```")
                if silent == False:
                    if channel == False: await ctx.author.send(embed=embederr)
                    else: await ctx.send(embed=embederr)
                err = True

        if err == True:
            if silent == False:
                if channel == False: desc = f"{desc} \n\n📬 {ctx.author.mention}, I sent you all the tracebacks."
                else: desc = f"{desc} \n\n📬 Sent all tracebacks here."
            if silent == True: desc = f"{desc} \n\n📭 silent, no tracebacks sent."
            embed = discord.Embed(color=ctx.me.color, description = desc, title = 'Reloaded some extensions')
            await message.edit(embed=embed)
        else:
            embed = discord.Embed(title = 'Reloaded all extensions', color=ctx.me.color, description = desc)
            await message.edit(embed=embed)

def setup(client):
    client.add_cog(dev(client))
