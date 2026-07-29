"""
Bot de configuração e onboarding do servidor de Discord da comunidade.

O que ele faz:
  1. Ao iniciar (ou via comando /sync), aplica config.yaml no servidor:
     cria/atualiza cargos, categorias e canais (texto e áudio), na ordem e
     com as visibilidades descritas no config. Nunca deleta nada que não
     esteja no config -- é seguro reexecutar a qualquer momento.
  2. Publica/atualiza a mensagem de regras no canal #regras, com um botão
     "Li e concordo" que libera o cargo Participantes.
  3. Quando alguém entra no servidor, manda uma DM perguntando nick e
     classe, ajusta o apelido, e direciona a pessoa para o canal de regras.

Rode com: python bot.py
Configuração: variáveis de ambiente em .env (veja .env.example) + config.yaml
"""

import asyncio
import logging
import os

import discord
import yaml
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("discord-setup")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

VISIBILITY_ROLE = {
    "participantes": "Participantes",
    "membros": "Membros",
    "moderacao": "Moderação",
    "lideranca": "Liderança",
}

CHANNEL_TYPE_CLASS = {
    "texto": discord.TextChannel,
    "audio": discord.VoiceChannel,
    "forum": discord.ForumChannel,
}


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def hex_to_color(hex_str: str) -> discord.Color:
    return discord.Color(int(hex_str.lstrip("#"), 16))


intents = discord.Intents.default()
intents.members = True          # necessário para on_member_join
intents.message_content = True  # necessário para ler a resposta da DM


class SetupBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.config = load_config()
        self.guild_id = int(os.getenv("DISCORD_GUILD_ID") or self.config["server"]["guild_id"])
        # nick, classe pendentes de quem já respondeu a DM (evita corrida)
        self._onboarding_locks: dict[int, asyncio.Lock] = {}

    async def setup_hook(self):
        guild_obj = discord.Object(id=self.guild_id)
        self.tree.copy_global_to(guild=guild_obj)
        await self.tree.sync(guild=guild_obj)

    # ------------------------------------------------------------------
    # Sincronização de cargos / categorias / canais a partir do config.yaml
    # ------------------------------------------------------------------
    async def get_or_create_role(self, guild: discord.Guild, role_cfg: dict) -> discord.Role:
        role = discord.utils.get(guild.roles, name=role_cfg["name"])
        perms = discord.Permissions(**{p: True for p in role_cfg.get("permissions", [])})
        color = hex_to_color(role_cfg["color"])
        try:
            if role is None:
                role = await guild.create_role(
                    name=role_cfg["name"],
                    color=color,
                    hoist=role_cfg.get("hoist", False),
                    mentionable=role_cfg.get("mentionable", False),
                    permissions=perms,
                    reason="discord-setup: sync config.yaml",
                )
                log.info("Cargo criado: %s", role.name)
            else:
                await role.edit(
                    color=color,
                    hoist=role_cfg.get("hoist", False),
                    mentionable=role_cfg.get("mentionable", False),
                    permissions=perms,
                    reason="discord-setup: sync config.yaml",
                )
        except discord.Forbidden:
            log.warning(
                "Sem permissão pra gerenciar o cargo '%s' -- ele está acima do cargo do bot "
                "na hierarquia. Peça pro dono do servidor arrastar o cargo do bot acima dele. "
                "Seguindo sem atualizar esse cargo por enquanto.",
                role_cfg["name"],
            )
            if role is None:
                # Não dá pra criar nem editar -- sem essa role, overwrites de canal vão falhar.
                raise
        return role

    def overwrites_for(self, guild: discord.Guild, roles_by_name: dict, visibility: str,
                        deny_send_everyone: bool = False) -> dict:
        everyone = guild.default_role
        if visibility == "publico":
            ow = {}
            if deny_send_everyone:
                ow[everyone] = discord.PermissionOverwrite(send_messages=False)
            return ow
        ow = {everyone: discord.PermissionOverwrite(view_channel=False)}
        target_role_name = VISIBILITY_ROLE[visibility]
        ow[roles_by_name[target_role_name]] = discord.PermissionOverwrite(view_channel=True)
        # Se a visibilidade não é "participantes", nega explicitamente o
        # cargo Participantes pra não vazar acesso via ordem de cargos.
        if visibility != "participantes" and "Participantes" in roles_by_name:
            ow[roles_by_name["Participantes"]] = discord.PermissionOverwrite(view_channel=False)
        return ow

    async def get_or_create_category(self, guild: discord.Guild, name: str, position: int,
                                      overwrites: dict) -> discord.CategoryChannel:
        category = discord.utils.get(guild.categories, name=name)
        try:
            if category is None:
                category = await guild.create_category(name, overwrites=overwrites, position=position)
                log.info("Categoria criada: %s", name)
            else:
                await category.edit(overwrites=overwrites, position=position)
        except discord.Forbidden:
            log.warning("Sem permissão pra gerenciar a categoria '%s' -- pulando.", name)
            if category is None:
                raise
        return category

    async def ensure_text_intro(self, channel: discord.TextChannel, resumo: str):
        # Cria a mensagem de resumo SÓ na primeira vez (com o texto do
        # config.yaml como rascunho inicial). Depois disso o sync nunca mais
        # sobrescreve -- a edição passa a ser feita com o comando /resumo
        # direto no Discord, por quem tiver permissão de Moderação+.
        marker = "discord-setup:intro"
        async for msg in channel.history(limit=20, oldest_first=True):
            if msg.author.id == self.user.id and msg.embeds and msg.embeds[0].footer.text == marker:
                return
        embed = discord.Embed(description=resumo, color=discord.Color.blurple())
        embed.set_footer(text=marker)
        try:
            sent = await channel.send(embed=embed)
            await sent.pin(reason="discord-setup: resumo do canal")
        except discord.Forbidden:
            log.warning("Sem permissão pra postar/fixar o resumo em #%s.", channel.name)

    async def get_or_create_channel(self, guild: discord.Guild, category: discord.CategoryChannel,
                                     chan_cfg: dict, position: int, overwrites: dict):
        name = chan_cfg["name"]
        chan_type = chan_cfg["type"]
        resumo = chan_cfg.get("resumo")
        is_voice = chan_type == "audio"
        slug = name if is_voice else name.lower().replace(" ", "-")
        existing = discord.utils.get(category.channels, name=slug)
        existing = existing or discord.utils.get(guild.channels, name=slug)

        if existing is not None and not isinstance(existing, CHANNEL_TYPE_CLASS[chan_type]):
            log.warning(
                "Canal '%s' já existe como %s, mas o config.yaml pede tipo '%s'. O Discord "
                "não permite converter o tipo por API -- apague o canal antigo manualmente "
                "no Discord e rode /sync de novo pra ele nascer com o tipo certo. Pulando por "
                "enquanto.",
                name, type(existing).__name__, chan_type,
            )
            return None

        try:
            if chan_type == "audio":
                if existing is None:
                    existing = await guild.create_voice_channel(
                        name, category=category, overwrites=overwrites, position=position
                    )
                    log.info("Canal de voz criado: %s", name)
                else:
                    await existing.edit(category=category, overwrites=overwrites, position=position)
            elif chan_type == "forum":
                if existing is None:
                    existing = await guild.create_forum(
                        name, category=category, overwrites=overwrites, position=position,
                        topic=resumo,
                    )
                    log.info("Canal forum criado: %s", name)
                else:
                    await existing.edit(category=category, overwrites=overwrites, position=position,
                                         topic=resumo)
            else:
                if existing is None:
                    existing = await guild.create_text_channel(
                        name, category=category, overwrites=overwrites, position=position
                    )
                    log.info("Canal de texto criado: %s", name)
                else:
                    await existing.edit(category=category, overwrites=overwrites, position=position)
        except discord.Forbidden:
            log.warning("Sem permissão pra gerenciar o canal '%s' -- pulando.", name)
            return existing

        if resumo and chan_type == "texto":
            await self.ensure_text_intro(existing, resumo)
        return existing

    async def sync_structure(self, guild: discord.Guild):
        log.info("Sincronizando estrutura do servidor '%s'...", guild.name)

        # 1) Cargos (ordem: Participantes -> ... -> Liderança)
        roles_by_name = {}
        for role_cfg in sorted(self.config["roles"], key=lambda r: r["position"]):
            roles_by_name[role_cfg["name"]] = await self.get_or_create_role(guild, role_cfg)

        # posiciona os cargos gerenciados logo abaixo do cargo mais alto do
        # bot (o bot só pode reordenar cargos abaixo do seu próprio cargo)
        try:
            ordered = sorted(self.config["roles"], key=lambda r: r["position"])
            positions = {roles_by_name[r["name"]]: i + 1 for i, r in enumerate(ordered)}
            await guild.edit_role_positions(positions=positions)
        except discord.Forbidden:
            log.warning(
                "Sem permissão pra reordenar cargos -- arraste o cargo do bot "
                "acima de 'Liderança' em Configurações do Servidor > Cargos."
            )

        # 2) Categorias e canais
        for cat_cfg in sorted(self.config["categories"], key=lambda c: c["order"]):
            deny_send = any(ch.get("somente_leitura") for ch in cat_cfg["channels"])
            cat_overwrites = self.overwrites_for(guild, roles_by_name, cat_cfg["visibility"])
            category = await self.get_or_create_category(
                guild, cat_cfg["name"], cat_cfg["order"], cat_overwrites
            )

            for idx, chan_cfg in enumerate(cat_cfg["channels"]):
                visibility = chan_cfg.get("visibility_override", cat_cfg["visibility"])
                chan_overwrites = self.overwrites_for(
                    guild, roles_by_name, visibility,
                    deny_send_everyone=chan_cfg.get("somente_leitura", False),
                )
                await self.get_or_create_channel(guild, category, chan_cfg, idx, chan_overwrites)

        log.info("Sincronização concluída.")
        return roles_by_name

    # ------------------------------------------------------------------
    # Mensagem de regras + botão persistente
    # ------------------------------------------------------------------
    def build_rules_embeds(self) -> list[discord.Embed]:
        rules_cfg = self.config["rules"]
        embeds = []
        current = discord.Embed(title=rules_cfg["titulo"], description=rules_cfg["intro"],
                                 color=discord.Color.blurple())
        embeds.append(current)
        for item in rules_cfg["itens"]:
            if len(current.fields) >= 5:
                current = discord.Embed(color=discord.Color.blurple())
                embeds.append(current)
            current.add_field(name=item["titulo"], value=item["texto"][:1024], inline=False)
        return embeds

    async def ensure_rules_message(self, guild: discord.Guild):
        onboarding = self.config["onboarding"]
        channel = discord.utils.get(guild.text_channels, name=onboarding["regras_channel"])
        if channel is None:
            log.warning("Canal de regras '%s' não encontrado -- rode a sincronização primeiro.",
                        onboarding["regras_channel"])
            return

        marker = "discord-setup:regras"
        target_message = None
        async for msg in channel.history(limit=50):
            if msg.author.id == self.user.id and msg.embeds and msg.embeds[0].footer.text == marker:
                target_message = msg
                break

        embeds = self.build_rules_embeds()
        embeds[-1].set_footer(text=marker)
        view = RulesView(self, onboarding)

        if target_message:
            await target_message.edit(embeds=embeds, view=view)
        else:
            await channel.send(embeds=embeds, view=view)

    # ------------------------------------------------------------------
    # Onboarding: DM perguntando nick/classe + ajuste de apelido
    # ------------------------------------------------------------------
    async def on_member_join(self, member: discord.Member):
        onboarding = self.config["onboarding"]
        try:
            dm = await member.create_dm()
            await dm.send(onboarding["dm_boas_vindas"])
        except discord.Forbidden:
            guild = member.guild
            channel = discord.utils.get(guild.text_channels, name=onboarding["boas_vindas_channel"])
            if channel:
                await channel.send(
                    f"{member.mention} não consegui te mandar DM! Abra suas mensagens diretas "
                    f"pra membros do servidor e me envie qualquer mensagem por aqui que eu "
                    f"configuro seu acesso, ou chame a Moderação."
                )
            return

        def check(m: discord.Message):
            return m.author.id == member.id and isinstance(m.channel, discord.DMChannel)

        try:
            reply = await self.wait_for("message", check=check, timeout=1800)
        except asyncio.TimeoutError:
            await dm.send(
                "Não recebi sua resposta a tempo. Sem problema -- me manda uma mensagem "
                "aqui (`Nick, Classe`) quando puder que eu configuro seu apelido."
            )
            return

        nick, classe = self._parse_nick_classe(reply.content)
        if nick is None:
            await dm.send(
                "Não entendi. Manda no formato `Nick, Classe`, "
                "exemplo: `Fulano, Assassin Cross`."
            )
            return

        novo_nick = onboarding["nickname_template"].format(nick=nick, classe=classe)[:32]
        try:
            await member.edit(nick=novo_nick, reason="discord-setup: onboarding")
        except discord.Forbidden:
            log.warning("Sem permissão pra editar apelido de %s.", member)

        await dm.send(
            onboarding["dm_apos_cadastrar_nick"].format(
                nick=nick, regras_channel=onboarding["regras_channel"]
            )
        )

    @staticmethod
    def _parse_nick_classe(text: str):
        if "," not in text:
            return None, None
        nick, _, classe = text.partition(",")
        nick, classe = nick.strip(), classe.strip()
        if not nick or not classe:
            return None, None
        return nick, classe

    def resolve_guild(self) -> discord.Guild | None:
        guild = self.get_guild(self.guild_id)
        if guild is not None:
            return guild
        if len(self.guilds) == 1:
            guild = self.guilds[0]
            log.warning(
                "DISCORD_GUILD_ID (%s) não bate com nenhum servidor em que o bot está -- "
                "usando o único servidor disponível: '%s' (%s).",
                self.guild_id, guild.name, guild.id,
            )
            return guild
        return None

    async def on_ready(self):
        log.info("Conectado como %s", self.user)
        guild = self.resolve_guild()
        if guild is None:
            log.error(
                "Não foi possível identificar o servidor. O bot está em %d servidores: %s. "
                "Ajuste DISCORD_GUILD_ID no .env para o ID correto (botão direito no ícone "
                "do servidor > Copiar ID de Servidor).",
                len(self.guilds), ", ".join(f"{g.name} ({g.id})" for g in self.guilds),
            )
            return
        roles_by_name = await self.sync_structure(guild)
        self.add_view(RulesView(self, self.config["onboarding"]))
        await self.ensure_rules_message(guild)
        log.info("Pronto. Cargos ativos: %s", ", ".join(roles_by_name))


