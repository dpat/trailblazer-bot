import hikari
import lightbulb
import sqlite3
import asyncio
import pytz

from Database import Database
import random
import datetime

plugin = lightbulb.Plugin("Challenge Handler")

conn = sqlite3.connect('bot.db', timeout=5.0)
c = conn.cursor()
conn.row_factory = sqlite3.Row


async def embed_creator(ctx: lightbulb.Context, title: str, description: str):
    colour = random.randint(0x0, 0xFFFFFF)
    embed = hikari.Embed(title=title, description=description, colour=hikari.Colour(colour))
    embed.set_footer(text=f"Command used by {ctx.author}", icon=ctx.author.display_avatar_url)
    return await ctx.respond(embed=embed)


c.execute(
    '''CREATE TABLE IF NOT EXISTS userProfile (
    user_id INT PRIMARY KEY,
    peaks_completed INT DEFAULT 0,
    trailmix INT DEFAULT 0,
    message_count INT DEFAULT 0 
    )''')

c.execute(
    '''CREATE TABLE IF NOT EXISTS channelTrackers (
    guild_id INT, 
    channel_id INT,
    UNIQUE(guild_id, channel_id)
    )''')

c.execute(
    '''CREATE TABLE IF NOT EXISTS challengeTracker (
    user_id INT,
    challenge_id INT,
    challenge_completed_day INT DEFAULT 0,
    challenge_cooldown INT DEFAULT 0,
    UNIQUE(user_id, challenge_id)
    )''')

c.execute(
    '''CREATE TABLE IF NOT EXISTS challengeProfile (
    challenge_id INT PRIMARY KEY,
    challenge_days INT,
    challenge_peak INT,
    challenge_reward INT,
    challenge_trailmix_min INT,
    challenge_trailmix_max INT
    )
    '''
)


@plugin.listener(hikari.GuildMessageCreateEvent)
async def on_message(event: hikari.GuildMessageCreateEvent):
    if not event.is_human:
        return

    channel_objects = Settings(event.guild_id)
    channel_list = channel_objects.get_channels()

    if channel_list:
        if event.channel_id not in channel_list:
            return

        if len(event.message.content.split()) < 15 or len(event.message.content) < 75:
            msg = await event.message.respond(f"{event.author.mention}, your message is too short!")
            await asyncio.sleep(5)
            await msg.delete()
            return

        all_challenges = [i[0] for i in Database.get('SELECT challenge_id FROM challengeProfile')]

        for challenge_id in all_challenges:
            challenge_object = Challenge(challenge_id)
            user_object = User(event.author_id)
            challenge_object.get_peak()
            challenge_object.get_reward()
            challenge_object.get_trailmix_range()
            before_completed_days = user_object.get_specific_challenge(challenge_id)
            time_to_reset = (datetime.datetime.utcnow() + datetime.timedelta(days=1, hours=8)).replace(hour=00,
                                                                                                       minute=00,
                                                                                                       second=00,
                                                                                                       microsecond=00)

            if before_completed_days >= challenge_object.peak:  # If already completed
                continue

            challenge_check = user_object.challenge_transaction(challenge_id)

            if not challenge_check:  # If not yet finished cooldown
                embed = hikari.Embed(title="Climb Failed",
                                     description=f"{event.author.mention}, You've already sent a message for the day. "
                                                 f"You will be able to climb again in <t:{int(time_to_reset.timestamp())}:R>")
                embed.set_footer(text=f"Ascended {before_completed_days} of {challenge_object.peak} days",
                                 icon=event.author.display_avatar_url)
                return await event.message.respond(embed=embed)

            # If successfully submitted
            after_completed_days = user_object.get_specific_challenge(challenge_id)
            user_object.message_count_transaction(1)
            trailmix_amount = random.choice(range(challenge_object.min, challenge_object.max + 1))
            user_object.trailmix_transaction(trailmix_amount)

            embed = hikari.Embed(title="Climb Successful",
                                 description=f"{event.author.mention}, You've ascended one step for Challenge #{challenge_id} and earned "
                                             f"{trailmix_amount:,} Trailmix. "
                                             f"You will be able to climb again in <t:{int(time_to_reset.timestamp())}:R>")
            embed.set_footer(text=f"Ascended {after_completed_days} of {challenge_object.peak} days",
                             icon=event.author.display_avatar_url)
            await event.message.respond(embed=embed)

            if after_completed_days >= challenge_object.peak:
                user_object.peaks_transaction(1)
                user_object.trailmix_transaction(challenge_object.reward)
                embed = hikari.Embed(title="Peak Reached",
                                     description=f"{event.author.mention}, You've ascended to the peak for Challenge #{challenge_id} and earned "
                                                 f"the peak reward of **{challenge_object.reward:,} Trailmix**. Congratulations!")
                embed.set_footer(text=f"Ascended {after_completed_days} of {challenge_object.peak} days",
                                 icon=event.author.display_avatar_url)
                await event.message.respond(embed=embed)


