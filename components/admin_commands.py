import sqlite3
import hikari
import lightbulb
from Database import Database
from components.challenge_handler import Challenge, User, embed_creator, challenge_create, Settings
import random
import miru
import math

plugin = lightbulb.Plugin("Administrator Commands")
plugin.add_checks(lightbulb.checks.has_guild_permissions(hikari.Permissions.ADMINISTRATOR))


class View(miru.View):
    def __init__(self, data, n):
        self.current_page = None
        self.value = 1
        self.data = data
        self.n = n
        self.pages = math.ceil(len(self.data) / self.n)
        super().__init__(timeout=60)

    async def view_check(self, ctx: miru.Context) -> bool:
        return ctx.interaction.user == ctx.user

    async def on_timeout(self) -> None:
        i = 0
        for button in self.children:
            if not i:
                button.emoji = "❎"
                button.label = "Timed Out"
                button.style = hikari.ButtonStyle.DANGER
                button.disabled = True
                i += 1
                continue
            self.remove_item(button)
        await self.message.edit(components=self.build())

    @miru.button(label="Previous", style=hikari.ButtonStyle.PRIMARY, emoji="◀", disabled=True)
    async def previous_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.value -= 1
        description_second_half = ''
        self.current_page = [item for item in self.data[self.n * (self.value - 1):self.value * self.n]]

        if self.data:
            for id, days, peak, reward, min, max in self.current_page:
                peak_days = f"{peak} Days"
                length_desc = f"{id:3,} | {peak_days:14} | {reward:6,} | {min:3,} | {max:,}\n"
                description_second_half += length_desc

        header = 'ID. | Challenge Peak | Reward | Min | Max'
        description = f'```yaml\n{header}\n{len(header) * "="}\n'
        description += description_second_half
        description += '\n```'

        colour = random.randint(0x0, 0xFFFFFF)
        embed = hikari.Embed(title=f"Challenges List", description=description, colour=hikari.Colour(colour))
        embed.set_thumbnail(ctx.get_guild().icon_url)
        embed.set_footer(text=f"Page {self.value} of {self.pages}")

        if self.value <= 1:
            self.children[0].disabled = True
        else:
            self.children[0].disabled = False
        if self.value >= self.pages:
            self.children[1].disabled = True
        else:
            self.children[1].disabled = False
        await self.message.edit(embed=embed, components=self.build())

    @miru.button(label="Next", style=hikari.ButtonStyle.PRIMARY, emoji="▶")
    async def next_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.value += 1

        if self.value >= self.pages:
            self.children[1].disabled = True
            return await self.message.edit(components=self.build())

        description_second_half = ''
        self.current_page = [item for item in self.data[self.n * (self.value - 1):self.value * self.n]]

        if self.data:
            for id, days, peak, reward, min, max in self.current_page:
                peak_days = f"{peak} Days"
                length_desc = f"{id:3,} | {peak_days:14} | {reward:6,} | {min:3,} | {max:,}\n"
                description_second_half += length_desc

        header = 'ID. | Challenge Peak | Reward | Min | Max'
        description = f'```yaml\n{header}\n{len(header) * "="}\n'
        description += description_second_half
        description += '\n```'

        colour = random.randint(0x0, 0xFFFFFF)
        embed = hikari.Embed(title=f"Challenges List", description=description, colour=hikari.Colour(colour))
        embed.set_thumbnail(ctx.get_guild().icon_url)
        embed.set_footer(text=f"Page {self.value} of {self.pages}")

        if self.value <= 1:
            self.children[0].disabled = True
        else:
            self.children[0].disabled = False
        if self.value >= self.pages:
            self.children[1].disabled = True
        else:
            self.children[1].disabled = False
        await self.message.edit(embed=embed, components=self.build())