class RulesView(discord.ui.View):
    """Botão persistente (sobrevive a restart do bot, via custom_id fixo)."""

    def __init__(self, client: "SetupBot", onboarding_cfg: dict):
        super().__init__(timeout=None)
        self.client = client
        self.onboarding_cfg = onboarding_cfg
        self.confirmar.label = onboarding_cfg["botao_confirmar_label"]

    @discord.ui.button(style=discord.ButtonStyle.success, custom_id="discord-setup:confirmar_regras")
    async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
        role_name = self.onboarding_cfg["cargo_liberado_apos_confirmar"]
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if role is None:
            await interaction.response.send_message(
                "Cargo de acesso não encontrado -- avise a Liderança.", ephemeral=True
            )
            return
        await interaction.user.add_roles(role, reason="Confirmou leitura das regras")
        await interaction.response.send_message(self.onboarding_cfg["msg_apos_confirmar"], ephemeral=True)


client = SetupBot()
tree = client.tree


@tree.command(name="sync", description="Reaplica config.yaml no servidor (cargos, canais e regras).")
@app_commands.checks.has_permissions(administrator=True)
async def sync_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    client.config = load_config()  # recarrega o arquivo do zero
    await client.sync_structure(interaction.guild)
    await client.ensure_rules_message(interaction.guild)
    await interaction.followup.send("Configuração sincronizada com sucesso. ✅", ephemeral=True)


