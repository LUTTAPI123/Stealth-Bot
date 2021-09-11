import re, random, discord, lavalink, datetime as dt, typing, random
from time import time
from lavalink.events import (NodeChangedEvent, PlayerUpdateEvent,  # noqa: F401
                            QueueEndEvent, TrackEndEvent, TrackExceptionEvent,
                            TrackStartEvent, TrackStuckEvent)
from discord.ext import commands, menus
from discord.ext.menus.views import ViewMenuPages

url_rx = re.compile(r'https?://(?:www\.)?.+')
TIME_REGEX = r"([0-9]{1,2})[:ms](([0-9]{1,2})s?)?"

def setup(bot):
    bot.add_cog(music(bot))

class FullVoiceChannel(commands.CommandError):
    pass

class NotAuthorized(commands.CommandError):
    pass

class IncorrectChannelError(commands.CommandError):
    pass

class AlreadyConnectedToChannel(commands.CommandError):
    pass

class NoVoiceChannel(commands.CommandError):
    pass

class QueueIsEmpty(commands.CommandError):
    pass

class NoCurrentTrack(commands.CommandError):
    pass

class PlayerIsAlreadyPaused(commands.CommandError):
    pass

class PlayerIsNotPaused(commands.CommandError):
    pass

class NoMoreTracks(commands.CommandError):
    pass

class InvalidTimeString(commands.CommandError):
    pass

class NoPerms(commands.CommandError):
    pass

class NoConnection(commands.CommandError):
    pass

class AfkChannel(commands.CommandError):
    pass

class SkipInLoopMode(commands.CommandError):
    pass

class InvalidTrack(commands.CommandError):
    pass

class InvalidPosition(commands.CommandError):
    pass

class InvalidVolume(commands.CommandError):
    pass

#MENUS / DROPDOWNS
class QueueMenu(menus.ListPageSource):
    """Player queue paginator class."""
    def __init__(self, data):
        self.data = data
        super().__init__(data, per_page=10)

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page
        text = '1 song in the queue'
        if len(self.data) > 1:  text = f'{len(self.data)} songs in the queue'
        embed = discord.Embed(title=text, colour=discord.Color.blurple(),description = '\n'.join(f'`{i+1}.` {v}' for i, v in enumerate(entries, start=offset)))
        return embed
    def is_paginating(self):
        return True

class PlayMenu(discord.ui.Select):
    def __init__(self, data, bot, ctx):
        self.bot = bot
        self.ctx = ctx
        self.player = self.bot.lavalink.player_manager.get(ctx.guild.id)

        values = []
        integer = 0
        self.info = data
        for track in self.info:
            integer += 1
            title = track['info']['title'].upper()
            author = track['info']['author']
            id = track['info']['identifier']
            values.append(discord.SelectOption(label=title , value = id,description=author, emoji=f'{integer}\U0000fe0f\U000020e3'))
        values.append(discord.SelectOption(label='Cancel',description = 'Cancels the action and disconnects the player, if the queue remains empty.', emoji=f'<:redTick:596576672149667840>'))
        super().__init__(placeholder='Select a track', min_values=1, max_values=1, options=values)

    async def callback(self, interaction: discord.Interaction):
        for track in self.info:
            if self.values[0] == track['info']['identifier']:
                track = lavalink.models.AudioTrack(track, interaction.user, recommended=True)
                self.player.add(requester=interaction.user, track=track)
                embed = discord.Embed(color=discord.Color.blurple(),title = "Added a track to the queue",description = f"**[{track.title.upper()}]({track.uri})**")
                await interaction.message.delete()
                await self.ctx.send(embed=embed)
            if not self.player.is_playing:
                await self.player.play()
        if self.values[0] == 'Cancel':
            await interaction.message.delete()
            if not self.player.is_playing:
                await self.ctx.guild.change_voice_state(channel=None)

class PlayMenuView(discord.ui.View):
    def __init__(self, options, bot, ctx):
        super().__init__(timeout = 30.0)
        self.ctx = ctx
        self.add_item(PlayMenu(options, bot, ctx))
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return False
        else:
            return True

