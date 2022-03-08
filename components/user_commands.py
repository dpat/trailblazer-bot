import sqlite3
import hikari
import lightbulb
from Database import Database
from components.challenge_handler import Challenge, User, embed_creator
import random
import miru
import math

plugin = lightbulb.Plugin("User Commands")


class View(miru.View):
    def __init__(self, data, n, main_data):
        self.current_page = None
        self.value = 1
        self.data = data
        self.n = n
        self.main_data = main_data
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
            for challenge_id, challenge_completed_day in self.current_page:
                challenge_object = Challenge(challenge_id)
                days = f"{challenge_completed_day} Days"
                peak_days = f"{challenge_object.get_peak()} Days"
                length_desc = f"{challenge_id:13,} | {days:16} | {peak_days}\n"
                description_second_half += length_desc

        header = 'Challenge ID. | Current Progress | Challenge Peak'
        description = f'```yaml\n{header}\n{len(header) * "="}\n'
        description += description_second_half
        description += '\n```'

        colour = random.randint(0x0, 0xFFFFFF)
        embed = hikari.Embed(title=f"{ctx.interaction.user}'s Profile", description=description,
                             colour=hikari.Colour(colour))
        embed.set_thumbnail(ctx.interaction.user.display_avatar_url)
        trailmix, peaks, msg_count = self.main_data
        embed.set_footer(text=f"Page {self.value} of {self.pages}")
        embed.add_field(name="Trailmix", value=trailmix)
        embed.add_field(name="Peaks Completed", value=peaks)
        embed.add_field(name="Message Count", value=msg_count)

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
            for challenge_id, challenge_completed_day in self.current_page:
                challenge_object = Challenge(challenge_id)
                days = f"{challenge_completed_day} Days"
                peak_days = f"{challenge_object.get_peak()} Days"
                length_desc = f"{challenge_id:13,} | {days:16} | {peak_days}\n"
                description_second_half += length_desc

        header = 'Challenge ID. | Current Progress | Challenge Peak'
        description = f'```yaml\n{header}\n{len(header) * "="}\n'
        description += description_second_half
        description += '\n```'

        colour = random.randint(0x0, 0xFFFFFF)
        embed = hikari.Embed(title=f"{ctx.interaction.user}'s Profile", description=description,
                             colour=hikari.Colour(colour))
        embed.set_thumbnail(ctx.interaction.user.display_avatar_url)
        trailmix, peaks, msg_count = self.main_data
        embed.set_footer(text=f"Page {self.value} of {self.pages}")
        embed.add_field(name="Trailmix", value=trailmix)
        embed.add_field(name="Peaks Completed", value=peaks)
        embed.add_field(name="Message Count", value=msg_count)
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
@lightbulb.command("profile", "Shows your profile.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def profile(ctx: lightbulb.Context) -> None:
    user_object = User(ctx.author.id)
    user_challenges = user_object.get_challenges()
    description_second_half = ''

    if user_challenges:
        for challenge_id, challenge_completed_day in user_challenges[:5]:
            challenge_object = Challenge(challenge_id)
            days = f"{challenge_completed_day} Days"
            peak_days = f"{challenge_object.get_peak()} Days"
            length_desc = f"{challenge_id:13,} | {days:16} | {peak_days}\n"
            description_second_half += length_desc

    header = 'Challenge ID. | Current Progress | Challenge Peak'
    description = f'```yaml\n{header}\n{len(header) * "="}\n'
    description += description_second_half
    description += '\n```'

    trailmix = user_object.get_trailmix()
    peaks = user_object.get_peaks_completed()
    msg_count = user_object.get_message_count()
    main_data = [trailmix, peaks, msg_count]
    colour = random.randint(0x0, 0xFFFFFF)
    embed = hikari.Embed(title=f"{ctx.author}'s Profile", description=description, colour=hikari.Colour(colour))
    embed.add_field(name="Trailmix", value=trailmix)
    embed.add_field(name="Peaks Completed", value=peaks)
    embed.add_field(name="Message Count", value=msg_count)
    embed.set_thumbnail(ctx.author.display_avatar_url)
    pages = math.ceil(len(user_challenges))/5
    embed.set_footer(text=f"Page 1 of {pages if pages else 1}")
    if pages:
        view = View(user_challenges, 5, main_data)
        proxy = await ctx.respond(embed=embed, components=view.build())
        message = await proxy.message()
        view.start(message)

    else:
        await ctx.respond(embed=embed)


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
