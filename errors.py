import discord
from discord.ext import commands

class CommandDoesntExist(commands.CheckFailure):
    pass

class AuthorBlacklisted(commands.CheckFailure):
    pass

class TooLongPrefix(commands.CheckFailure):
    pass

class TooManyPrefixes(commands.CheckFailure):
    pass

class PrefixAlreadyExists(commands.CheckFailure):
    pass

class PrefixDoesntExist(commands.CheckFailure):
    pass

class KillYourself(commands.CheckFailure):
    pass