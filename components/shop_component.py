import dataclasses
import asyncio
import lightbulb
import miru
import hikari
import sqlite3
import math
import random
from Database import Database
from components.challenge_handler import User
from dataclasses import dataclass

conn = sqlite3.connect('bot.db', timeout=5.0)
c = conn.cursor()

plugin = lightbulb.Plugin("Shop")

c.execute(
    '''CREATE TABLE IF NOT EXISTS shopSettings (
    identifier INT PRIMARY KEY DEFAULT "1", 
    name TEXT DEFAULT "Shop", 
    description TEXT DEFAULT "Welcome to the shop!", 
    thankyoumessage TEXT DEFAULT "Thank you!"
    ) ''')

c.execute(
    '''CREATE TABLE IF NOT EXISTS userInventory (
     user_id INT, 
     item_name TEXT,
     quantity INT DEFAULT 0,
     UNIQUE(user_id, item_name)
      ) ''')

c.execute(
    '''CREATE TABLE IF NOT EXISTS items (
     item_id INT PRIMARY KEY,
     item_name TEXT,
     price INT,
     role INT
      ) ''')


def get_all_shop_items():
    item_list = [i for i in Database.get(' SELECT * FROM items ')]
    return item_list


def create_default_item():
    try:
        Database.execute('INSERT INTO items VALUES (?, ?, ?, ?) ', 1, 'Trail Access', 50, 950508081626898483)

    except sqlite3.IntegrityError:
        print(f"Item ({'Trail Access'}) has already been added before.")


def create_shop():
    try:
        Database.execute('INSERT INTO shopSettings (identifier) VALUES (?) ', 1)

    except sqlite3.IntegrityError:
        print(f"Shop has already been added before.")


create_default_item()
create_shop()


@dataclass
class Shop:
    title: str = None
    description: str = None
    thank_you: str = None

    def get_shop_info(self):
        id, self.title, self.description, self.thank_you = \
        [i for i in Database.get('SELECT * FROM shopSettings WHERE identifier = ? ', 1)][0]
        return self.title, self.description, self.thank_you


@dataclass
class Item:
    item_id: int = None
    item_name: str = None
    price: int = None
    role: int = None

    def get_item_name(self, id: int):
        self.item_id = id
        self.item_name, self.price = \
            [i for i in Database.get(' SELECT item_name, price, role FROM items WHERE item_id = ? ', self.item_id)][0]
        return self.item_name

    def get_item_id(self, name: str):
        self.item_name = name
        self.item_id, self.price, self.role = \
            [i for i in Database.get(' SELECT item_id, price, role FROM items WHERE item_name = ? ', self.item_name)][0]
        return self.item_id

    def get_role_id(self, id: int):
        self.item_id = id
        self.item_id, self.price, self.role = \
            [i for i in Database.get(' SELECT item_id, price, role FROM items WHERE item_id = ? ', self.item_id)][0]
        return self.role

    def item_transaction(self, user: int, amount: int):
        user_object = User(user)
        qty = user_object.user_item_quantity(self.item_name)
        qty += amount
        Database.execute('UPDATE userInventory SET quantity = ? WHERE user_id = ? AND item_name = ? ', qty, user,
                         self.item_name)
        return qty


class ShopChoice(miru.Select):
    def __init__(self, shop_object, placeholder, choices):
        options = []
        self.shop = shop_object
        self.thank_you = self.shop['thank_you']
        for item_id, item_name, item_price, role_id in choices:
            options.append(miru.SelectOption(label=item_name))
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)

    async def callback(self, ctx: miru.Context):
        labels = [i.label for i in self.options]
        idx = labels.index(self.values[0])
        name = str(self.options[idx].label)
        user_object = User(ctx.interaction.user.id)
        item_object = Item()
        item_object.get_item_id(name)
        role_id = item_object.get_role_id(item_object.item_id)
        role_object = ctx.get_guild().get_role(role_id)

        if role_object:
            await ctx.interaction.member.add_role(role_object)

        check = user_object.shop_transaction(-item_object.price)

        if not check:
            return await ctx.respond("❌ Purchase is unsuccessful.\n\n"
                                     "You do not have sufficient balance to make this purchase.\n\n"
                                     f"**Your Balance:** {user_object.trailmix} Trailmix{'s' if user_object.trailmix > 1 else ''}",
                                     flags=hikari.MessageFlag.EPHEMERAL)

        item_object.item_transaction(ctx.interaction.user.id, 1)
        await ctx.respond(f"☑ Purchase is successful.\n\n"
                          f"{self.thank_you}\n\n"
                          f"**Balance:** {user_object.trailmix:,} Trailmix{'s' if user_object.trailmix > 1 else ''}\n"
                          f"{f'You have earned a new role: {role_object.mention}' if role_object else ''}",
                          flags=hikari.MessageFlag.EPHEMERAL)