@plugin.command()
@lightbulb.command("challengelist", "Shows the list of ongoing challenge.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def challengelist(ctx: lightbulb.Context) -> None:
    challenge_list = [i for i in Database.get(' SELECT * FROM challengeProfile ')]
    description_second_half = ''

    if challenge_list:
        for id, days, peak, reward, min, max in challenge_list[:5]:
            peak_days = f"{peak} Days"
            length_desc = f"{id:3,} | {peak_days:14} | {reward:6,} | {min:3,} | {max:,}\n"
            description_second_half += length_desc

    header = 'ID. | Challenge Peak | Reward | Min | Max'
    description = f'```yaml\n{header}\n{len(header) * "="}\n'
    description += description_second_half
    description += '\n```'

    colour = random.randint(0x0, 0xFFFFFF)
    embed = hikari.Embed(title=f"Challenges List", description=description, colour=hikari.Colour(colour))
    embed.set_thumbnail(ctx.get_guild().icon_url)

    pages = math.ceil(len(challenge_list))/5
    embed.set_footer(text=f"Page 1 of {pages if pages else 1}")
    if pages:
        view = View(challenge_list, 5)
        proxy = await ctx.respond(embed=embed, components=view.build())
        message = await proxy.message()
        view.start(message)

    else:
        await ctx.respond(embed=embed)


@plugin.command()
@lightbulb.option("challenge_id", "The challenge ID that you're removing.", int)
@lightbulb.command("removechallenge", "Removes a challenge by their ID. Administrator Only.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def removechallenge(ctx: lightbulb.Context) -> None:
    Database.execute('DELETE FROM challengeProfile WHERE challenge_id = ? ', ctx.options.challenge_id)
    Database.execute('DELETE FROM challengeTracker WHERE challenge_id = ? ', ctx.options.challenge_id)
    return await embed_creator(ctx, f"Challenge Removed",
                               f"Successfully removed challenge **ID {ctx.options.challenge_id}**.")


@plugin.command()
@lightbulb.option("channel", "The channel you are enabling/disabling message count on.",
                  type=hikari.TextableChannel,
                  channel_types=[hikari.ChannelType.GUILD_TEXT])
@lightbulb.command("togglechannel",
                   "Toggles the eligiblity of a text channel for mountain-climbing. Administrator Only.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def togglechannel(ctx: lightbulb.Context) -> None:
    channel_object = ctx.get_guild().get_channel(ctx.options.channel)
    settings_object = Settings(ctx.guild_id)

    if channel_object.id in settings_object.get_channels():
        Database.execute('DELETE FROM channelTrackers WHERE guild_id = ? AND channel_id = ? ', ctx.guild_id,
                         channel_object.id)
        return await embed_creator(ctx,
                                   f"Channel Successfully Removed",
                                   f"Successfully removed {channel_object.mention} as an eligible channel.")

    Database.execute('INSERT INTO channelTrackers VALUES (?, ?) ', ctx.guild_id, channel_object.id)
    return await embed_creator(ctx,
                               f"Channel Successfully Added",
                               f"Successfully included {channel_object.mention} as an eligible channel.")


@plugin.command()
@lightbulb.option("days", "The days required to reach the peak.", int)
@lightbulb.option("rewards", "The trailmix reward players will get upon reaching the peak.", int)
@lightbulb.option("minimum", "The minimum trailmix reward players will get upon send a message.", int)
@lightbulb.option("maximum", "The maximum trailmix reward players will get upon send a message.", int)
@lightbulb.command("start", "Starts a new mountain challenge. Administrator Only.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def start(ctx: lightbulb.Context) -> None:
    if ctx.options.minimum > ctx.options.maximum:
        return embed_creator(ctx, "Error", "Minimum cannot be more than maximum. Please try again!")

    if ctx.options.minimum <= 0 or ctx.options.maximum <= 0:
        return embed_creator(ctx, "Error", "Please enter a valid positive integer for minimum and maximum.")

    if ctx.options.days <= 0:
        return embed_creator(ctx, "Error", "Please enter a valid positive integer for days.")

    i = 1
    while True:
        try:
            Database.execute(' INSERT INTO challengeProfile VALUES (?, ?, ?, ?, ?, ?) ', i, ctx.options.days,
                             ctx.options.days, ctx.options.rewards,
                             ctx.options.minimum, ctx.options.maximum)
            challenge_create(i)
            return await embed_creator(ctx,
                                       f"New Challenge Created",
                                       f"Successfully started a new mountain challenge. Mountain challenge ID is **{i}**")
        except sqlite3.IntegrityError:
            i += 1
            continue


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