class LoopMenu(discord.ui.Select):
    def __init__(self, bot, ctx):
        self.bot = bot
        self.ctx = ctx
        self.player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        values = []
        if not self.player.loop == 1:
            values.append(discord.SelectOption(label='Track', emoji=f'🔂'))
        if not self.player.loop == 2:
            values.append(discord.SelectOption(label='Queue',emoji=f'🔁'))
        values.append(
            discord.SelectOption(label='Off',emoji=f'➡️'
        ))
        values.append(
            discord.SelectOption(label='Cancel',emoji=f'<:tickNo:885222934036226068>'
        ))
        super().__init__(placeholder='Select a loop mode', min_values=1, max_values=1, options=values)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == 'Track':
            self.player.set_loop(1)
            embed = discord.Embed(color=discord.Color.blurple(),description=f'Loop mode was set to `Track`')
            await interaction.message.delete()
            await self.ctx.send(embed=embed)

        if self.values[0] == 'Queue':
            self.player.set_loop(2)
            embed = discord.Embed(color=discord.Color.blurple(),description=f'Loop mode was set to `Queue`')
            await interaction.message.delete()
            await self.ctx.send(embed=embed)

        if self.values[0] == 'Off':
            self.player.set_loop(0)
            embed = discord.Embed(color=discord.Color.blurple(),description='Loop mode disabled')
            await interaction.message.delete()
            await self.ctx.send(embed=embed)

        if self.values[0] == 'Cancel':
            await interaction.message.delete()

class LoopMenuView(discord.ui.View):
    def __init__(self, bot, ctx):
        super().__init__(timeout = 30.0)
        self.ctx = ctx
        self.add_item(LoopMenu(bot, ctx))
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return False
        else:
            return True

