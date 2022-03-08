import hikari
import lightbulb

from PrefixDatabase import PrefixDatabase, prefix_dictionary

plugin = lightbulb.Plugin("Prefix Commands")
plugin.add_checks(lightbulb.checks.has_guild_permissions(hikari.Permissions.ADMINISTRATOR))


@plugin.command()
@lightbulb.option("prefix", "The new prefix of your server.", str)
@lightbulb.command("setprefix", "Updates the server's prefix. Administrator Only.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def setprefix(ctx: lightbulb.Context) -> None:
    PrefixDatabase.execute('UPDATE prefix SET prefix = ? WHERE guild_id = ? ', ctx.options.prefix, ctx.guild_id)
    embed = hikari.Embed(title="Prefix Successfully Updated",
                         description=f"Prefix for **{ctx.get_guild()}** is now set to `{ctx.options.prefix}`")
    prefix_dictionary.update({ctx.guild_id: ctx.options.prefix})
    await ctx.respond(embed=embed)


@plugin.command()
@lightbulb.command("myprefix", "Checks for the server's prefix. Administrator Only.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def myprefix(ctx: lightbulb.Context) -> None:
    prefix = [i[0] for i in PrefixDatabase.get('SELECT prefix FROM prefix WHERE guild_id = ? ', ctx.guild_id)][0]
    embed = hikari.Embed(description=f"Prefix for **{ctx.get_guild()}** is `{prefix}`")
    await ctx.respond(embed=embed)


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