@tree.command(name="resumo", description="Cria/atualiza o resumo fixado no topo deste canal (texto e/ou imagem).")
@app_commands.describe(
    texto="Novo texto do resumo (deixe em branco pra só trocar a imagem, mantendo o texto atual)",
    imagem="Imagem opcional pra ilustrar o resumo",
)
@app_commands.checks.has_permissions(manage_messages=True)
async def resumo_command(interaction: discord.Interaction, texto: str = None, imagem: discord.Attachment = None):
    channel = interaction.channel
    if not isinstance(channel, discord.TextChannel):
        await interaction.response.send_message(
            "Esse comando só funciona em canais de texto (não dá em fórum nem voz).", ephemeral=True
        )
        return

    marker = "discord-setup:intro"
    existing_msg = None
    async for msg in channel.history(limit=20, oldest_first=True):
        if msg.author.id == client.user.id and msg.embeds and msg.embeds[0].footer.text == marker:
            existing_msg = msg
            break

    descricao = texto or (existing_msg.embeds[0].description if existing_msg else None)
    if not descricao:
        await interaction.response.send_message(
            "Preciso de um texto pelo menos na primeira vez -- use `/resumo texto: ...`.", ephemeral=True
        )
        return

    embed = discord.Embed(description=descricao, color=discord.Color.blurple())
    embed.set_footer(text=marker)
    if imagem:
        embed.set_image(url=imagem.url)
    elif existing_msg and existing_msg.embeds[0].image:
        embed.set_image(url=existing_msg.embeds[0].image.url)

    if existing_msg:
        await existing_msg.edit(embed=embed)
    else:
        existing_msg = await channel.send(embed=embed)
        try:
            await existing_msg.pin(reason="discord-setup: resumo do canal")
        except discord.Forbidden:
            pass

    await interaction.response.send_message("Resumo atualizado. ✅", ephemeral=True)


