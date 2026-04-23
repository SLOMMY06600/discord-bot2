import discord
from discord.ext import commands
import datetime
import io
import json
import os
import aiohttp
owners = []

OWNERS_FILE = "owners.json"

def load_owners():
    if os.path.exists(OWNERS_FILE):
        with open(OWNERS_FILE, "r") as f:
            return json.load(f)
    return []

def save_owners():
    with open(OWNERS_FILE, "w") as f:
        json.dump(owners, f)

owners = load_owners()

# ======================
# INTENTS
# ======================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="+", intents=intents, help_command=None)

# ======================
# CONFIG
# ======================

ticket_options = [
    {"name": "🛠 Support", "category_id": None},
    {"name": "🐞 Bug", "category_id": None},
    {"name": "❓ Autre", "category_id": None}
]

LOG_CHANNEL_ID = 1496568287415505069

# ======================
# READY
# ======================

@bot.event
async def on_ready():
    print(f"Connecté : {bot.user}")

# ======================
# TRANSCRIPT
# ======================

async def create_transcript(channel):
    messages = []

    async for msg in channel.history(oldest_first=True):
        time = msg.created_at.strftime("%Y-%m-%d %H:%M")
        messages.append(f"[{time}] {msg.author}: {msg.content}")

    return discord.File(
        fp=io.BytesIO("\n".join(messages).encode()),
        filename=f"transcript-{channel.name}.txt"
    )

# ======================
# TICKET CONTROLS
# ======================

class TicketControls(discord.ui.View):

    @discord.ui.button(label="📌 Claim", style=discord.ButtonStyle.primary)
    async def claim(self, interaction, button):

        await interaction.response.send_message(
            f"📌 Ticket pris par {interaction.user.mention}"
        )

    @discord.ui.button(label="🔒 Fermer", style=discord.ButtonStyle.danger)
    async def close(self, interaction, button):

        await interaction.response.send_message("🔒 Fermeture...", ephemeral=True)

        file = await create_transcript(interaction.channel)

        log = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log:
            await log.send(file=file)

        await interaction.channel.delete()

# ======================
# CREATE TICKET
# ======================

async def create_ticket(interaction, index):

    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    user = interaction.user
    data = ticket_options[index]

    category = None
    if data["category_id"]:
        category = discord.utils.get(guild.categories, id=data["category_id"])

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True),
        guild.me: discord.PermissionOverwrite(view_channel=True),
    }

    channel = await guild.create_text_channel(
        name=f"ticket-{user.name}".lower(),
        category=category,
        overwrites=overwrites
    )

    embed = discord.Embed(
        title="🎫 Ticket ouvert",
        description=(
            f"Ticket ouvert par {user.mention}\n\n"
            "Merci d'avoir contacté le support\n"
            "Décrivez votre problème puis attendez une réponse"
        ),
        color=discord.Color.green()
    )

    await channel.send(embed=embed, view=TicketControls())

    await interaction.followup.send(f"✅ Ticket créé : {channel.mention}", ephemeral=True)

# ======================
# MENU TICKETS
# ======================

class TicketMenu(discord.ui.Select):

    def __init__(self):

        options = [
            discord.SelectOption(label=t["name"], value=str(i))
            for i, t in enumerate(ticket_options)
        ]

        super().__init__(placeholder="Ouvrir un ticket...", options=options)

    async def callback(self, interaction):
        await create_ticket(interaction, int(self.values[0]))

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(TicketMenu())

# ======================
# PANEL
# ======================

@bot.command()
async def ticket(ctx):

    embed = discord.Embed(
        title="🎫 Tickets.                       ",
        description="Ouvre un ticket avec le menu",
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed, view=TicketView())

# ======================
# CONFIG
# ======================