class Settings:
    def __init__(self, guild_id: int):
        self.channels = None
        self.guild_id = guild_id

    def get_channels(self):
        self.channels = [i[0] for i in
                         Database.get('SELECT channel_id FROM channelTrackers WHERE guild_id = ? ', self.guild_id)]
        return self.channels


class User:
    def __init__(self, user_id):
        self.challenges = None
        self.peaks_completed = None
        self.trailmix = None
        self.message_count = None
        self.user_id = user_id

    def user_item_quantity(self, item_name: str):
        quantity = [i[0] for i in
                    Database.get('SELECT quantity FROM userInventory WHERE item_name = ? AND user_id = ? ',
                                     item_name, self.user_id)][0]
        return quantity

    def shop_transaction(self, amount: int) -> int:
        self.trailmix = self.get_trailmix()

        if self.trailmix + amount < 0:
            return False

        self.trailmix += amount
        Database.execute('UPDATE userProfile SET trailmix = ? WHERE user_id = ? ', self.trailmix, self.user_id)
        return True

    def trailmix_transaction(self, amount: int) -> int:
        self.trailmix = self.get_trailmix()
        self.trailmix += amount
        Database.execute('UPDATE userProfile SET trailmix = ? WHERE user_id = ? ', self.trailmix, self.user_id)
        return self.trailmix

    def peaks_transaction(self, amount: int) -> int:
        self.peaks_completed = self.get_peaks_completed()
        self.peaks_completed += amount
        Database.execute('UPDATE userProfile SET peaks_completed = ? WHERE user_id = ? ', self.peaks_completed,
                         self.user_id)
        return self.peaks_completed

    def message_count_transaction(self, amount: int) -> int:
        self.message_count = self.get_message_count()
        self.message_count += amount
        Database.execute('UPDATE userProfile SET message_count = ? WHERE user_id = ? ', self.message_count,
                         self.user_id)
        return self.message_count

    def challenge_transaction(self, challenge_id: int):
        challenge_object = Challenge(challenge_id)
        challenge_object.get_specific_challenge(self.user_id)

        now = datetime.datetime.now().timestamp()
        reset = (datetime.datetime.utcnow() + datetime.timedelta(days=1, hours=8)).replace(hour=00, minute=00,
                                                                                           second=00,
                                                                                           microsecond=00).timestamp()
        if now > challenge_object.cooldown:
            challenge_object.challenge_day += 1
            Database.execute('UPDATE challengeTracker SET challenge_completed_day = ?, '
                             'challenge_cooldown = ? WHERE user_id = ? AND challenge_id = ? ',
                             challenge_object.challenge_day, reset,
                             self.user_id, challenge_id)
            return True
        return False

    def get_peaks_completed(self):
        try:
            self.peaks_completed = \
                Database.get('SELECT peaks_completed FROM userProfile WHERE user_id = ? ', self.user_id)[0][0]
            return self.peaks_completed

        except IndexError:
            return None

    def get_trailmix(self):
        try:
            self.trailmix = Database.get('SELECT trailmix FROM userProfile WHERE user_id = ? ', self.user_id)[0][0]
            return self.trailmix

        except IndexError:
            return None

    def get_message_count(self):
        try:
            self.message_count = \
                Database.get('SELECT message_count FROM userProfile WHERE user_id = ? ', self.user_id)[0][0]
            return self.message_count

        except IndexError:
            return None

    def get_challenges(self) -> []:
        self.challenges = [i for i in Database.get(
            'SELECT challenge_id, challenge_completed_day FROM challengeTracker WHERE user_id = ? ', self.user_id)]
        return self.challenges

    def get_specific_challenge(self, challenge_id: int):
        return [i[0] for i in
                Database.get(
                    'SELECT challenge_completed_day FROM challengeTracker WHERE user_id = ? AND challenge_id = ? ',
                    self.user_id,
                    challenge_id)][0]