class CustomPlayer(lavalink.BasePlayer):
    def __init__(self, guild_id, node):
        super().__init__(guild_id, node)

        self.dj = int
        self.play_random = False
        self.text_channel = None
        self.paused = False
        self._last_update = 0
        self._last_position = 0
        self.position_timestamp = 0
        self.volume = 100
        self.loop = 0

        self.queue = []
        self.current = None
        self.last_track = None

    @property
    def length(self):
        """ Returns the length of the queue. """
        return len(self.queue)

    @property
    def is_playing(self):
        """ Returns the player's track state. """
        return self.is_connected and self.current is not None

    @property
    def is_connected(self):
        """ Returns whether the player is connected to a voicechannel or not. """
        return self.channel_id is not None

    @property
    def upcoming(self):
        """ Returns whether the player is having next tracks or not. """
        if self.length > 0:
            return True

    @property
    def next(self):
        """ Returns the next track in the queue, if there is. """
        if self.length > 0:
            return None
        return self.queue[0]

    @property
    def position(self):
        """ Returns the position in the track, adjusted for Lavalink's 5-second stats interval. """
        if not self.is_playing:
            return 0

        if self.paused:
            return min(self._last_position, self.current.duration)

        difference = time() * 1000 - self._last_update
        return min(self._last_position + difference, self.current.duration)

    def add(self, requester: int, track: typing.Union[lavalink.AudioTrack, dict], index: int = None):
        """
        Adds a track to the queue.

        Parameters
        ----------
        requester: :class:`int`
            The ID of the user who requested the track.
        track: Union[:class:`AudioTrack`, :class:`dict`]
            The track to add. Accepts either an AudioTrack or
            a dict representing a track returned from Lavalink.
        index: Optional[:class:`int`]
            The index at which to add the track.
            If index is left unspecified, the default behaviour is to append the track. Defaults to `None`.
        """
        at = lavalink.AudioTrack(track, requester) if isinstance(track, dict) else track

        if index is None:
            self.queue.append(at)
        else:
            self.queue.insert(index, at)

    async def play(self, track: typing.Union[lavalink.AudioTrack, dict] = None, start_time: int = 0, end_time: int = 0, no_replace: bool = False):
        """
        Plays the given track.

        Parameters
        ----------
        track: Optional[Union[:class:`AudioTrack`, :class:`dict`]]
            The track to play. If left unspecified, this will default
            to the first track in the queue. Defaults to `None` so plays the next
            song in queue. Accepts either an AudioTrack or a dict representing a track
            returned from Lavalink.
        start_time: Optional[:class:`int`]
            Setting that determines the number of milliseconds to offset the track by.
            If left unspecified, it will start the track at its beginning. Defaults to `0`,
            which is the normal start time.
        end_time: Optional[:class:`int`]
            Settings that determines the number of milliseconds the track will stop playing.
            By default track plays until it ends as per encoded data. Defaults to `0`, which is
            the normal end time.
        no_replace: Optional[:class:`bool`]
            If set to true, operation will be ignored if a track is already playing or paused.
            Defaults to `False`
        """
        if track is not None and isinstance(track, dict):
            track = lavalink.AudioTrack(track, 0)

        if self.loop == 2 and self.last_track:
            self.queue.append(self.last_track)

        self._last_update = 0
        self._last_position = 0
        self.position_timestamp = 0
        self.paused = False

        if not track:
            if not self.queue:
                await self.stop()  # Also sets current to None.
                await self.node._dispatch_event(QueueEndEvent(self))
                return

            pop_at = random.randrange(len(self.queue)) if self.play_random else 0
            track = self.queue.pop(pop_at)

        options = {}

        if start_time is not None:
            if not isinstance(start_time, int) or not 0 <= start_time <= track.duration:
                raise ValueError('start_time must be an int with a value equal to, or greater than 0, and less than the track duration')
            options['startTime'] = start_time

        if end_time is not None:
            if not isinstance(end_time, int) or not 0 <= end_time <= track.duration:
                raise ValueError('end_time must be an int with a value equal to, or greater than 0, and less than the track duration')
            options['endTime'] = end_time

        if no_replace is None:
            no_replace = False
        if not isinstance(no_replace, bool):
            raise TypeError('no_replace must be a bool')
        options['noReplace'] = no_replace

        self.current = track
        self.last_track = track
        await self.node._send(op='play', guildId=self.guild_id, track=track.track, **options)
        await self.node._dispatch_event(TrackStartEvent(self, track))

    async def stop(self):
        """ Stops the player. """
        await self.node._send(op='stop', guildId=self.guild_id)
        self.current = None

    async def skip(self):
        """ Plays the next track in the queue, if any. """
        await self.play()

    def set_loop(self, mode: int):
        """
        Sets the player's loop state.
        Parameters
        ----------
        loop: :class:`int`
            0 = Will not loop.
            1 = Will loop current track.
            2 = will loop current queue.
        """
        if mode > 2:
            raise TypeError("Invalid loop mode.")
        self.loop = mode

    async def shuffle(self):
        """
        Randomizes the current order of tracks in the queue
        """
        random.shuffle(self.queue)

    async def set_pause(self, pause: bool):
        """
        Sets the player's paused state.

        Parameters
        ----------
        pause: :class:`bool`
            Whether to pause the player or not.
        """
        await self.node._send(op='pause', guildId=self.guild_id, pause=pause)
        self.paused = pause

    async def set_volume(self, vol: int):
        """
        Sets the player's volume

        Note
        ----
        A limit of 1000 is imposed by Lavalink.

        Parameters
        ----------
        vol: :class:`int`
            The new volume level.
        """
        self.volume = max(min(vol, 1000), 0)
        await self.node._send(op='volume', guildId=self.guild_id, volume=self.volume)

    async def seek(self, position: int):
        """
        Seeks to a given position in the track.

        Parameters
        ----------
        position: :class:`int`
            The new position to seek to in milliseconds.
        """
        await self.node._send(op='seek', guildId=self.guild_id, position=position)

    async def _handle_event(self, event):
        """
        Handles the given event as necessary.

        Parameters
        ----------
        event: :class:`Event`
            The event that will be handled.
        """
        if isinstance(event, (TrackStuckEvent, TrackExceptionEvent)) or \
                isinstance(event, TrackEndEvent) and event.reason == 'FINISHED':
            await self.play()
        if isinstance(event, (TrackStuckEvent, TrackExceptionEvent)) or \
                isinstance(event, TrackEndEvent):
            if self.loop == 1:
                await self.play(self.last_track)

    async def _update_state(self, state: dict):
        """
        Updates the position of the player.

        Parameters
        ----------
        state: :class:`dict`
            The state that is given to update.
        """
        self._last_update = time() * 1000
        self._last_position = state.get('position', 0)
        self.position_timestamp = state.get('time', 0)

        event = PlayerUpdateEvent(self, self._last_position, self.position_timestamp)
        await self.node._dispatch_event(event)

    async def change_node(self, node):
        """
        Changes the player's node

        Parameters
        ----------
        node: :class:`Node`
            The node the player is changed to.
        """
        if self.node.available:
            await self.node._send(op='destroy', guildId=self.guild_id)

        old_node = self.node
        self.node = node

        if self._voice_state:
            await self._dispatch_voice_update()

        if self.current:
            await self.node._send(op='play', guildId=self.guild_id, track=self.current.track, startTime=self.position)
            self._last_update = time() * 1000

            if self.paused:
                await self.node._send(op='pause', guildId=self.guild_id, pause=self.paused)

        if self.volume != 100:
            await self.node._send(op='volume', guildId=self.guild_id, volume=self.volume)

        if any(self.equalizer):  # If any bands of the equalizer was modified
            payload = [{'band': b, 'gain': g} for b, g in enumerate(self.equalizer)]
            await self.node._send(op='equalizer', guildId=self.guild_id, bands=payload)

        await self.node._dispatch_event(NodeChangedEvent(self, old_node, node))