class ConfigView(discord.ui.View):

    @discord.ui.button(label="Ajouter", style=discord.ButtonStyle.success)
    async def add(self, interaction, button):

        await interaction.response.send_message("Nom :", ephemeral=True)

        def check(m):
            return m.author.id == interaction.user.id

        msg = await bot.wait_for("message", check=check)

        ticket_options.append({"name": msg.content, "category_id": None})

        await interaction.followup.send("Ajouté", ephemeral=True)

    @discord.ui.button(label="Supprimer", style=discord.ButtonStyle.danger)
    async def delete(self, interaction, button):

        await interaction.response.send_message(
            "\n".join([f"{i} → {t['name']}" for i, t in enumerate(ticket_options)]),
            ephemeral=True
        )

        def check(m):
            return m.author.id == interaction.user.id

        msg = await bot.wait_for("message", check=check)

        try:
            ticket_options.pop(int(msg.content))
            await interaction.followup.send("supprimé", ephemeral=True)
        except:
            await interaction.followup.send("erreur", ephemeral=True)

    @discord.ui.button(label="Assigner", style=discord.ButtonStyle.secondary)
    async def assign(self, interaction, button):

        text = "\n".join([f"{i} → {t['name']}" for i, t in enumerate(ticket_options)])

        await interaction.response.send_message(
            f"{text}\nFormat: index | id_categorie",
            ephemeral=True
        )

        def check(m):
            return m.author.id == interaction.user.id

        msg = await bot.wait_for("message", check=check)

        try:
            idx, cat = msg.content.split("|")

            ticket_options[int(idx)]["category_id"] = int(cat)

            await interaction.followup.send("assigné", ephemeral=True)
        except:
            await interaction.followup.send("erreur", ephemeral=True)

@bot.command()
@commands.has_permissions(administrator=True)
async def config(ctx):
    await ctx.send("Cnfiguration Ticket", view=ConfigView())

# ======================
# MODERATION (inchangé)
# ======================

@bot.command()
async def kick(ctx, member: discord.Member):

    try:
        await member.kick()
        await ctx.send(f"{member.mention} a bien été kick du serveur")

    except discord.Forbidden:
        await ctx.send("Le bot n'a pas les permissions pour kick ce membre")

@bot.command()
async def ban(ctx, member: discord.Member):

    try:
        await member.ban()
        await ctx.send(f"{member.mention} a bien été ban du serveur")

    except discord.Forbidden:
        await ctx.send("Le bot n'a pas les permissions pour ban ce membre")

@bot.command()
async def unban(ctx, user_id: int):

    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(f"{user.mention} a été unban du serveur")

    except discord.NotFound:
        await ctx.send("Utilisateur introuvable")
    except discord.Forbidden:
        await ctx.send("Le bot n'a pas les permissions pour unban")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):

    if amount <= 0:
        return await ctx.send("Tu dois mettre un nombre supérieur à 0")

    deleted = await ctx.channel.purge(limit=amount + 1)

    await ctx.send(f"{len(deleted)-1} messages supprimés", delete_after=5)

@bot.command()
@commands.has_permissions(manage_roles=True)
async def addrole(ctx, member: discord.Member, role: discord.Role):

    try:
        await member.add_roles(role)
        await ctx.send(f"{member.mention} a reçu le rôle **{role.name}**")
    except:
        await ctx.send("Impossible d'ajouter ce rôle")


@bot.command()
@commands.has_permissions(manage_roles=True)
async def delrole(ctx, member: discord.Member, role: discord.Role):

    try:
        await member.remove_roles(role)
        await ctx.send(f"Le rôle **{role.name}** a été retiré à {member.mention}")
    except:
        await ctx.send("Impossible de retirer ce rôle")

@bot.command()
@commands.has_permissions(manage_channels=True)
async def lock(ctx):

    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

    await ctx.send("Ce salon est désormais verrouillé")


@bot.command()
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):

    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = True
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)

    await ctx.send("Ce salon est de nouveau ouvert")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, minutes: int):

    try:
        duration = discord.utils.utcnow() + datetime.timedelta(minutes=minutes)
        await member.timeout(duration)

        await ctx.send(f"{member.mention} est mute pendant {minutes} minutes")

    except discord.Forbidden:
        await ctx.send("Le bot n'a pas les permissions pour mute cette personne")


