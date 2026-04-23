import discord
from discord.ext import commands
import datetime
import io
import json
import os
import aiohttp
antiban = True
antiunban = True
antikick = True
antirole = True
antirank = True
antisalon = True
antieveryone = True
owners = []
Whitelist = []

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
@commands.has_permissions(administrator=True)
async def antiban(ctx, mode=None):

    global antiban

    if mode == "on":
        antiban = True
        return await ctx.send("Antiban activé")

    if mode == "off":
        antiban = False
        return await ctx.send("Antiban désactivé")

    await ctx.send("Utilise +antiban on/off")


@bot.command()
@commands.has_permissions(administrator=True)
async def antiunban(ctx, mode=None):

    global antiunban

    if mode == "on":
        antiunban = True
        return await ctx.send("Antiunban activé")

    if mode == "off":
        antiunban = False
        return await ctx.send("Antiunban désactivé")

    await ctx.send("Utilise +antiunban on/off")


@bot.command()
@commands.has_permissions(administrator=True)
async def antikick(ctx, mode=None):

    global antikick

    if mode == "on":
        antikick = True
        return await ctx.send("Antikick activé")

    if mode == "off":
        antikick = False
        return await ctx.send("Antikick désactivé")

    await ctx.send("Utilise +antikick on/off")


@bot.command()
@commands.has_permissions(administrator=True)
async def antirole(ctx, mode=None):

    global antirole

    if mode == "on":
        antirole = True
        return await ctx.send("Antirole activé")

    if mode == "off":
        antirole = False
        return await ctx.send("Antirole désactivé")

    await ctx.send("Utilise +antirole on/off")


@bot.command()
@commands.has_permissions(administrator=True)
async def antirank(ctx, mode=None):

    global antirank

    if mode == "on":
        antirank = True
        return await ctx.send("Antirank activé")

    if mode == "off":
        antirank = False
        return await ctx.send("Antirank désactivé")

    await ctx.send("Utilise +antirank on/off")


@bot.command()
@commands.has_permissions(administrator=True)
async def antisalon(ctx, mode=None):

    global antisalon

    if mode == "on":
        antisalon = True
        return await ctx.send("Antisalons activé")

    if mode == "off":
        antisalon = False
        return await ctx.send("Antisalons désactivé")

    await ctx.send("Utilise +antisalon on/off")


@bot.command()
@commands.has_permissions(administrator=True)
async def antieveryone(ctx, mode=None):

    global antieveryone

    if mode == "on":
        antieveryone = True
        return await ctx.send("Antieveryone activé")

    if mode == "off":
        antieveryone = False
        return await ctx.send("Antieveryone désactivé")

    await ctx.send("Utilise +antieveryone on/off")

@bot.command()
async def wl(ctx, member: discord.Member):

    if ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("Seul le owner serveur peut utiliser ça")

    if member.id in WHITELIST:
        return await ctx.send("Déjà whitelist")

    WHITELIST.append(member.id)
    await ctx.send(f"{member.mention} whitelist")


@bot.command()
async def unwl(ctx, member: discord.Member):

    if ctx.author.id != ctx.guild.owner_id:
        return await ctx.send("Seul le owner serveur peut utiliser ça")

    if member.id in WHITELIST:
        WHITELIST.remove(member.id)
        return await ctx.send(f"{member.mention} retiré whitelist")

    await ctx.send("Pas whitelist")


@bot.command()
async def wllist(ctx):

    if not WHITELIST:
        return await ctx.send("Aucun whitelist")

    users = []
    for uid in WHITELIST:
        user = await bot.fetch_user(uid)
        users.append(user.mention)

    await ctx.send("**Whitelist :**\n" + "\n".join(users))

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

class TicketView(discord.ui.View):

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id not in owners and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message(
                "❌ Vous n'avez pas l'autorisation d'utiliser ce menu",
                ephemeral=True
            )
            return False
        return True

# ======================
# ANTI NUKE EVENTS
# ======================

@bot.event
async def on_member_ban(guild, user):

    if not antiban:
        return

    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        executor = entry.user

        if executor.id in WHITELIST or executor.id == guild.owner_id:
            return

        try:
            await guild.unban(user)
            await executor.kick(reason="Antiban")

            for role in executor.roles:
                if role.name != "@everyone":
                    await executor.remove_roles(role)

        except:
            pass


@bot.event
async def on_member_remove(member):

    if not antikick:
        return

    guild = member.guild

    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.kick):
            executor = entry.user

            if entry.target.id == member.id:

                if executor.id in WHITELIST or executor.id == guild.owner_id:
                    return

                await executor.kick(reason="Antikick")

                break
    except:
        pass

@bot.event
async def on_member_unban(guild, user):

    if not antiunban:
        return

    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.unban):
        executor = entry.user

        if executor.id in WHITELIST or executor.id == guild.owner_id:
            return

        try:
            await executor.kick(reason="Antiunban")

        except:
            pass

@bot.event
async def on_guild_channel_delete(channel):

    if not antisalon:
        return

    guild = channel.guild

    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.channel_delete):
            executor = entry.user

            if executor.id in WHITELIST or executor.id == guild.owner_id:
                return

            await executor.kick(reason="Antisalon")

            break
    except:
        pass

@bot.event
async def on_member_update(before, after):

    if not antirole and not antirank:
        return

    removed_roles = set(before.roles) - set(after.roles)

    if not removed_roles:
        return

    guild = after.guild

    try:
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
            executor = entry.user

            if executor.id in WHITELIST or executor.id == guild.owner_id:
                return

            await executor.kick(reason="Antirole / Antirank")

            break
    except:
        pass

@bot.event
async def on_message(message):

    if not antieveryone:
        return

    if "@everyone" in message.content or "@here" in message.content:

        if message.author.id in WHITELIST:
            return

        try:
            await message.delete()
            await message.author.kick(reason="AntiEveryone")
        except:
            pass

    await bot.process_commands(message)

# ======================
# RUN
# ======================

bot.run(os.getenv("DISCORD_TOKEN"))
