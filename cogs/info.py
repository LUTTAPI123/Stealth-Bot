import discord
import datetime
import io
import psutil
import helpers
import unicodedata
import time
import aiohttp
from discord.ext import commands, menus
from discord.ext.commands.cooldowns import BucketType
import threading
from platform import python_version
import asyncio
pythonVersion = python_version()
start_time = time.time()

class EmbedPageSource(menus.ListPageSource):
    async def format_page(self, menu, item):
        embed = discord.Embed(title="Character information", description="\n".join(item), timestamp=discord.utils.utcnow(), color=0x2F3136)
        #embed.set_footer(text=f"Command requested by {self.context.author}", icon_url=self.context.author.avatar.url)

        return embed

class info(commands.Cog):
    "All informative commands like `serverinfo`, `userinfo` and more!"
    def __init__(self, client):
        self.client = client
        client.session = aiohttp.ClientSession()

    @commands.command(help="Shows you information about the member you mentioned", aliases=['ui', 'user', 'member', 'memberinfo'], brief="https://cdn.discordapp.com/attachments/878984821081272401/878986523423416370/userinfo.gif")
    @commands.cooldown(1, 5, BucketType.member)
    async def userinfo(self, ctx, member : discord.Member=None):
        if member == None:
            member = ctx.author

        fetchedMember = await self.client.fetch_user(member.id)

        if member.bot == True:
            botText = "Yes"
        else:
            botText = "No"

        if member.premium_since == None:
            premiumText = "Not boosting"
        else:
            premiumText = f"{discord.utils.format_dt(member.premium_since, style='f')} ({discord.utils.format_dt(member.premium_since, style='R')})"

        if str(member.status).title() == "Online":
            statusEmote = "<:status_online:596576749790429200>"
        elif str(member.status).title() == "Idle":
            statusEmote = "<:status_idle:596576773488115722>"
        elif str(member.status).title() == "Dnd":
            statusEmote = "<:status_dnd:596576774364856321>"
        elif str(member.status).title() == "Streaming":
            statusEmote = "<:status_streaming:596576747294818305>"
        else:
            statusEmote = "<:status_offline:596576752013279242>"

        roles = ""
        for role in member.roles:
            if role is ctx.guild.default_role: continue
            roles = f"{roles} {role.mention}"
        if roles != "":
            roles = f"{roles}"

        top_role = member.top_role.mention.replace("@@everyone", "")

        badges = helpers.get_member_badges(member)
        if badges:
            badges = f"{badges}"
        else:
            badges = ''

        perms = helpers.get_perms(member.guild_permissions)
        if perms:
            perms = f"{', '.join(perms)}"
        else:
            perms = ''

        if member.avatar.is_animated() == True:
            text1 = f"[PNG]({member.avatar.replace(format='png', size=2048).url}) | [JPG]({member.avatar.replace(format='jpg', size=2048).url}) | [WEBP]({member.avatar.replace(format='webp', size=2048).url}) | [GIF]({member.avatar.replace(format='gif', size=2048).url})"
            text = text1.replace("cdn.discordapp.com", "media.discordapp.net")
        else:
            text1 = f"[PNG]({member.avatar.replace(format='png', size=2048).url}) | [JPG]({member.avatar.replace(format='jpg', size=2048).url}) | [WEBP]({member.avatar.replace(format='webp', size=2048).url})"
            text = text1.replace("cdn.discordapp.com", "media.discordapp.net")

        guild = ctx.guild

        desktopStatus = ":desktop: <:redTick:596576672149667840>"
        webStatus = ":globe_with_meridians: <:redTick:596576672149667840>"
        mobileStatus = ":mobile_phone:  <:redTick:596576672149667840>"

        if str(member.desktop_status) == "online" or str(member.desktop_status) == "idle" or str(member.desktop_status) == "dnd" or str(member.desktop_status) == "streaming":
            desktopStatus = ":desktop: <:greenTick:596576670815879169>"

        if str(member.web_status) == "online" or str(member.web_status) == "idle" or str(member.web_status) == "dnd" or str(member.web_status) == "streaming":
            webStatus = ":globe_with_meridians: <:greenTick:596576670815879169>"

        if str(member.mobile_status) == "online" or str(member.mobile_status) == "idle" or str(member.mobile_status) == "dnd" or str(member.mobile_status) == "streaming":
            mobileStatus = ":mobile_phone: <:greenTick:596576670815879169>"

        embed = discord.Embed(title=f"Userinfo - {member}", url=f"https://discord.com/users/{member.id}", description=f"""
Name: {member}
<:nickname:876507754917929020> Nickname: {member.nick}
Discriminator:  #{member.discriminator}
Display name: {member.mention}
<:greyTick:860644729933791283> ID: {member.id}
:robot: Bot?: {botText}
Avatar url: {text}
<a:nitro_wumpus:857636144875175936> Boosting: {premiumText}
<:invite:860644752281436171> Created: {discord.utils.format_dt(member.created_at, style="f")} ({discord.utils.format_dt(member.created_at, style="R")})
<:member_join:596576726163914752> Joined: {discord.utils.format_dt(member.joined_at, style="f")} ({discord.utils.format_dt(member.joined_at, style="R")})
<:moved:848312880666640394> Join position: {sorted(ctx.guild.members, key=lambda member : member.joined_at).index(member) + 1}
Mutual guilds: {len(member.mutual_guilds)}
{statusEmote} Current status: {str(member.status).title()}
:video_game: Current activity: {str(member.activity.type).split('.')[-1].title() if member.activity else 'Not playing'} {member.activity.name if member.activity else ''}
<:discord:877926570512236564> Client: {desktopStatus} **–** {webStatus} **–** {mobileStatus}
<:role:876507395839381514> Top Role: {top_role}
<:role:876507395839381514> Roles: {roles}
<:store_tag:860644620857507901> Staff permissions: {perms}
<:store_tag:860644620857507901> Badges: {badges}
:rainbow: Color: {member.color}
:rainbow: Accent color: {fetchedMember.accent_color}
        """, timestamp=discord.utils.utcnow(), color=0x2F3136)
        embed.set_thumbnail(url=member.avatar.url)
        embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

        await ctx.reply(embed=embed)


    @commands.command(help="Shows you information about the server", aliases=['si', 'guild', 'guildinfo'])
    @commands.cooldown(1, 5, BucketType.member)
    async def serverinfo(self, ctx, id : int=None):
        if id:
            server = self.client.get_guild(id)
            if not server:
                return await ctx.reply("I couldn't find that server. Make sure the ID you entered was correct.")
        else:
            server = ctx.guild

        if ctx.me.guild_permissions.ban_members:
            bannedMembers = len(await server.bans())
        else:
            bannedMembers = "Couldn't get banned members."

        statuses = [len(list(filter(lambda m: str(m.status) == "online", server.members))),
                    len(list(filter(lambda m: str(m.status) == "idle", server.members))),
                    len(list(filter(lambda m: str(m.status) == "dnd", server.members))),
                    len(list(filter(lambda m: str(m.status) == "streaming", server.members))),
                    len(list(filter(lambda m: str(m.status) == "offline", server.members)))]

        last_boost = max(server.members, key=lambda m : m.premium_since or server.created_at)
        if last_boost.premium_since is not None:
            boost = f"{last_boost} {discord.utils.format_dt(last_boost.premium_since, style='f')} {discord.utils.format_dt(last_boost.premium_since, style='R')}"
        else:
            boost = "No boosters exist."

        if server.description:
            description = server.description
        else:
            description = "This serer doesn't have a descripton"

        enabled_features = []
        features = set(server.features)
        all_features = {
            'COMMUNITY': 'Community Server',
            'VERIFIED': 'Verified',
            'DISCOVERABLE': 'Discoverable',
            'PARTNERED': 'Partnered',
            'FEATURABLE': 'Featured',
            'COMMERCE': 'Commerce',
            'MONETIZATION_ENABLED': 'Monetization',
            'NEWS': 'News Channels',
            'PREVIEW_ENABLED': 'Preview Enabled',
            'INVITE_SPLASH': 'Invite Splash',
            'VANITY_URL': 'Vanity Invite URL',
            'ANIMATED_ICON': 'Animated Server Icon',
            'BANNER': 'Server Banner',
            'MORE_EMOJI': 'More Emoji',
            'MORE_STICKERS': 'More Stickers',
            'WELCOME_SCREEN_ENABLED': 'Welcome Screen',
            'MEMBER_VERIFICATION_GATE_ENABLED': 'Membership Screening',
            'TICKETED_EVENTS_ENABLED': 'Ticketed Events',
            'VIP_REGIONS': 'VIP Voice Regions',
            'PRIVATE_THREADS': 'Private Threads',
            'THREE_DAY_THREAD_ARCHIVE': '3 Day Thread Archive',
            'SEVEN_DAY_THREAD_ARCHIVE': '1 Week Thread Archive',
        }

        for feature, label in all_features.items():
            if feature in features:
                enabled_features.append(f"<:greenTick:596576670815879169> {label}")

        features = '\n'.join(enabled_features)

        embed = discord.Embed(title=f"Server info - {server}", description=f"""
Name: {server}
<:greyTick:860644729933791283> ID: {server.id}
:information_source: Description: {description}

<:members:858326990725709854> Members: {len(server.members)} (:robot: {len(list(filter(lambda m : m.bot, server.members)))})
:robot: Bots: {len(list(filter(lambda m: m.bot, server.members)))}
<:owner_crown:845946530452209734> Owner: {server.owner}
<:members:858326990725709854> Max members: {server.max_members}
<:bans:878324391958679592> Banned members: {bannedMembers}

Verification Level: {server.verification_level}
Created: {discord.utils.format_dt(server.created_at, style="f")} ({discord.utils.format_dt(server.created_at, style="R")})
{helpers.get_server_region_emote(server)} Region: {helpers.get_server_region(server)}

<:status_offline:596576752013279242> Statuses: <:status_online:596576749790429200> {statuses[0]} <:status_idle:596576773488115722> {statuses[1]} <:status_dnd:596576774364856321> {statuses[2]} <:status_streaming:596576747294818305> {statuses[3]} <:status_offline:596576752013279242> {statuses[4]}
<:text_channel:876503902554578984> Channels: <:text_channel:876503902554578984> {len(server.text_channels)} <:voice_channel:876503909512933396> {len(server.voice_channels)} <:category:882685952999428107> {len(server.categories)} <:stagechannel:824240882793447444> {len(server.stage_channels)} <:threadnew:833432474347372564> {len(server.threads)}
<:role:876507395839381514> Roles: {len(server.roles)}

<:emoji_ghost:658538492321595393> Animated emojis: {len([x for x in server.emojis if x.animated])}/{server.emoji_limit}
<:emoji_ghost:658538492321595393> Non animated emojis: {len([x for x in server.emojis if not x.animated])}/{server.emoji_limit}

<:boost:858326699234164756> Level: {server.premium_tier}
<:boost:858326699234164756> Boosts: {server.premium_subscription_count}
<:boost:858326699234164756> Latest booster: {boost}

Features:
{features}
        """)

        if server.banner:
            url1 = server.banner.url
            url = url1.replace("cdn.discordapp.com", "media.discordapp.net")
            embed.set_thumbnail(url=url)


        if server.icon:
            url1 = server.icon.url
            url = url1.replace("cdn.discordapp.com", "media.discordapp.net")
            embed.set_thumbnail(url=url)

        #embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

        await ctx.reply(embed=embed)

    @commands.command(help="Shows information about the bot", aliases=['bi', 'bot', 'info', 'about'])
    async def botinfo(self, ctx):
        prefix = await self.client.db.fetchval('SELECT prefix FROM guilds WHERE guild_id = $1', ctx.guild.id)
        prefix = prefix or 'sb!'
        current_time = time.time()
        threads = threading.activeCount()
        mem_info = psutil.virtual_memory()

        embed = discord.Embed(title=f"Bot info - Stealth Bot [-]#1082",  color=0x2F3136)

        embed.add_field(name="Processor", value=f"""
Physical cores: {psutil.cpu_count(logical=False)}
Total cores: {psutil.cpu_count()}\nFrequency:  {psutil.cpu_freq()}
Usage: {psutil.cpu_percent(interval=None)}%""")

        embed.add_field(name="Memory", value=f"""
Total: {mem_info[0]}
Avaible: {mem_info[1]}
Used: {mem_info[2]}%
Free: {mem_info[3]}
Percent: {mem_info[4]}""")

        embed.set_thumbnail(url=self.client.user.avatar.url)
        embed.set_footer(text=f"Command requested by {ctx.author}", icon_url = ctx.author.avatar.url)

        await ctx.reply(embed=embed)

    @commands.command(help="Shows the avatar of the member you mentioned", aliases=['av'])
    async def avatar(self, ctx, member : discord.Member=None):
        if member == None:
            member = ctx.author
        if member.avatar:
            if member.avatar.is_animated() == True:
                text1 = f"[PNG]({member.avatar.replace(format='png', size=2048).url}) | [JPG]({member.avatar.replace(format='jpg', size=2048).url}) | [WEBP]({member.avatar.replace(format='webp', size=2048).url}) | [GIF]({member.avatar.replace(format='gif', size=2048).url})"
                text = text1.replace("cdn.discordapp.com", "media.discordapp.net")
            else:
                text1 = f"[PNG]({member.avatar.replace(format='png', size=2048).url}) | [JPG]({member.avatar.replace(format='jpg', size=2048).url}) | [WEBP]({member.avatar.replace(format='webp', size=2048).url})"
                text = text1.replace("cdn.discordapp.com", "media.discordapp.net")
            embed=discord.Embed(title=f"{member}'s avatar", description=f"{text}", timestamp=discord.utils.utcnow(), color=0x2F3136)
            url1 = member.avatar.url
            url = url1.replace("cdn.discordapp.com", "media.discordapp.net")
            embed.set_image(url=url)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await ctx.reply(embed=embed)
        else:
            await ctx.reply("You don't have a avatar.")

    @commands.command(help="Shows the banner of the member you mentioned", aliases=['bn'])
    @commands.cooldown(1, 5, BucketType.member)
    async def banner(self, ctx, member : discord.Member=None):
        errorMessage = f"{member} doesn't have a banner."
        if member == None or member == ctx.author:
            member = ctx.author
            errorMessage = "You don't have a banner"

        fetchedMember = await self.client.fetch_user(member.id)

        if fetchedMember.banner:
            if fetchedMember.banner.is_animated() == True:
                text1 = f"[PNG]({fetchedMember.banner.replace(format='png', size=2048).url}) | [JPG]({fetchedMember.banner.replace(format='jpg', size=2048).url}) | [WEBP]({fetchedMember.banner.replace(format='webp', size=2048).url}) | [GIF]({fetchedMember.banner.replace(format='gif', size=2048).url})"
                text = text1.replace("cdn.discordapp.com", "media.discordapp.net")
            else:
                text1 = f"[PNG]({fetchedMember.avatar.replace(format='png', size=2048).url}) | [JPG]({fetchedMember.banner.replace(format='jpg', size=2048).url}) | [WEBP]({fetchedMember.banner.replace(format='webp', size=2048).url})"
                text = text1.replace("cdn.discordapp.com", "media.discordapp.net")
            embed=discord.Embed(title=f"{member}'s avatar", description=f"{text}", timestamp=discord.utils.utcnow(), color=0x2F3136)
            url1 = fetchedMember.banner.url
            url = url1.replace("cdn.discordapp.com", "media.discordapp.net")
            embed.set_image(url=url)
            embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await ctx.reply(embed=embed)
        else:
            await ctx.reply(f"{errorMessage}")

    @commands.command(help="Shows you the bot's latency")
    @commands.cooldown(1, 5, BucketType.member)
    async def ping(self, ctx):
        pings = []
        number = 0

        typings = time.monotonic()
        await ctx.trigger_typing()
        typinge = time.monotonic()
        typingms = (typinge - typings) * 1000
        pings.append(typingms)

        start = time.perf_counter()
        message = await ctx.reply("Getting ping...")
        end = time.perf_counter()
        messagems = (end - start) * 1000
        pings.append(messagems)

        discords = time.monotonic()
        url = "https://discordapp.com/"
        async with self.client.session.get(url) as resp:
            if resp.status == 200:
                discorde = time.monotonic()
                discordms = (discorde - discords) * 1000
                pings.append(discordms)
            else:
                discordms = 0

        latencyms = self.client.latency * 1000
        pings.append(latencyms)

        pstart = time.perf_counter()
        await self.client.db.fetch("SELECT 1")
        pend = time.perf_counter()
        psqlms = (pend - pstart) * 1000
        pings.append(psqlms)

        for ms in pings:
            number += ms
        average = number / len(pings)

        websocket_latency = f"{round(latencyms)}ms{' ' * (9-len(str(round(latencyms, 3))))}"
        typing_latency = f"{round(typingms)}ms{' ' * (9-len(str(round(typingms, 3))))}"
        message_latency = f"{round(messagems)}ms{' ' * (9-len(str(round(messagems, 3))))}"
        discord_latency = f"{round(discordms)}ms{' ' * (9-len(str(round(discordms, 3))))}"
        database_latency = f"{round(psqlms)}ms{' ' * (9-len(str(round(psqlms, 3))))}"
        average_latency = f"{round(average)}ms{' ' * (9-len(str(round(average, 3))))}"

        embed = discord.Embed(title="Pong!", timestamp=discord.utils.utcnow(), color=0x2F3136)
        embed.add_field(name=":globe_with_meridians: Websocket latency", value=f"{websocket_latency}")
        embed.add_field(name="<a:typing:597589448607399949> Typing latency", value=f"{typing_latency}")
        embed.add_field(name=":speech_balloon: Message latency", value=f"{message_latency}")
        embed.add_field(name="<:discord:877926570512236564> Discord latency", value=f"{discord_latency}")
        embed.add_field(name="<:psql:871758815345901619> Database latency", value=f"{database_latency}")
        embed.add_field(name=":infinity: Average latency", value=f"{average_latency}")
        embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

        await message.edit(content="Received ping!", embed=embed)

    @commands.command(help="Shows you the uptime of the bot", aliases=['up'])
    async def uptime(self, ctx):
        embed = discord.Embed(title=f'I\'ve been online since {discord.utils.format_dt(self.client.launch_time, style="f")} ({discord.utils.format_dt(self.client.launch_time, style="R")})', timestamp=discord.utils.utcnow(), color=0x2F3136)
        embed.set_footer(text=f"Command requested by {ctx.author}", icon_url=ctx.author.avatar.url)

        await ctx.reply(embed=embed)

    @commands.command(help="Sends a suggestion", aliases=['bot_suggestion', 'suggestion', 'make_suggestion', 'botsuggestion', 'makesuggestion'])
    async def suggest(self, ctx, *, suggestion):
        if len(suggestion) > 750:
            return await ctx.reply("Your suggestion exceeded the 750-character limit.")
        else:
            embed = discord.Embed(title="Bot suggestion", description=f"""
Suggestion by: {ctx.author} | {ctx.author.name} | {ctx.author.id}

Suggestion from server: {ctx.guild} | {ctx.guild.id}

Suggestion from channel: {ctx.channel} | {ctx.channel.name} | {ctx.channel.id}

Suggestion: {suggestion}
            """, timestamp=discord.utils.utcnow(), color=0x2F3136)
            channel = self.client.get_channel(879786064473129033)
            await channel.send(embed=embed)
            await ctx.reply("Your suggestion has been sent! It will be reviewed by Ender2K89 soon.")

    @commands.command(help="Shows you information about a character", aliases=['characterinfo', 'character_info', 'char_info'])
    @commands.cooldown(1, 5, BucketType.member)
    async def charinfo(self, ctx, *, characters: str):
        def to_string(c):
            digit = f'{ord(c):x}'
            name = unicodedata.name(c, 'Name not found.')
            return f'`\\U{digit:>08}`: {name} - **{c}** \N{EM DASH} <http://www.fileformat.info/info/unicode/char/{digit}>'
        msg = '\n'.join(map(to_string, characters))

        menu = menus.MenuPages(EmbedPageSource(msg.split("\n"), per_page=20), delete_message_after=True)
        await menu.start(ctx)

    @commands.command(help="Shows you who helped with the making of this bot", aliases=['credit'])
    async def credits(self, ctx):
        embed = discord.Embed(title="Credits", description="""
Owner: Ender2K89#9999
Helped make bot open-source and with a lot of other things: LeoCx1000#9999
Main help command page inspired by: Charles#5244
A lot of command ideas: Vicente0670 YT#0670
Tested verify command: Eiiknostv#2016
        """, timestamp=discord.utils.utcnow(), color=0x2F3136)

        await ctx.reply(embed=embed)

    @commands.command(help="Shows the current time", aliases=['date'])
    async def time(self, ctx):
        await ctx.reply(f"The current time is {discord.utils.format_dt(discord.utils.utcnow(), style='T')}")


def setup(client):
    client.add_cog(info(client))