@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):

    try:
        await member.timeout(None)

        await ctx.send(f"{member.mention} a été unmute")

    except discord.Forbidden:
        await ctx.send("Le bot n'a pas les permissions pour unmute cette personne")

@bot.command()
async def owner(ctx, member: discord.Member):

    if ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("Seul le owner du serveur peut faire ça")

    if member.id in owners:
        return await ctx.send(f"{member.mention} est déjà owner bot")

    owners.append(member.id)
    save_owners()

    await ctx.send(f"{member.mention} est maintenant owner bot")

@bot.check
async def global_owner_check(ctx):
    return ctx.author.id in owners or ctx.author.id == ctx.guild.owner_id

@bot.command()
async def unowner(ctx, member: discord.Member):

    if ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("Seul le owner du serveur peut faire ça")

    if member.id not in owners:
        return await ctx.send(f"{member.mention} n'est pas owner bot")

    owners.remove(member.id)
    save_owners()

    await ctx.send(f"{member.mention} n'est plus owner bot")

@bot.command()
async def ownerlist(ctx):

    if not owners:
        return await ctx.send("Aucun owner")

    mentions = []
    for user_id in owners:
        user = await bot.fetch_user(user_id)
        mentions.append(user.mention)

    await ctx.send("**Owners bot :**\n" + "\n".join(mentions))

@bot.command()
@commands.has_permissions(administrator=True)
async def botname(ctx, *, name=None):

    if name is None:
        return await ctx.send(f"{ctx.author.mention} tu dois donner un nom")

    try:
        await bot.user.edit(username=name)
        await ctx.send(f"Nom du bot changé en **{name}**")

    except discord.HTTPException:
        await ctx.send("Impossible de changer le nom (limite Discord)")

import aiohttp

@bot.command()
@commands.has_permissions(administrator=True)
async def botpic(ctx, url=None):

    if url is None:
        return await ctx.send(f"{ctx.author.mention} tu dois mettre un lien d'image")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:

                if resp.status != 200:
                    return await ctx.send("Image invalide")

                data = await resp.read()
                await bot.user.edit(avatar=data)

        await ctx.send("Avatar du bot changé")

    except:
        await ctx.send("Erreur lors du changement d'avatar")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message: str = None):

    if not message:
        return await ctx.send("❌ Tu dois écrire un message")

    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

    await ctx.send(message)

@bot.command()
async def avatar(ctx, member: discord.Member = None):

    member = member or ctx.author

    try:
        url = member.display_avatar.url
    except:
        return await ctx.send("❌ Impossible de récupérer l'avatar")

    embed = discord.Embed(
        title=f"Avatar de {member}",
        color=discord.Color.blurple()
    )
    embed.set_image(url=url)

    await ctx.send(embed=embed)
    
# ======================
# NEW COMMANDS
# ======================

