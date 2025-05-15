import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from discord.ui import View, Select

# Constants
GUILD_ID = 111111111111111 # Replace with your discord server ID
CATEGORY_ID = 1111111111111111 # Replace with the category ID
SUPPORT_ROLE_ID = 111111111111111  # Replace with the support role ID

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True

bot = commands.Bot(command_prefix=".", intents=intents)

CATEGORY_OPTIONS = [
    discord.SelectOption(label="🔧 X", value="X1"), # Replace X with names of your categories
    discord.SelectOption(label="🛒 X", value="X2"),
    discord.SelectOption(label="❓ X", value="X3"),
]
CATEGORY_LABELS = {
    "X1": "XXX", # Replace the first X with the name of the category [the value], and second replace with name of your category
    "X2": "XXX",
    "X3": "XXX"
}


@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"🔁 {len(synced)} was synchronized")
        bot.add_view(TicketCategoryView()) 
        bot.add_view(TicketControlView())   
    except Exception as e:
        print(e)


class TicketCategorySelect(Select):
    def __init__(self):
        super().__init__(
            placeholder="Chose the category of your ticket",
            min_values=1,
            max_values=1,
            options=CATEGORY_OPTIONS,
            custom_id="select_ticket_category"
        )

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        category_label = CATEGORY_LABELS.get(selected, "Category not found")

        modal = discord.ui.Modal(title=f"Create ticket – {category_label}", custom_id=f"ticket_modal:{selected}")
        modal.add_item(discord.ui.TextInput(
            label="Why are you making a ticket",
            placeholder="Enter a reason:",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=1000,
            custom_id="ticket_reason"
        ))

        await interaction.response.send_modal(modal)


class TicketCategoryView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())

class TicketControlView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.claimed = False

    @discord.ui.button(label="✅ Claim Ticket", style=discord.ButtonStyle.success, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        support_role = interaction.guild.get_role(SUPPORT_ROLE_ID) 
        if support_role not in interaction.user.roles:
            await interaction.response.send_message(
                "❌ This ticket can be claimed only by a person who has the support role",
                ephemeral=True
            )
            return

        if self.claimed:
            await interaction.response.send_message("This ticket is already claimed", ephemeral=True)
            return

        self.claimed = True
        button.label = f"Claimed by: {interaction.user.display_name}"
        button.disabled = True

        try:
            await interaction.channel.edit(name=f"ticket-{interaction.user.name}")
        except discord.Forbidden:
            pass

        messages = [msg async for msg in interaction.channel.history(limit=10)]
        for msg in messages:
            if msg.author == interaction.client.user and msg.embeds:
                embed = msg.embeds[0]
                updated_embed = embed.copy()
                updated_embed.set_footer(text=f"Support - Claimed by {interaction.user.display_name}")
                updated_embed.timestamp = discord.utils.utcnow()
                await msg.edit(embed=updated_embed, view=self)
                break

        await interaction.response.defer()

    @discord.ui.button(label="🔒 Close ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if not channel.name.startswith("ticket-"):
            await interaction.response.send_message("❌ This channel isnt a ticket, and can't be closed", ephemeral=True)
            return

        await interaction.response.send_message("🛑 Closing in 5...", ephemeral=True)
        await asyncio.sleep(5)
        await channel.delete(reason="Ticket closed")


@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.modal_submit:
        return

    custom_id = interaction.data.get("custom_id", "")
    if not custom_id.startswith("ticket_modal:"):
        return

    category_key = custom_id.split(":")[1]
    category_label = CATEGORY_LABELS.get(category_key, "Neznámá kategorie")
    reason = interaction.data["components"][0]["components"][0]["value"]

    try:
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )
        }

        ticket_channel = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites,
            category=interaction.guild.get_channel(CATEGORY_ID),
            reason="New support ticket"
        )

        embed = discord.Embed(
            title=f"🎫 Ticket – {category_label}",
            description=f"**User:** {interaction.user.mention}\n**Category:** {category_label}\n**Reason:** {reason}",
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Support")
        embed.timestamp = discord.utils.utcnow()

        await ticket_channel.send(embed=embed, view=TicketControlView())

        await interaction.response.send_message(
            f"✅ Your ticket was created: {ticket_channel.mention}",
            ephemeral=True
        )

    except Exception as e:
        print(f"❌ Error while making the ticket: {e}")
        await interaction.response.send_message(
            "❌ Something went wrong.",
            ephemeral=True
        )


@bot.tree.command(name="sendticket", description="Send's the ticket message into a specified channel", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(channel="Channel, where you want to send te message")
async def send_ticket_button(interaction: discord.Interaction, channel: discord.TextChannel):
    embed = discord.Embed(
        title="🎫 Need help?",
        description="Choose the category, for what you need",
        color=discord.Color.blurple()
    )
    embed.set_footer(text="Support")
    embed.timestamp = discord.utils.utcnow()

    await channel.send(embed=embed, view=TicketCategoryView())
    await interaction.response.send_message(f"✅ Panel of ticket sent to: {channel.mention}", ephemeral=True)

bot.run('Bot token')
