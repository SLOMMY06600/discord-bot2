import discord
from discord.ext import commands
import os

# ======================
# INTENTS
# ======================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

# ======================
# CONFIG
# ======================

ADDROLE_PERMISSION_ID = 1493037666768523479
DELROLE_PERMISSION_ID = 1493037710082965585

PROTECTED_ROLES = [
    1493039967365103716
]

LOG_CHANNEL_ID = 1496244094970761356  # ID salon logs

# ======================
# LOG SYSTEM
# ======================

async def send_log(guild, message, mention=None):
    channel = guild.get_channel(1496244094970761356)
    if channel:
        content = f"{mention} | {message}" if mention else message
        await channel.send(content)

# ======================
# ADDROLE
# ======================

@bot.command()
async def addrole(ctx, member: discord.Member, role: discord.Role):

    if not any(r.id == ADDROLE_PERMISSION_ID for r in ctx.author.roles):
        return await ctx.send("pas la permission")

    if role >= ctx.author.top_role:
        return await ctx.send("role trop haut")

    if role >= ctx.guild.me.top_role:
        return await ctx.send("role trop haut pour le bot")

    try:
        await member.add_roles(role)
        await ctx.send("role ajoute")

        await send_log(
            ctx.guild,
            f"➕ rôle ajouté : {role.name} par {ctx.author}",
            member.mention
        )

    except discord.Forbidden:
        await ctx.send("je n'ai pas la permission")

# ======================
# DELROLE
# ======================

@bot.command()
async def delrole(ctx, member: discord.Member, role: discord.Role):

    if not any(r.id == DELROLE_PERMISSION_ID for r in ctx.author.roles):
        return await ctx.send("pas la permission")

    if role.id in PROTECTED_ROLES:
        return await ctx.send("ce role est protege")

    if role >= ctx.author.top_role:
        return await ctx.send("role trop haut")

    try:
        await member.remove_roles(role)
        await ctx.send("role retire")

        await send_log(
            ctx.guild,
            f"➖ rôle retiré : {role.name} par {ctx.author}",
            member.mention
        )

    except discord.Forbidden:
        await ctx.send("je n'ai pas la permission")

# ======================
# DERANK + RAISON
# ======================

@bot.command()
async def derank(ctx, member: discord.Member, *, reason: str = "Aucune raison fournie"):

    if member.top_role >= ctx.author.top_role:
        return await ctx.send("impossible de derank ce membre")

    roles_to_remove = []

    for role in member.roles:

        if role == ctx.guild.default_role:
            continue

        if role.id in PROTECTED_ROLES:
            continue

        if role < ctx.author.top_role:
            roles_to_remove.append(role)

    if not roles_to_remove:
        return await ctx.send("aucun role a retirer")

    try:
        await member.remove_roles(*roles_to_remove)
        await ctx.send(f"{member.mention} a ete derank")

        await send_log(
            ctx.guild,
            f"🚫 derank | roles retirés: {len(roles_to_remove)} | raison: {reason}",
            member.mention
        )

    except discord.Forbidden:
        await ctx.send("je n'ai pas la permission")

# ======================
# ERROR HANDLER
# ======================

@bot.event
async def on_command_error(ctx, error):
    await send_log(
        ctx.guild,
        f"⚠️ erreur commande {ctx.command} par {ctx.author} | {error}"
    )

# ======================
# READY
# ======================

@bot.event
async def on_ready():
    print(f"connecte en tant que {bot.user}")

# ======================
# RUN
# ======================

bot.run(os.getenv("TOKEN"))