@tree.command(name="xprate", description="Atualiza o bônus de XP/drop vigente no canal de status.")
@app_commands.describe(
    bonus="Bônus mostrado no jogo agora (ex: +100%)",
    ate="Até quando vale, se souber (ex: 22h, domingo 23h59) -- opcional",
    avisar="Mandar aviso novo no canal chamando os Participantes? (padrão: sim)",
)
@app_commands.checks.has_permissions(manage_messages=True)
async def xprate_command(interaction: discord.Interaction, bonus: str, ate: str = None, avisar: bool = True):
    channel = discord.utils.get(interaction.guild.text_channels, name="status-xp-drop-penalidade")
    if channel is None:
        await interaction.response.send_message(
            "Canal 'status-xp-drop-penalidade' não encontrado -- rode /sync primeiro.", ephemeral=True
        )
        return

    marker = "discord-setup:xprate"
    texto = f"📈 **Bônus de XP/Drop atual: {bonus}**"
    if ate:
        texto += f"\nVale até: {ate}"
    texto += f"\n\n*Atualizado por {interaction.user.mention} <t:{int(discord.utils.utcnow().timestamp())}:R>*"

    target = None
    async for msg in channel.history(limit=20, oldest_first=True):
        if msg.author.id == client.user.id and msg.embeds and msg.embeds[0].footer.text == marker:
            target = msg
            break

    embed = discord.Embed(description=texto, color=discord.Color.gold())
    embed.set_footer(text=marker)
    if target:
        await target.edit(embed=embed)
    else:
        target = await channel.send(embed=embed)
        try:
            await target.pin(reason="discord-setup: status de xp")
        except discord.Forbidden:
            pass

    if avisar:
        role = discord.utils.get(interaction.guild.roles, name="Participantes")
        mention = role.mention if role else ""
        aviso = f"{mention} 📈 O bônus de XP/Drop mudou: **{bonus}**" + (f" (até {ate})" if ate else "")
        await channel.send(aviso, allowed_mentions=discord.AllowedMentions(roles=True))

    await interaction.response.send_message("Status de XP atualizado. ✅", ephemeral=True)


if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("Defina DISCORD_BOT_TOKEN no arquivo .env (veja .env.example).")
    try:
        client.run(token, log_handler=None)
    except discord.LoginFailure:
        raise SystemExit(
            "Token inválido. Gere um novo em Discord Developer Portal > sua aplicação > "
            "Bot > Reset Token, e atualize o .env."
        )
    except discord.PrivilegedIntentsRequired:
        raise SystemExit(
            "Faltou ativar os Privileged Gateway Intents. Vá em Discord Developer Portal > "
            "sua aplicação > Bot > Privileged Gateway Intents e ligue 'Server Members Intent' "
            "e 'Message Content Intent'."
        )