class ShopMenu(miru.View):
    def __init__(self, n, data, shop_object, item):
        super().__init__(timeout=60)
        self.current_page = None
        self.value = 1
        self.n = n
        self.data = data
        self.shop = shop_object
        self.title = self.shop['title']
        self.description = self.shop['description']
        self.pages = math.ceil(len(self.data) / n)
        self.item = item
        self.previous = item
        self.add_item(self.item)

    async def view_check(self, ctx: miru.Context) -> bool:
        return ctx.interaction.user == ctx.user

    async def on_timeout(self) -> None:
        i = 0
        embed = hikari.Embed(description="Shop has timed out. Please restart the command.")
        await self.message.edit(embed=embed, components=[])

    @miru.button(label="Previous", style=hikari.ButtonStyle.PRIMARY, emoji="◀", disabled=True)
    async def previous_button(self, button: miru.Button, ctx: miru.Context) -> None:

        self.value -= 1
        self.current_page = [item for item in self.data[self.n * (self.value - 1):self.value * self.n]]

        colour = random.randint(0x0, 0xFFFFFF)
        embed = hikari.Embed(title=self.title, description=self.description, colour=hikari.Colour(colour))

        guild_object = ctx.get_guild()
        for item_id, item_name, item_price, item_role in self.current_page:
            role_object = guild_object.get_role(item_role).mention if guild_object.get_role(item_role).id in guild_object.get_roles() else "None"
            embed.add_field(name=f'• {item_name}', value=f'> Item ID: {item_id}\n'
                                                         f'> Price: {item_price:,} Trailmix{"s" if item_price > 1 else ""}'
                                                         f'> Role Reward: {role_object}')
        embed.set_thumbnail(guild_object.icon_url)
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

        self.current_page = [item for item in self.data[self.n * (self.value - 1):self.value * self.n]]

        colour = random.randint(0x0, 0xFFFFFF)
        embed = hikari.Embed(title=self.title, description=self.description, colour=hikari.Colour(colour))
        guild_object = ctx.get_guild()
        for item_id, item_name, item_price, item_role in self.current_page:
            role_object = guild_object.get_role(item_role).mention if guild_object.get_role(item_role).id in guild_object.get_roles() else "None"
            embed.add_field(name=f'• {item_name}', value=f'> Item ID: {item_id}\n'
                                                         f'> Price: {item_price:,} Trailmix{"s" if item_price > 1 else ""}'
                                                         f'> Role Reward: {role_object}')
        embed.set_thumbnail(guild_object.icon_url)
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

    @miru.button(label="Exit", style=hikari.ButtonStyle.DANGER, emoji="❎")
    async def cancel(self, button: miru.Button, ctx: miru.Context):
        embed = hikari.Embed(description="Successfully exited the shop.")
        await self.message.edit(embed=embed, components=[])
        await asyncio.sleep(5)
        await self.message.edit()


@plugin.command()
@lightbulb.command("shop", "Displays the shop interface.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def shop(ctx: lightbulb.Context) -> None:
    item_list = get_all_shop_items()
    n = 5
    i = 1
    every_page = [item for item in item_list[n * (i - 1):i * n]]
    shop_object = Shop()
    shop_object.get_shop_info()

    colour = random.randint(0x0, 0xFFFFFF)
    embed = hikari.Embed(title=shop_object.title, description=shop_object.description, colour=hikari.Colour(colour))
    guild_object = ctx.get_guild()
    if item_list:
        for item_id, item_name, item_price, item_role in every_page:
            role_object = guild_object.get_role(item_role).mention if guild_object.get_role(item_role).id in guild_object.get_roles() else "None"
            embed.add_field(name=f'• {item_name}', value=f'> Item ID: {item_id}\n'
                                                         f'> Price: {item_price:,} Trailmix{"s" if item_price > 1 else ""}\n'
                                                         f'> Role Reward: {role_object}')
    embed.set_thumbnail(guild_object.icon_url)
    pages = math.ceil(len(item_list) / n)
    embed.set_footer(text=f"Page 1 of {pages if pages else 1}")

    if pages:
        view = ShopMenu(n, item_list, dataclasses.asdict(shop_object),
                        ShopChoice(dataclasses.asdict(shop_object), 'Select an item to buy', [item for item in every_page]))
        proxy = await ctx.respond(embed=embed, components=view.build())
        message = await proxy.message()
        view.start(message)

    else:
        await ctx.respond(embed=embed)


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