class Challenge:
    def __init__(self, challenge_id):
        self.challenge_list = None
        self.max = None
        self.reward = None
        self.peak = None
        self.min = None
        self.days = None
        self.challenge_id = challenge_id
        self.challenge_day = None
        self.cooldown = None

    def get_days(self):
        try:
            self.days = \
                Database.get('SELECT challenge_days FROM challengeProfile WHERE challenge_id = ? ', self.challenge_id)[
                    0][0]
            return self.days

        except IndexError:
            return None

    def get_peak(self):
        try:
            self.peak = \
                Database.get('SELECT challenge_peak FROM challengeProfile WHERE challenge_id = ? ', self.challenge_id)[
                    0][0]
            return self.peak

        except IndexError:
            return None

    def get_reward(self):
        try:
            self.reward = \
                Database.get('SELECT challenge_reward FROM challengeProfile WHERE challenge_id = ? ',
                             self.challenge_id)[0][
                    0]
            return self.reward

        except IndexError:
            return None

    def get_trailmix_range(self) -> ():
        try:
            self.min, self.max = Database.get(
                'SELECT challenge_trailmix_min, challenge_trailmix_max FROM challengeProfile WHERE challenge_id = ? ',
                self.challenge_id)[0]
            return self.min, self.max

        except IndexError:
            return None

    def get_specific_challenge(self, user: int):
        self.challenge_day, self.cooldown = [i for i in Database.get(
            'SELECT challenge_completed_day, challenge_cooldown FROM challengeTracker WHERE user_id = ? AND challenge_id = ?',
            user, self.challenge_id)][0]

    def get_challengers(self) -> []:
        self.challenge_list = [i for i in Database.get('SELECT user_id, challenge_completed_day FROM challengeTracker '
                                                       'WHERE challenge_id = ? ', self.challenge_id)]
        return self.challenge_list


def account_create(member: hikari.Member):
    Database.execute(' REPLACE INTO userProfile (user_id) VALUES (?) ', member.id)
    challenge_list = [i for i in Database.get('SELECT challenge_id FROM challengeProfile ')]
    for id in challenge_list:
        Database.execute(' REPLACE INTO challengeTracker (user_id, challenge_id) VALUES (?, ?) ', member.id, id)
    item_list = [i for i in Database.get(' SELECT * FROM items ')]

    for id, name, price, role in item_list:
        Database.execute(' REPLACE INTO userInventory (user_id, item_name) VALUES (?, ?) ', member.id, name)


def challenge_create(id: int):
    user_list = [i[0] for i in Database.get('SELECT user_id FROM userProfile ')]
    for user in user_list:
        Database.execute('INSERT INTO challengeTracker (user_id, challenge_id) VALUES (?, ?) ', user, id)


@plugin.listener(hikari.StartedEvent)
async def on_ready(event: hikari.StartedEvent) -> None:
    user_list = [i[0] for i in Database.get('SELECT user_id FROM userProfile ')]
    guilds = event.app.rest.fetch_my_guilds()

    async for guild in guilds:
        members = await event.app.rest.fetch_members(guild)
        for member in members:
            if member.id not in user_list:
                account_create(member)


@plugin.listener(hikari.GuildJoinEvent)
async def on_guild_join(event: hikari.GuildJoinEvent) -> None:
    user_list = [i[0] for i in Database.get('SELECT user_id FROM userProfile ')]

    for member in event.guild.get_members():
        if member.id not in user_list:
            account_create(member)


@plugin.listener(hikari.MemberCreateEvent)
async def on_guild_join(event: hikari.MemberCreateEvent) -> None:
    user_list = [i[0] for i in Database.get('SELECT user_id FROM userProfile ')]

    if event.member.id not in user_list:
        account_create(event.member)


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
