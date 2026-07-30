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
import json
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

# Ordem hierárquica -- cada membro tem UM só desses cargos por vez (não é
# mais cumulativo). Visibilidade de canal por tier X libera esse cargo e
# todos os que vêm depois dele nesta lista.
CARGOS_HIERARQUICOS = ["Participantes", "Membros", "Moderação", "Liderança"]

VISIBILITY_TIER = {
    "participantes": 0,
    "membros": 1,
    "moderacao": 2,
    "lideranca": 3,
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
        # Cargo é único por pessoa (não cumulativo), então cada canal precisa
        # liberar explicitamente o cargo alvo E todos os que vêm depois dele
        # na hierarquia -- senão quem só tem "Liderança", por exemplo, não
        # veria canais marcados como "membros" ou "participantes".
        ow = {everyone: discord.PermissionOverwrite(view_channel=False)}
        tier = VISIBILITY_TIER[visibility]
        liberados = set(CARGOS_HIERARQUICOS[tier:])
        for nome in CARGOS_HIERARQUICOS:
            role = roles_by_name.get(nome)
            if role is None:
                continue
            ow[role] = discord.PermissionOverwrite(view_channel=(nome in liberados))
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
        embeds[0].set_footer(text=marker)  # precisa ser o [0] -- é o que a busca acima confere
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
        self.add_view(InstanciaView())
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


class InstanciaView(discord.ui.View):
    """Botões de confirmação de presença -- persistente, um único view cobre
    todas as mensagens de /instancia (o estado fica salvo nos campos do
    embed de cada mensagem, não no view em si)."""

    def __init__(self):
        super().__init__(timeout=None)

    async def _registrar(self, interaction: discord.Interaction, indice_alvo: int):
        embed = interaction.message.embeds[0]
        mencao = interaction.user.mention

        novos_campos = []
        for i, field in enumerate(embed.fields):
            nomes = [] if field.value == "-" else field.value.split("\n")
            nomes = [n for n in nomes if n != mencao]
            if i == indice_alvo:
                nomes.append(mencao)
            label = field.name.split(" (")[0]
            novos_campos.append((f"{label} ({len(nomes)})", "\n".join(nomes) if nomes else "-"))

        embed.clear_fields()
        for nome, valor in novos_campos:
            embed.add_field(name=nome, value=valor, inline=True)
        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Vou", emoji="✅", style=discord.ButtonStyle.success,
                        custom_id="discord-setup:instancia_vou")
    async def vou(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._registrar(interaction, 0)

    @discord.ui.button(label="Não vou", emoji="❌", style=discord.ButtonStyle.danger,
                        custom_id="discord-setup:instancia_nao")
    async def nao_vou(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._registrar(interaction, 1)

    @discord.ui.button(label="Talvez", emoji="🤔", style=discord.ButtonStyle.secondary,
                        custom_id="discord-setup:instancia_talvez")
    async def talvez(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._registrar(interaction, 2)


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


@tree.command(name="promover", description="Troca o cargo hierárquico de um membro (Participantes/Membros/Moderação/Liderança).")
@app_commands.describe(
    membro="Quem vai trocar de cargo",
    cargo="Novo cargo -- substitui qualquer um dos outros três que a pessoa já tinha",
)
@app_commands.choices(cargo=[app_commands.Choice(name=c, value=c) for c in CARGOS_HIERARQUICOS])
@app_commands.checks.has_permissions(administrator=True)
async def promover_command(interaction: discord.Interaction, membro: discord.Member, cargo: app_commands.Choice[str]):
    # O Discord não deixa NINGUÉM (nem Administrator) atribuir manualmente um
    # cargo igual ou acima do próprio cargo mais alto -- só o Dono real da
    # conta escapa disso. Como o cargo do bot está acima de todos, ele
    # consegue atribuir por quem chamou o comando (que precisa já ser
    # Liderança/Administrator pra poder chamar).
    alvo_nome = cargo.value
    alvo_role = discord.utils.get(interaction.guild.roles, name=alvo_nome)
    if alvo_role is None:
        await interaction.response.send_message(
            f"Não encontrei o cargo '{alvo_nome}' -- rode /sync primeiro.", ephemeral=True
        )
        return

    # Cada pessoa tem só UM dos quatro cargos por vez -- remove qualquer
    # outro que ela já tinha antes de dar o novo.
    outros = [r for r in membro.roles if r.name in CARGOS_HIERARQUICOS and r.id != alvo_role.id]

    try:
        if outros:
            await membro.remove_roles(*outros, reason=f"Troca de cargo por {interaction.user} via /promover")
        if alvo_role not in membro.roles:
            await membro.add_roles(alvo_role, reason=f"Atribuído por {interaction.user} via /promover")
    except discord.Forbidden:
        await interaction.response.send_message(
            "Sem permissão pra alterar algum desses cargos -- confirme que o cargo do bot "
            "está acima de todos em Configurações do Servidor > Cargos.", ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"{membro.mention} agora tem apenas o cargo **{alvo_nome}**. ✅", ephemeral=True
    )


@tree.command(name="apelido", description="Muda o apelido de um membro -- funciona mesmo entre duas pessoas de Liderança.")
@app_commands.describe(
    membro="Quem vai ter o apelido alterado",
    nick="Novo apelido (deixe em branco pra remover o apelido customizado e voltar ao nome original)",
)
@app_commands.checks.has_permissions(administrator=True)
async def apelido_command(interaction: discord.Interaction, membro: discord.Member, nick: str = None):
    # Mesma trava de hierarquia do /promover: editar apelido de outra pessoa
    # exige que o cargo mais alto de quem edita seja MAIOR que o da pessoa
    # editada -- não funciona entre dois Liderança, nem pro Dono não ser
    # necessário. O bot contorna isso porque o cargo dele está acima de todos.
    try:
        await membro.edit(nick=nick, reason=f"Apelido alterado por {interaction.user} via /apelido")
    except discord.Forbidden:
        await interaction.response.send_message(
            "Sem permissão pra mudar o apelido dessa pessoa -- confirme que o cargo do bot "
            "está acima de todos em Configurações do Servidor > Cargos.", ephemeral=True
        )
        return

    novo = nick or membro.name
    await interaction.response.send_message(
        f"Apelido de {membro.mention} atualizado para **{novo}**. ✅", ephemeral=True
    )


class ResumoModal(discord.ui.Modal, title="Resumo do canal"):
    # style=paragraph é o campo de texto "de verdade" do Discord -- só ele
    # aceita Enter/Shift+Enter pra quebrar linha. Campo de slash command
    # normal (texto: ...) é sempre de uma linha só, não tem como mudar isso.
    texto = discord.ui.TextInput(label="Texto do resumo", style=discord.TextStyle.paragraph, max_length=4000)

    def __init__(self, channel: discord.TextChannel, existing_msg, imagem_url: str | None, marker: str):
        super().__init__()
        self.channel = channel
        self.existing_msg = existing_msg
        self.imagem_url = imagem_url
        self.marker = marker
        if existing_msg:
            self.texto.default = existing_msg.embeds[0].description or ""

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(description=self.texto.value, color=discord.Color.blurple())
        embed.set_footer(text=self.marker)
        if self.imagem_url:
            embed.set_image(url=self.imagem_url)

        if self.existing_msg:
            await self.existing_msg.edit(embed=embed)
        else:
            msg = await self.channel.send(embed=embed)
            try:
                await msg.pin(reason="discord-setup: resumo do canal")
            except discord.Forbidden:
                pass

        await interaction.response.send_message("Resumo atualizado. ✅", ephemeral=True)


@tree.command(name="resumo", description="Cria/atualiza o resumo fixado no topo deste canal (abre um formulário com quebra de linha).")
@app_commands.describe(imagem="Imagem opcional pra ilustrar o resumo (deixe em branco pra manter a atual)")
@app_commands.checks.has_permissions(manage_messages=True)
async def resumo_command(interaction: discord.Interaction, imagem: discord.Attachment = None):
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

    imagem_url = imagem.url if imagem else (
        existing_msg.embeds[0].image.url if existing_msg and existing_msg.embeds[0].image else None
    )
    await interaction.response.send_modal(ResumoModal(channel, existing_msg, imagem_url, marker))


XPRATE_MARKER = "discord-setup:xprate"
XPRATE_CAMPOS = (
    "exp_bonus", "exp_nidhogg",
    "drop_bonus", "drop_nidhogg",
    "penalidade_bonus", "penalidade_nidhogg",
)


def _formata_taxa(label: str, bonus: float, nidhogg: float) -> str:
    total = 100.0 + bonus + nidhogg
    return f"**Taxa de {label}:** {total:.1f}% ( Normal 100.0% + Bônus {bonus:.1f}% + Nidhogg {nidhogg:.1f}% )"


@tree.command(name="xprate", description="Atualiza as taxas de EXP/Drop/Penalidade vigentes (igual à tela do jogo).")
@app_commands.describe(
    exp_bonus="% de Bônus na taxa de EXP -- deixe em branco pra manter o valor atual",
    exp_nidhogg="% de Nidhogg na taxa de EXP",
    drop_bonus="% de Bônus na taxa de DROP",
    drop_nidhogg="% de Nidhogg na taxa de DROP",
    penalidade_bonus="% de Bônus na Penalidade de Morte",
    penalidade_nidhogg="% de Nidhogg na Penalidade de Morte",
    avisar="Mandar aviso novo no canal? (padrão: sim)",
    mencionar="Quem chamar no aviso (padrão: @everyone)",
)
@app_commands.choices(mencionar=[
    app_commands.Choice(name="@everyone", value="everyone"),
    app_commands.Choice(name="@here (só quem está online)", value="here"),
    app_commands.Choice(name="Cargo Participantes", value="participantes"),
])
@app_commands.checks.has_permissions(manage_messages=True)
async def xprate_command(
    interaction: discord.Interaction,
    exp_bonus: float = None,
    exp_nidhogg: float = None,
    drop_bonus: float = None,
    drop_nidhogg: float = None,
    penalidade_bonus: float = None,
    penalidade_nidhogg: float = None,
    avisar: bool = True,
    mencionar: app_commands.Choice[str] = None,
):
    channel = discord.utils.get(interaction.guild.text_channels, name="status-xp-drop-penalidade")
    if channel is None:
        await interaction.response.send_message(
            "Canal 'status-xp-drop-penalidade' não encontrado -- rode /sync primeiro.", ephemeral=True
        )
        return

    state = {campo: 0.0 for campo in XPRATE_CAMPOS}
    target = None
    async for msg in channel.history(limit=20, oldest_first=True):
        footer = (msg.embeds[0].footer.text or "") if msg.embeds else ""
        if msg.author.id == client.user.id and footer.startswith(XPRATE_MARKER):
            target = msg
            try:
                salvo = json.loads(footer.split("|", 1)[1])
                state.update({k: v for k, v in salvo.items() if k in state})
            except (IndexError, ValueError, json.JSONDecodeError):
                pass
            break

    novos_valores = {
        "exp_bonus": exp_bonus, "exp_nidhogg": exp_nidhogg,
        "drop_bonus": drop_bonus, "drop_nidhogg": drop_nidhogg,
        "penalidade_bonus": penalidade_bonus, "penalidade_nidhogg": penalidade_nidhogg,
    }
    for campo, valor in novos_valores.items():
        if valor is not None:
            state[campo] = valor

    texto = (
        f"{_formata_taxa('E X P', state['exp_bonus'], state['exp_nidhogg'])}\n"
        f"{_formata_taxa('DROP', state['drop_bonus'], state['drop_nidhogg'])}\n"
        f"{_formata_taxa('Penalidade de Morte', state['penalidade_bonus'], state['penalidade_nidhogg'])}\n\n"
        f"*Atualizado por {interaction.user.mention} <t:{int(discord.utils.utcnow().timestamp())}:R>*"
    )

    embed = discord.Embed(title="📊 Taxas atuais do servidor", description=texto, color=discord.Color.gold())
    embed.set_footer(text=f"{XPRATE_MARKER}|{json.dumps(state)}")

    if target:
        await target.edit(embed=embed)
    else:
        target = await channel.send(embed=embed)
        try:
            await target.pin(reason="discord-setup: status de xp")
        except discord.Forbidden:
            pass

    if avisar:
        alvo = mencionar.value if mencionar else "everyone"
        if alvo == "participantes":
            role = discord.utils.get(interaction.guild.roles, name="Participantes")
            mention = role.mention if role else ""
        else:
            mention = f"@{alvo}"  # "@everyone" ou "@here"
        exp_total = 100.0 + state["exp_bonus"] + state["exp_nidhogg"]
        drop_total = 100.0 + state["drop_bonus"] + state["drop_nidhogg"]
        pen_total = 100.0 + state["penalidade_bonus"] + state["penalidade_nidhogg"]
        aviso = (
            f"{mention} 📊 As taxas do servidor mudaram! "
            f"EXP {exp_total:.1f}% · DROP {drop_total:.1f}% · Penalidade {pen_total:.1f}%"
        )
        await channel.send(aviso, allowed_mentions=discord.AllowedMentions(everyone=True, roles=True))

    await interaction.response.send_message("Taxas atualizadas. ✅", ephemeral=True)


MENCIONAR_CHOICES = [
    app_commands.Choice(name="@everyone", value="everyone"),
    app_commands.Choice(name="@here (só quem está online)", value="here"),
    app_commands.Choice(name="Nenhuma menção", value="nenhuma"),
]


def _conteudo_mencao(mencionar: app_commands.Choice[str] | None) -> str | None:
    alvo = mencionar.value if mencionar else "everyone"
    return None if alvo == "nenhuma" else f"@{alvo}"


@tree.command(name="instancia", description="Anuncia uma instância/atividade e abre confirmação de presença.")
@app_commands.describe(
    nome="Nome da instância/atividade",
    quando="Quando vai rolar (ex: hoje 20h, sábado 19h)",
    vagas="Número de vagas, se houver limite -- opcional",
    obs="Observações extras -- opcional",
    mencionar="Quem chamar no aviso (padrão: @everyone)",
)
@app_commands.choices(mencionar=MENCIONAR_CHOICES)
@app_commands.checks.has_permissions(manage_messages=True)
async def instancia_command(
    interaction: discord.Interaction,
    nome: str,
    quando: str,
    vagas: int = None,
    obs: str = None,
    mencionar: app_commands.Choice[str] = None,
):
    channel = discord.utils.get(interaction.guild.text_channels, name="anuncio-de-instancias")
    if channel is None:
        await interaction.response.send_message(
            "Canal 'anuncio-de-instancias' não encontrado -- rode /sync primeiro.", ephemeral=True
        )
        return

    descricao = f"**Quando:** {quando}"
    if vagas is not None:
        descricao += f"\n**Vagas:** {vagas}"
    if obs:
        descricao += f"\n{obs}"
    descricao += f"\n\n*Organizado por {interaction.user.mention}*"

    embed = discord.Embed(title=f"🗡️ Instância: {nome}", description=descricao, color=discord.Color.blurple())
    embed.add_field(name="✅ Vou (0)", value="-", inline=True)
    embed.add_field(name="❌ Não vou (0)", value="-", inline=True)
    embed.add_field(name="🤔 Talvez (0)", value="-", inline=True)

    await channel.send(
        content=_conteudo_mencao(mencionar),
        embed=embed,
        view=InstanciaView(),
        allowed_mentions=discord.AllowedMentions(everyone=True),
    )
    await interaction.response.send_message("Instância anunciada! ✅", ephemeral=True)


CRONOGRAMA_DIAS = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
CRONOGRAMA_LABELS = {
    "segunda": "Segunda", "terca": "Terça", "quarta": "Quarta", "quinta": "Quinta",
    "sexta": "Sexta", "sabado": "Sábado", "domingo": "Domingo",
}
CRONOGRAMA_MARKER = "discord-setup:cronograma"


@tree.command(name="cronograma", description="Atualiza o cronograma semanal fixado em #anuncio-de-instancias.")
@app_commands.describe(
    segunda="Atividade de segunda-feira (deixe em branco pra manter o valor atual)",
    terca="Atividade de terça-feira",
    quarta="Atividade de quarta-feira",
    quinta="Atividade de quinta-feira",
    sexta="Atividade de sexta-feira",
    sabado="Atividade de sábado",
    domingo="Atividade de domingo",
    limpar="Limpa o cronograma inteiro, ignorando os outros campos",
)
@app_commands.checks.has_permissions(manage_messages=True)
async def cronograma_command(
    interaction: discord.Interaction,
    segunda: str = None,
    terca: str = None,
    quarta: str = None,
    quinta: str = None,
    sexta: str = None,
    sabado: str = None,
    domingo: str = None,
    limpar: bool = False,
):
    channel = discord.utils.get(interaction.guild.text_channels, name="anuncio-de-instancias")
    if channel is None:
        await interaction.response.send_message(
            "Canal 'anuncio-de-instancias' não encontrado -- rode /sync primeiro.", ephemeral=True
        )
        return

    state = {dia: "" for dia in CRONOGRAMA_DIAS}
    target = None
    async for msg in channel.history(limit=20, oldest_first=True):
        footer = (msg.embeds[0].footer.text or "") if msg.embeds else ""
        if msg.author.id == client.user.id and footer.startswith(CRONOGRAMA_MARKER):
            target = msg
            try:
                salvo = json.loads(footer.split("|", 1)[1])
                state.update({k: v for k, v in salvo.items() if k in state})
            except (IndexError, ValueError, json.JSONDecodeError):
                pass
            break

    if limpar:
        state = {dia: "" for dia in CRONOGRAMA_DIAS}
    else:
        novos = {
            "segunda": segunda, "terca": terca, "quarta": quarta, "quinta": quinta,
            "sexta": sexta, "sabado": sabado, "domingo": domingo,
        }
        for dia, valor in novos.items():
            if valor is not None:
                state[dia] = valor

    texto = "\n".join(
        f"**{CRONOGRAMA_LABELS[dia]}:** {state[dia] or '—'}" for dia in CRONOGRAMA_DIAS
    )
    embed = discord.Embed(title="🗓️ Cronograma da semana", description=texto, color=discord.Color.teal())
    embed.set_footer(text=f"{CRONOGRAMA_MARKER}|{json.dumps(state)}")

    if target:
        await target.edit(embed=embed)
    else:
        target = await channel.send(embed=embed)
        try:
            await target.pin(reason="discord-setup: cronograma semanal")
        except discord.Forbidden:
            pass

    await interaction.response.send_message("Cronograma atualizado. ✅", ephemeral=True)


class ComunicadoModal(discord.ui.Modal, title="Novo comunicado"):
    titulo = discord.ui.TextInput(label="Título", style=discord.TextStyle.short, max_length=256)
    texto = discord.ui.TextInput(label="Texto", style=discord.TextStyle.paragraph, max_length=4000)

    def __init__(self, channel: discord.TextChannel, imagem_url: str | None, conteudo_mencao: str | None):
        super().__init__()
        self.channel = channel
        self.imagem_url = imagem_url
        self.conteudo_mencao = conteudo_mencao

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"📣 {self.titulo.value}", description=self.texto.value,
                               color=discord.Color.orange())
        if self.imagem_url:
            embed.set_image(url=self.imagem_url)
        embed.set_footer(text=f"Publicado por {interaction.user.display_name}")

        await self.channel.send(
            content=self.conteudo_mencao,
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=True),
        )
        await interaction.response.send_message("Comunicado publicado! ✅", ephemeral=True)


@tree.command(name="comunicado", description="Publica um comunicado da guilda (abre um formulário com quebra de linha).")
@app_commands.describe(
    imagem="Imagem opcional",
    mencionar="Quem chamar no aviso (padrão: @everyone)",
)
@app_commands.choices(mencionar=MENCIONAR_CHOICES)
@app_commands.checks.has_permissions(manage_messages=True)
async def comunicado_command(
    interaction: discord.Interaction,
    imagem: discord.Attachment = None,
    mencionar: app_commands.Choice[str] = None,
):
    channel = discord.utils.get(interaction.guild.text_channels, name="comunicados-da-guilda")
    if channel is None:
        await interaction.response.send_message(
            "Canal 'comunicados-da-guilda' não encontrado -- rode /sync primeiro.", ephemeral=True
        )
        return

    imagem_url = imagem.url if imagem else None
    await interaction.response.send_modal(
        ComunicadoModal(channel, imagem_url, _conteudo_mencao(mencionar))
    )


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