class HelpSelect(discord.ui.Select):
    def __init__(self):

        options = [
            discord.SelectOption(label="Tickets"),
            discord.SelectOption(label="Utilitaires"),
            discord.SelectOption(label="Moderation"),
            discord.SelectOption(label="Owner")
        ]

        super().__init__(
            placeholder="Choisis Une Catégorie",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        embed = discord.Embed(color=discord.Color.dark_blue())

        choice = self.values[0]

        if choice == "Tickets":
            embed.title = "Tickets"
            embed.description = (
                "**+Ticket**\nOuvre Le Menu Des Tickets\n\n"
                "**+Config**\nConfigure Les Tickets\n\n"
                "**+Adduser**\nAjoute Un Utilisateur Au Ticket\n\n"
                "**+Deluser**\nRetire Un Utilisateur Du Ticket\n\n"
                "**+Rename**\nRenomme Le Salon Du Ticket"
            )

        elif choice == "Utilitaires":
            embed.title = "Utilitaires"
            embed.description = (
                "**+Avatar**\nAffiche L’Avatar D’Un Utilisateur\n\n"
                "**+Userinfo**\nInformations Utilisateur\n\n"
                "**+Serverinfo**\nInformations Serveur\n\n"
                "**+Say**\nFait Parler Le Bot"
            )

        elif choice == "Moderation":
            embed.title = "Moderation"
            embed.description = (
                "**+Kick**\nExpulse Un Membre\n\n"
                "**+Ban**\nBannit Un Membre\n\n"
                "**+Unban**\nDébannit Un Utilisateur\n\n"
                "**+Clear**\nSupprime Des Messages\n\n"
                "**+Addrole**\nAjoute Un Rôle\n\n"
                "**+Delrole**\nRetire Un Rôle\n\n"
                "**+Lock**\nVerrouille Un Salon\n\n"
                "**+Unlock**\nDéverrouille Un Salon\n\n"
                "**+Mute**\nRend Muet Un Membre\n\n"
                "**+Unmute**\nRetire Le Mute"
            )

        elif choice == "Owner":
            embed.title = "Owner"
            embed.description = (
                "**+Owner**\nAjoute Un Owner Bot\n\n"
                "**+Unowner**\nRetire Un Owner Bot\n\n"
                "**+Ownerlist**\nListe Des Owners\n\n"
                "**+Botname**\nChange Le Nom Du Bot\n\n"
                "**+Botpic**\nChange L’Avatar Du Bot"
            )

        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(HelpSelect())

@bot.command()
async def help(ctx):

    embed = discord.Embed(
        title="Help Menu",
        description="Choisis Une Catégorie Dans Le Menu",
        color=discord.Color.dark_blue()
    )

    await ctx.send(embed=embed, view=HelpView())

# ======================
# RUN
# ======================

@bot.command()
async def serverinfo(ctx):

    guild = ctx.guild

    if guild is None:
        return await ctx.send("❌ Utilisable uniquement dans un serveur")

    embed = discord.Embed(
        title=f"📊 {guild.name}",
        color=discord.Color.blue()
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    embed.add_field(name="🆔 ID", value=str(guild.id), inline=True)
    embed.add_field(name="👑 Owner", value=guild.owner.mention if guild.owner else "Inconnu", inline=True)
    embed.add_field(name="👥 Membres", value=str(guild.member_count), inline=True)

    embed.add_field(name="💬 Salons texte", value=str(len(guild.text_channels)), inline=True)
    embed.add_field(name="🔊 Salons vocaux", value=str(len(guild.voice_channels)), inline=True)
    embed.add_field(name="📁 Catégories", value=str(len(guild.categories)), inline=True)

    embed.add_field(name="📅 Créé le", value=guild.created_at.strftime("%d/%m/%Y"), inline=False)

    embed.set_footer(text=f"Demandé par {ctx.author}")

    await ctx.send(embed=embed)

@bot.command()
async def userinfo(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = discord.Embed(
        title=f"👤 Userinfo - {member}",
        color=discord.Color.blurple()
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    embed.add_field(name="🆔 ID", value=str(member.id), inline=True)
    embed.add_field(name="📅 Compte créé", value=member.created_at.strftime("%d/%m/%Y"), inline=True)

    if member.joined_at:
        embed.add_field(name="📥 Rejoint le serveur", value=member.joined_at.strftime("%d/%m/%Y"), inline=True)
    else:
        embed.add_field(name="📥 Rejoint le serveur", value="Inconnu", inline=True)

    embed.add_field(name="🤖 Bot", value="Oui" if member.bot else "Non", inline=True)
    embed.add_field(name="🔝 Rôle principal", value=member.top_role.mention, inline=True)

    roles = [role.mention for role in member.roles if role != ctx.guild.default_role]
    embed.add_field(
        name=f"🎭 Rôles ({len(roles)})",
        value=", ".join(roles) if roles else "Aucun rôle",
        inline=False
    )

    embed.set_footer(text=f"Demandé par {ctx.author}")

    await ctx.send(embed=embed)

bot.run(os.getenv("DISCORD_TOKEN"))