class music(commands.Cog):
    """
    🎵 Commands related to playing music through the bot in a voice channel (made by DaPandaOfficial🐼#5684).
    """
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, 'lavalink'):  # This ensures the client isn't overwritten during cog reloads.
            bot.lavalink = lavalink.Client(bot.user_id,CustomPlayer)
            bot.lavalink.add_node('lava.link', 80, 'anything as a password' 'eu', 'default-node', 5)  # Host, Port, Password, Region, Name
            bot.add_listener(bot.lavalink.voice_update_handler, 'on_socket_custom_receive')
        lavalink.add_event_hook(self.track_hook)

    def cog_unload(self):
        """ Cog unload handler. This removes any event hooks that were registered. """
        self.bot.lavalink._event_hooks.clear()

    async def cog_before_invoke(self, ctx):
        """ Command before-invoke handler. """
        guild_check = ctx.guild is not None
        if guild_check:
            await self.ensure_voice(ctx)
        return guild_check

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send(error.original)

        if isinstance(error, IncorrectChannelError):
            player = self.bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
            channel = self.bot.get_channel(int(player.channel_id))
            embed = discord.Embed(color = discord.Color.red(),description = f'{ctx.author.mention}, you must be in {channel.mention} for this session.')
            return await ctx.send(embed=embed)

        if isinstance(error, NoVoiceChannel):
            embed = discord.Embed(color = discord.Color.red(),description = "I'm not connected to any voice channels.")
            return await ctx.send(embed=embed)

        if isinstance(error, AlreadyConnectedToChannel):
            embed = discord.Embed(color = discord.Color.red(),description = "Already connected to a voice channel.")
            return await ctx.send(embed=embed)

        if isinstance(error, QueueIsEmpty):
            embed = discord.Embed(color = discord.Color.red(),description = "There are no tracks in the queue.")
            return await ctx.send(embed=embed)

        if isinstance(error, PlayerIsAlreadyPaused):
            embed = discord.Embed(color = discord.Color.red(),description = "The current track is already paused.")
            return await ctx.send(embed=embed)

        if isinstance(error, NoMoreTracks):
            embed = discord.Embed(color = discord.Color.red(),description = "There are no more tracks in the queue.")
            return await ctx.send(embed=embed)

        if isinstance(error, NoCurrentTrack):
            embed = discord.Embed(color = discord.Color.red(),description = "There is no track currently playing.")
            return await ctx.send(embed=embed)

        if isinstance(error, FullVoiceChannel):
            embed = discord.Embed(color = discord.Color.red(),description = f'I can\'t join {ctx.author.voice.channel.mention}, because it\'s full.')
            return await ctx.send(embed=embed)

        if isinstance(error, NoPerms):
            embed = discord.Embed(color = discord.Color.red(),description = "I don't have permissions to `CONNECT` or `SPEAK`.")
            return await ctx.send(embed=embed)

        if isinstance(error, NoConnection):
            embed = discord.Embed(color = discord.Color.red(),description = "You must be connected to a voice channel to use voice commands.")
            return await ctx.send(embed=embed)

        if isinstance(error, PlayerIsNotPaused):
            embed = discord.Embed(color = discord.Color.red(),description = "The current track is not paused.")
            return await ctx.send(embed=embed)

        if isinstance(error, AfkChannel):
            embed = discord.Embed(color=discord.Color.red(),description="I can't play music in the afk channel.")
            return await ctx.send(embed=embed)

        if isinstance(error, NotAuthorized):
            embed = discord.Embed(colour = discord.Color.red(),description = "You cannot perform this action.")
            return await ctx.send(embed=embed)

        if isinstance(error, InvalidTrack):
            embed = discord.Embed(colour = discord.Color.red(),description = "Can't perform action on track that is out of the queu.")
            return await ctx.send(embed=embed)

        if isinstance(error, InvalidPosition):
            embed = discord.Embed(colour = discord.Color.red(),description = "Can't perform action with invalid position in the queue.")
            return await ctx.send(embed=embed)

        if isinstance(error, InvalidVolume):
            embed = discord.Embed(color = discord.Color.red(),description = 'Please enter a value between 1 and 100')
            return await ctx.send(embed=embed)

    async def ensure_voice(self, ctx):
        """ This check ensures that the bot and command author are in the same voicechannel. """
        player = self.bot.lavalink.player_manager.create(ctx.guild.id, endpoint=str(ctx.guild.region))
        should_connect = ctx.command.name in ('play',)

        if not ctx.author.voice or not ctx.author.voice.channel:
            raise NoConnection()
        if not player.is_connected:
            if not should_connect:
                raise NoVoiceChannel()
            if ctx.guild.afk_channel:
                if ctx.author.voice.channel.id == ctx.guild.afk_channel.id:
                    raise AfkChannel()
            permissions = ctx.author.voice.channel.permissions_for(ctx.me)
            if ctx.author.voice.channel.user_limit != 0:
                limit = ctx.author.voice.channel.user_limit
                if len(ctx.author.voice.channel.members) == limit:
                    raise FullVoiceChannel()
            if not permissions.connect or not permissions.speak:
                raise NoPerms()
            player.text_channel = ctx.channel.id
            player.dj = ctx.author.id
            await ctx.guild.change_voice_state(channel=ctx.author.voice.channel,self_deaf=True)
        else:
            if int(player.channel_id) != ctx.author.voice.channel.id:
                raise IncorrectChannelError()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        player = self.bot.lavalink.player_manager.get(member.guild.id)
        if player is None:
            return
        if not player.channel_id or not player:
            self.bot.lavalink.player_manager.remove(member.guild.id)
            return
        channel = self.bot.get_channel(int(player.channel_id))
        if member == player.dj and after.channel is None:
            for m in channel.members:
                if m.bot:
                    continue
                else:
                    player.dj =m
                    return

        elif after.channel == channel and player.dj not in channel.members:
            player.dj = member

        if player.is_connected:
            if len(channel.members) == 1:
                player.queue.clear()
                await player.stop()
                await member.guild.change_voice_state(channel=None)

    async def track_hook(self, event):
        if isinstance(event, TrackStartEvent):
            if event.player.loop != 1:
                channel = self.bot.get_channel(int(event.player.text_channel))
                thumnail = f'https://img.youtube.com/vi/{event.track.identifier}/maxresdefault.jpg'
                embed = discord.Embed(title=f'Now playing', color=discord.Color.blurple(),description = f'**[{event.track.title.upper()}]({event.track.uri})**' )
                embed.set_thumbnail(url=thumnail)
                embed.add_field(name="Artist:", value=f'{event.track.author}', inline=True)
                embed.add_field(name='Duration:', value=f'{str(dt.timedelta(milliseconds=int(event.track.duration)))}', inline=True)
                embed.add_field(name='Requested by:', value=event.track.requester.mention, inline=True)
                await channel.send(embed=embed)

    def is_privileged(self, ctx: commands.Context):
        """Check whether the user is an Admin or DJ or alone in a VC."""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if len(ctx.author.voice.channel.members) == 2:return True #Already giving the dj perms if the original dj disconnects ?
        elif player.dj == ctx.author.id: return True
        elif ctx.author.guild_permissions.manage_messages: return True
        else: return False

    @commands.command(name="play", aliases=['p'])
    async def play_command(self, ctx: commands.Context,*,query: str):
        """Loads your input and adds it to the queue; If there is no playing track, then it will start playing"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        query = query.strip('<>')
        if not url_rx.match(query): query = f'ytsearch:{query}'
        results = await player.node.get_tracks(query)

        # Results could be None if Lavalink returns an invalid response (non-JSON/non-200 (OK)).
        # ALternatively, resullts['tracks'] could be an empty array if the query yielded no tracks.
        if not results or not results['tracks']:
            embedVar = discord.Embed(colour=discord.Color.red())
            embedVar.description = 'No songs were found with that query. Please try again.'
            return await ctx.send(embed=embedVar)
        # Valid loadTypes are:
        #   TRACK_LOADED    - single video/direct URL)
        #   PLAYLIST_LOADED - direct URL to playlist)
        #   SEARCH_RESULT   - query prefixed with either ytsearch: or scsearch:.
        #   NO_MATCHES      - query yielded no results
        #   LOAD_FAILED     - most likely, the video encountered an exception during loading.
        if results['loadType'] == 'TRACK_LOADED':
            track = lavalink.models.AudioTrack(results['tracks'][0], ctx.author, recommended=True)
            player.add(requester=ctx.author, track=track)
            embed = discord.Embed(color=discord.Color.blurple(),title = "Added a track to the queue",description = f"**[{track.title.upper()}]({track.uri})**")
            await ctx.send(embed=embed)
            if not player.is_playing:
                await player.play()

        if results['loadType'] == 'PLAYLIST_LOADED':
            tracks = results['tracks']
            for track in tracks:
                player.add(requester=ctx.author, track=track)

            embed = discord.Embed(color=discord.Color.blurple(),title = "Added a playlist to the queue",description = f'**[{results["playlistInfo"]["name"]}]({query})** with {len(tracks)} songs.')
            await ctx.send(embed=embed)
            if not player.is_playing:
                await player.play()

        if results['loadType'] == 'SEARCH_RESULT':
            tracks = results['tracks'][0:9]
            embed = discord.Embed(color = discord.Color.blurple())
            integer = 0
            info = []
            for track in tracks:
                integer += 1
                info.append(f"`{integer}` **[{track['info']['title'].upper()}]({track['info']['uri']})**\n")
            embed.description = '\n'.join(x for x in info)
            await ctx.send(embed=embed, view = PlayMenuView(tracks,self.bot,ctx))

        if results['loadType'] == 'NO_MATCHES':
            embedVar = discord.Embed(colour=discord.Color.red(),description = 'No songs were found with that query. Please try again.')
            await ctx.send(embed=embedVar)

        if results['loadType'] == 'LOAD_FAILED':
            embedVar = discord.Embed(colour=discord.Color.red(),description = 'Failed loading your query.')
            await ctx.send(embed=embedVar)

    @commands.command(name="disconnect", aliases=['dc'])
    async def disconnect_command(self,ctx: commands.Context):
        """Disconnects the bot from your voice channel and clears the queue"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        #CHECKING
        if not player.is_connected: raise NoVoiceChannel
        if not self.is_privileged(ctx): raise NotAuthorized
        #ACTUAL PART
        embed = discord.Embed(colour = discord.Color.blurple(),description = 'The player was disconnected.')
        player.queue.clear()
        await player.stop()
        await ctx.guild.change_voice_state(channel=None)
        return await ctx.send(embed=embed)

    @commands.command(name="pause")
    async def pause_command(self,ctx: commands.Context):
        """Pauses playback"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        #CHECKING
        if not player.is_connected: raise NoVoiceChannel
        if not self.is_privileged(ctx): raise NotAuthorized
        if player.paused: raise PlayerIsAlreadyPaused
        #ACTUAL PART
        await player.set_pause(True)
        embed = discord.Embed(color = discord.Color.blurple(),description = "The playback was paused.")
        return await ctx.send(embed=embed)

    @commands.command(name="resume", aliases=['unpause'])
    async def resume_command(self,ctx: commands.Context):
        """Resumes playback"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        #CHECKING
        if not player.is_connected: raise NoVoiceChannel
        if not self.is_privileged(ctx): raise NotAuthorized
        if not player.paused: raise PlayerIsNotPaused()
        #ACTUAL PART
        await player.set_pause(False)
        embed = discord.Embed(color = discord.Color.blurple(),description = "The playback was resumed.")
        return await ctx.send(embed=embed)

    @commands.command(name="stop")
    async def stop_command(self,ctx: commands.Context):
        """Stops the currently playing track and removes all tracks from the queue"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        #CHECKING
        if not player.is_connected: raise NoVoiceChannel
        if not self.is_privileged(ctx): raise NotAuthorized
        if player.loop == 2: player.set_loop(0)
        #ACTUAL PART
        player.queue.clear()
        await player.stop()
        embed = discord.Embed(color = discord.Color.blurple(),description = "The playback was stopped.")
        return await ctx.send(embed=embed)

    @commands.command(name="clear_queue")
    async def clear_queue_command(self,ctx: commands.Context):
        """Removes all tracks from the queue"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        #CHECKING
        if not player.is_connected: raise NoVoiceChannel
        if not self.is_privileged(ctx):raise NotAuthorized
        if not player.length > 0: raise QueueIsEmpty
        if player.loop == 2: player.set_loop(0)
        #ACTUAL PART
        player.queue.clear()
        embed = discord.Embed(color = discord.Color.blurple(),description = "Playback stopped.")
        return await ctx.send(embed=embed)

    @commands.command(name="skip", aliases=["next"])
    async def skip_command(self,ctx: commands.Context):
        """Skips to the next song"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        #CHECKING
        if not player.is_connected: raise NoVoiceChannel
        if not self.is_privileged(ctx): raise NotAuthorized
        if player.length == 0: raise NoMoreTracks
        #ACTUAL PART
        if player.loop == 1: player.set_loop(0)
        await player.stop()
        await player.skip()

    @commands.command(name="shuffle")
    async def shuffle_command(self,ctx: commands.Context):
        """Randomizes the current order of tracks in the queue"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        #CHECKING
        if not player.is_connected: raise NoVoiceChannel
        if not self.is_privileged(ctx): raise NotAuthorized
        #ACTUAL PART
        player.shuffle()
        embed = discord.Embed(color = discord.Color.blurple(),description = "The current queue was shuffled.")
        return await ctx.send(embed=embed)

    @commands.command(name="loop", aliases=['repeat'])
    async def loop_command(self,ctx: commands.Context):
        """Starts/Stops looping your currently playing track"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.is_connected: raise NoVoiceChannel
        if not self.is_privileged(ctx): raise NotAuthorized
        #ACTUAL PART
        embed = discord.Embed(color = discord.Color.blurple(),description = "Choose loop mode\
            \n**:repeat_one: Track** - Starts looping your currently playing track.\
            \n**:repeat: Queue** - Starts looping your current queue.\
            \n **:arrow_right: Off** - Stops looping.\
            \n**<:tickNo:885222934036226068> Cancel** - Cancels the action.")
        await ctx.send(embed=embed,view = LoopMenuView(self.bot, ctx))

    @commands.command(name="queue",aliases=['q', 'que', 'list', 'upcoming'])
    async def queue_command(self,ctx: commands.Context):
        """Displays the current song queue"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        #CHECKING
        if not player.is_connected: raise NoVoiceChannel
        if player.length == 0: raise QueueIsEmpty
        #ACTUAL PART
        info = []
        for x in player.queue:
            info.append(f'**[{x.title.upper()}]({x.uri})** ({str(dt.timedelta(milliseconds=int(x.duration)))})\n')
        paginator = ViewMenuPages(source=QueueMenu(info), clear_reactions_after=True)
        await paginator.start(ctx)

    @commands.command(name="current", aliases=["np", "playing", "track"])
    async def playing_command(self,ctx: commands.Context):
        """Displays info about the current track in the queue"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        #CHECKINFG
        if not player.is_connected: raise NoVoiceChannel
        if not player.is_playing: raise NoCurrentTrack
        #ACTUAL PART
        thumnail = f"https://img.youtube.com/vi/{player.current.identifier}/maxresdefault.jpg"
        embed = discord.Embed(title=f'Current Track',color=discord.Color.blurple(),description = f'**[{player.current.title.upper()}]({player.current.uri})**')
        embed.set_thumbnail(url=thumnail)
        embed.add_field(name="Artist:", value=f'{player.current.author}', inline=True)
        embed.add_field(name='Duration:', value=f'{str(dt.timedelta(milliseconds=int(player.current.duration)))}', inline=True)
        embed.add_field(name='Requested By:', value=f'{player.current.requester.mention}', inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="restart")
    async def restart_command(self,ctx: commands.Context):
        """Restarts the current track in the queue"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        #CHECKING
        if not player.is_connected: raise NoVoiceChannel
        if not self.is_privileged(ctx): raise NotAuthorized
        if not player.current: raise NoCurrentTrack
        #ACTUAL PART
        await player.seek(0)
        embed = discord.Embed(color = discord.Color.blurple(),description = f"The current track was restarted.")
        return await ctx.send(embed=embed)

    @commands.command(name="seek")
    async def seek_command(self,ctx: commands.Context, position: str):
        """Skips to the specified timestamp in the currently playing track"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        #CHECKING
        if not player.is_connected: raise NoVoiceChannel
        if not self.is_privileged(ctx): raise NotAuthorized
        if not player.current:raise NoCurrentTrack()
        if not (match := re.match(TIME_REGEX, position)): raise InvalidTimeString
        if match.group(3): secs = (int(match.group(1)) * 60) + (int(match.group(3)))
        else: secs = int(match.group(1))
        #ACTUAL PART
        await player.seek(secs * 1000)
        embed = discord.Embed(color = discord.Color.blurple(),description = f"The current track was seeked to **{position}**.")
        return await ctx.send(embed=embed)

    @commands.command(name="volume",aliases=['vol'])
    async def volume_command(self,ctx: commands.Context, volume: int = None):
        """Sets the player's volume; If there is not input, it will return the current value"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        #CHECKING
        if not player.is_connected: raise NoVoiceChannel
        if volume is None:
            embed = discord.Embed(colour = discord.Color.blurple(),description = f'Current volume: **{player.volume}%**')
            return await ctx.send(embed=embed)
        if not self.is_privileged(ctx): raise NotAuthorized
        if not 0 < volume < 101: raise InvalidVolume
        #ACTUAL PART
        await player.set_volume(volume)
        embed = discord.Embed(colour = discord.Color.blurple(),description = f'The volume was set to **{player.volume}%**')
        return await ctx.send(embed=embed)

    @commands.command(name="remove")
    async def remove_range_command(self,ctx: commands.Context,start: int,*,end: int= None):
        """Removes all the tracks from the specified start through the specified end (if the end is not specified it will remove only one track)"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        #CHECKING
        if not player.is_connected: raise NoVoiceChannel
        if not self.is_privileged(ctx): raise NotAuthorized
        if player.length == 0: raise QueueIsEmpty
        if start < 0: raise InvalidPosition
        if end and end > player.length: raise InvalidTrack
        #ACTUAL PART
        if end == None or start == end :
            embed = discord.Embed(color = discord.Color.blurple(),description=f'Successfully removed **[{player.queue[start-1].title.upper()}]({player.queue[start-1].uri})** from the queue')
            del player.queue[start-1]
        else:
            embed = discord.Embed(color = discord.Color.blurple(),description=f'Successfully removed tracks **`{start}`** to **`{end}`** from the queue ({len(player.queue[start-1:end-1])} tracks)')
            del player.queue[start-1:end]
        await ctx.send(embed=embed,footer = False)

    @commands.command(name="move")
    async def move_command(self,ctx: commands.Context,position: int,*,track: str):
        """Moves the specified song to the specified position"""
        player = self.bot.lavalink.player_manager.get(ctx.guild.id)
        if not player.is_connected: raise NoVoiceChannel
        if not self.is_privileged(ctx): raise NotAuthorized
        if player.length == 0: raise QueueIsEmpty
        if position < 0 or position > player.length: raise InvalidPosition
        #ACTUAL PART
        queue = player.queue
        for x in queue:
            if x['title'].upper() == track.upper():
                queue.insert(position-1, queue.pop(queue.index(x)))
                embed = discord.Embed(color = discord.Color.blurple(),description=f'Successfully moved **[{x["title"]}]({x["uri"]})** to position `{position}`')
                return await ctx.send(embed=embed)
        embed = discord.Embed(color = discord.Color.red(),description='Track not found.')
        return await ctx.send(embed=embed)
