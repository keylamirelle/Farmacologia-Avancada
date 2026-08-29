"""
Bot de configuração e onboarding do servidor de Discord da comunidade.

O que ele faz:
  1. Comandos utilitários pra Moderação/Liderança administrarem o servidor
     e os canais (ver README) -- todos esperam que os cargos e canais que
     usam já existam no Discord (o bot não cria nem edita estrutura).
  2. Publica a mensagem de regras no canal #regras (só na primeira vez, se
     ela ainda não existir), com um botão "Li e concordo" que libera o
     cargo Participantes.
  3. Quando alguém entra no servidor, manda uma DM perguntando nick e
     classe, ajusta o apelido, e direciona a pessoa para o canal de regras.

Rode com: python bot.py
Configuração: variáveis de ambiente em .env (veja .env.example) + config.yaml
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import discord
import yaml
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv

FUSO_HORARIO = ZoneInfo("America/Sao_Paulo")

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("discord-setup")

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
REGRAS_MARKER = "discord-setup:regras"

# -----------------------------------------------------------------------------
# Permissões extras por comando (/permissao) -- guardadas numa mensagem do
# Discord (não em arquivo local) porque o Railway reseta o disco a cada
# redeploy. Carregado uma vez em on_ready e mantido em cache em memória;
# toda alteração via /permissao reescreve a mensagem na hora.
# -----------------------------------------------------------------------------
COMANDOS_GERENCIAVEIS = [
    "promover", "resumo", "regras",
    "xprate", "instancia", "cronograma", "comunicado", "permissao",
]
PERMISSOES_CANAL = "comunicacao-lideranca"
PERMISSOES_MARKER = "discord-setup:permissoes"

_permissoes_extra: dict[str, dict[str, set]] = {}
_permissoes_msg: discord.Message | None = None


async def _carregar_permissoes_extra(guild: discord.Guild):
    global _permissoes_msg
    channel = discord.utils.get(guild.text_channels, name=PERMISSOES_CANAL)
    if channel is None:
        return
    async for msg in channel.history(limit=50):
        footer = (msg.embeds[0].footer.text or "") if msg.embeds else ""
        if msg.author.id == client.user.id and footer.startswith(PERMISSOES_MARKER):
            _permissoes_msg = msg
            try:
                bruto = json.loads(footer.split("|", 1)[1])
                for cmd, dados in bruto.items():
                    _permissoes_extra[cmd] = {
                        "users": set(dados.get("users", [])),
                        "roles": set(dados.get("roles", [])),
                    }
            except (IndexError, ValueError, json.JSONDecodeError):
                log.warning("Não consegui ler a mensagem de permissões extras -- ignorando.")
            return


async def _salvar_permissoes_extra(guild: discord.Guild):
    global _permissoes_msg
    channel = discord.utils.get(guild.text_channels, name=PERMISSOES_CANAL)
    if channel is None:
        log.warning("Canal '%s' não encontrado -- não consegui salvar permissões extras.",
                    PERMISSOES_CANAL)
        return

    serializavel = {
        cmd: {"users": sorted(dados["users"]), "roles": sorted(dados["roles"])}
        for cmd, dados in _permissoes_extra.items() if dados["users"] or dados["roles"]
    }

    linhas = [
        "⚙️ **Dados internos do bot -- não edite esta mensagem manualmente.**",
        "Controla quem tem acesso extra a comandos além de Moderação+/Liderança "
        "(gerenciado com `/permissao`).",
        "",
    ]
    if not serializavel:
        linhas.append("_Nenhuma permissão extra configurada no momento._")
    else:
        for cmd, dados in serializavel.items():
            partes = []
            if dados["users"]:
                partes.append("pessoas: " + ", ".join(f"<@{u}>" for u in dados["users"]))
            if dados["roles"]:
                partes.append("cargos: " + ", ".join(f"<@&{r}>" for r in dados["roles"]))
            linhas.append(f"`/{cmd}` — " + "; ".join(partes))

    embed = discord.Embed(description="\n".join(linhas), color=discord.Color.dark_grey())
    embed.set_footer(text=f"{PERMISSOES_MARKER}|{json.dumps(serializavel)}")

    if _permissoes_msg:
        await _permissoes_msg.edit(embed=embed)
    else:
        _permissoes_msg = await channel.send(embed=embed)


def permissao_ou_excecao(nome_comando: str, **permissoes_base):
    """Mesmo que app_commands.checks.has_permissions(**permissoes_base), mas
    também libera quem foi adicionado via /permissao pra esse comando
    específico (pessoa ou cargo), mesmo sem ter a permissão base."""
    permissoes_necessarias = discord.Permissions(**permissoes_base)

    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.permissions.is_superset(permissoes_necessarias):
            return True
        extra = _permissoes_extra.get(nome_comando)
        if not extra:
            return False
        if interaction.user.id in extra["users"]:
            return True
        ids_dos_cargos = {r.id for r in getattr(interaction.user, "roles", [])}
        return bool(ids_dos_cargos & extra["roles"])

    return app_commands.check(predicate)

# Ordem hierárquica -- cada membro tem UM só desses cargos por vez (não é
# mais cumulativo). Usado pelo /promover.
CARGOS_HIERARQUICOS = ["Participantes", "Membros", "Moderação", "Liderança"]


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
        # Cria a mensagem de regras SÓ na primeira vez (semeada com o texto
        # do config.yaml). Chamado sempre que o bot conecta, mas nunca
        # sobrescreve uma mensagem já existente -- a edição passa a ser
        # feita com /regras direto no Discord, igual ao /resumo dos
        # outros canais.
        onboarding = self.config["onboarding"]
        channel = discord.utils.get(guild.text_channels, name=onboarding["regras_channel"])
        if channel is None:
            log.warning("Canal de regras '%s' não encontrado -- rode a sincronização primeiro.",
                        onboarding["regras_channel"])
            return

        async for msg in channel.history(limit=50):
            if msg.author.id == self.user.id and msg.embeds and msg.embeds[0].footer.text == REGRAS_MARKER:
                return  # já existe -- não mexe

        embeds = self.build_rules_embeds()
        embeds[0].set_footer(text=REGRAS_MARKER)  # precisa ser o [0], é o que a busca acima confere
        await channel.send(embeds=embeds, view=RulesView(self, onboarding))

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
        # O bot não cria/edita estrutura do Discord (cargos, categorias,
        # canais) em lugar nenhum -- isso é feito manualmente. A única
        # exceção é a mensagem de regras logo abaixo: ela só é CRIADA se
        # ainda não existir (nunca edita uma já existente), então é segura
        # de rodar sempre que o bot inicia.
        self.add_view(RulesView(self, self.config["onboarding"]))
        self.add_view(InstanciaView())
        await self.ensure_rules_message(guild)
        await _carregar_permissoes_extra(guild)
        if not fechar_instancias_vencidas.is_running():
            fechar_instancias_vencidas.start()
        log.info("Pronto -- conectado em '%s'.", guild.name)


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


INSTANCIA_MARKER = "discord-setup:instancia"
INSTANCIA_PRAZO_MINUTOS = 30  # respostas fecham sozinhas N minutos depois do horário marcado


def _instancia_prazo(embed: discord.Embed) -> int | None:
    footer = (embed.footer.text or "") if embed.footer else ""
    if not footer.startswith(INSTANCIA_MARKER):
        return None
    try:
        return json.loads(footer.split("|", 1)[1]).get("prazo")
    except (IndexError, ValueError, json.JSONDecodeError):
        return None


class InstanciaObsModal(discord.ui.Modal, title="Confirmar resposta"):
    observacao = discord.ui.TextInput(
        label="Observação (opcional)",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=200,
    )

    def __init__(self, mensagem: discord.Message, indice_alvo: int):
        super().__init__()
        self.mensagem = mensagem
        self.indice_alvo = indice_alvo

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.mensagem.embeds[0]
        mencao = interaction.user.mention
        obs = self.observacao.value.strip()
        entrada = f"{mencao} — {obs}" if obs else mencao

        novos_campos = []
        for i, field in enumerate(embed.fields):
            linhas = [] if field.value == "-" else field.value.split("\n")
            # troca de resposta descarta a anterior -- tira essa pessoa de
            # qualquer lista antes de adicionar na nova escolhida.
            linhas = [l for l in linhas if not l.startswith(mencao)]
            if i == self.indice_alvo:
                linhas.append(entrada)
            label = field.name.split(" (")[0]
            novos_campos.append((f"{label} ({len(linhas)})", "\n".join(linhas) if linhas else "-"))

        embed.clear_fields()
        for nome, valor in novos_campos:
            embed.add_field(name=nome, value=valor, inline=True)

        await self.mensagem.edit(embed=embed)
        await interaction.response.send_message("Resposta registrada. ✅", ephemeral=True)


class InstanciaView(discord.ui.View):
    """Botões de confirmação de presença -- persistente, um único view cobre
    todas as mensagens de /instancia (o estado fica salvo nos campos do
    embed de cada mensagem, não no view em si)."""

    def __init__(self):
        super().__init__(timeout=None)

    async def _abrir_modal(self, interaction: discord.Interaction, indice_alvo: int):
        embed = interaction.message.embeds[0] if interaction.message.embeds else None
        prazo = _instancia_prazo(embed) if embed else None
        if prazo and discord.utils.utcnow().timestamp() >= prazo:
            await interaction.response.send_message(
                "As respostas pra essa instância já foram encerradas.", ephemeral=True
            )
            return
        await interaction.response.send_modal(InstanciaObsModal(interaction.message, indice_alvo))

    @discord.ui.button(label="Vou", emoji="✅", style=discord.ButtonStyle.success,
                        custom_id="discord-setup:instancia_vou")
    async def vou(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir_modal(interaction, 0)

    @discord.ui.button(label="Não vou", emoji="❌", style=discord.ButtonStyle.danger,
                        custom_id="discord-setup:instancia_nao")
    async def nao_vou(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir_modal(interaction, 1)

    @discord.ui.button(label="Talvez", emoji="🤔", style=discord.ButtonStyle.secondary,
                        custom_id="discord-setup:instancia_talvez")
    async def talvez(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._abrir_modal(interaction, 2)


client = SetupBot()
tree = client.tree


@tasks.loop(minutes=5)
async def fechar_instancias_vencidas():
    guild = client.resolve_guild()
    if guild is None:
        return
    channel = discord.utils.get(guild.text_channels, name="anuncio-de-instancias")
    if channel is None:
        return

    agora = discord.utils.utcnow().timestamp()
    async for msg in channel.history(limit=50):
        if msg.author.id != client.user.id or not msg.embeds or not msg.components:
            continue  # não é do bot, ou já foi fechada antes (sem botões)
        prazo = _instancia_prazo(msg.embeds[0])
        if prazo is None or agora < prazo:
            continue
        embed = msg.embeds[0]
        if not embed.title.startswith("🔒"):
            embed.title = f"🔒 {embed.title}"
        try:
            await msg.edit(embed=embed, view=None)
        except discord.Forbidden:
            log.warning("Sem permissão pra encerrar respostas de instância em #%s.", channel.name)


@fechar_instancias_vencidas.before_loop
async def _antes_de_fechar_instancias_vencidas():
    await client.wait_until_ready()


@tree.command(name="promover", description="Troca o cargo hierárquico de um membro (Participantes/Membros/Moderação/Liderança).")
@app_commands.describe(
    membro="Quem vai trocar de cargo",
    cargo="Novo cargo -- substitui qualquer um dos outros três que a pessoa já tinha",
)
@app_commands.choices(cargo=[app_commands.Choice(name=c, value=c) for c in CARGOS_HIERARQUICOS])
@permissao_ou_excecao("promover", administrator=True)
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
            f"Não encontrei o cargo '{alvo_nome}' -- crie esse cargo manualmente no Discord "
            "com esse nome exato antes de usar /promover.", ephemeral=True
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
@permissao_ou_excecao("resumo", manage_messages=True)
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


def _extrair_texto_regras(msg: discord.Message) -> str:
    partes = []
    for embed in msg.embeds:
        if embed.description:
            partes.append(embed.description)
        for field in embed.fields:
            partes.append(f"{field.name}\n{field.value}")
    return "\n\n".join(partes)


def _dividir_embeds_regras(texto: str) -> list[discord.Embed]:
    # Cada embed aguenta até 4096 caracteres de descrição, mas o TOTAL de
    # caracteres somado entre todos os embeds de uma mensagem é limitado a
    # 6000 pelo Discord -- por isso o modal já limita as duas partes a um
    # tamanho que sempre cabe.
    pedacos, resto = [], texto
    while resto:
        pedacos.append(resto[:4000])
        resto = resto[4000:]
    embeds = [discord.Embed(title="📜 Regras da Comunidade", description=pedacos[0],
                             color=discord.Color.blurple())]
    for pedaco in pedacos[1:]:
        embeds.append(discord.Embed(description=pedaco, color=discord.Color.blurple()))
    embeds[0].set_footer(text=REGRAS_MARKER)
    return embeds


class RegrasModal(discord.ui.Modal, title="Editar regras da comunidade"):
    parte1 = discord.ui.TextInput(label="Regras (parte 1)", style=discord.TextStyle.paragraph, max_length=4000)
    parte2 = discord.ui.TextInput(label="Regras (parte 2, opcional)", style=discord.TextStyle.paragraph,
                                   max_length=1900, required=False)

    def __init__(self, mensagem: discord.Message, texto_atual: str):
        super().__init__()
        self.mensagem = mensagem
        self.parte1.default = texto_atual[:4000]
        self.parte2.default = texto_atual[4000:5900]

    async def on_submit(self, interaction: discord.Interaction):
        texto = self.parte1.value + (f"\n\n{self.parte2.value}" if self.parte2.value else "")
        embeds = _dividir_embeds_regras(texto)
        # não passa "view" -- deixa o botão "Li e concordo" que já está na
        # mensagem intacto, só troca o conteúdo dos embeds.
        try:
            await self.mensagem.edit(embeds=embeds)
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"Não consegui salvar -- o texto ficou grande demais pro Discord ({e}). "
                "Tenta encurtar um pouco.", ephemeral=True
            )
            return
        await interaction.response.send_message("Regras atualizadas. ✅", ephemeral=True)


@tree.command(name="regras", description="Edita o texto das regras (abre um formulário com quebra de linha).")
@permissao_ou_excecao("regras", manage_messages=True)
async def regras_command(interaction: discord.Interaction):
    onboarding = client.config["onboarding"]
    channel = discord.utils.get(interaction.guild.text_channels, name=onboarding["regras_channel"])
    if channel is None:
        await interaction.response.send_message(
            f"Canal '{onboarding['regras_channel']}' não encontrado -- crie esse canal de "
            "texto manualmente no Discord com esse nome exato.", ephemeral=True
        )
        return

    target = None
    async for msg in channel.history(limit=50):
        if msg.author.id == client.user.id and msg.embeds and msg.embeds[0].footer.text == REGRAS_MARKER:
            target = msg
            break

    if target is None:
        await interaction.response.send_message(
            "Não encontrei a mensagem de regras -- reinicie o bot (ele cria a mensagem "
            "sozinho ao conectar, se o canal já existir).", ephemeral=True
        )
        return

    texto_atual = _extrair_texto_regras(target)
    await interaction.response.send_modal(RegrasModal(target, texto_atual))


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
@permissao_ou_excecao("xprate", manage_messages=True)
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
    channel = discord.utils.get(interaction.guild.text_channels, name="xp-drop-status")
    if channel is None:
        await interaction.response.send_message(
            "Canal 'xp-drop-status' não encontrado -- crie esse canal manualmente no Discord com esse nome exato.", ephemeral=True
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


def _parse_data_hora(data: str, hora: str) -> datetime:
    partes_data = data.strip().split("/")
    if len(partes_data) not in (2, 3):
        raise ValueError("data")
    dia, mes = int(partes_data[0]), int(partes_data[1])
    ano = int(partes_data[2]) if len(partes_data) == 3 else datetime.now(FUSO_HORARIO).year
    h, m = (hora.strip().split(":") + ["0"])[:2]
    return datetime(ano, mes, dia, int(h), int(m), tzinfo=FUSO_HORARIO)


@tree.command(name="instancia", description="Anuncia uma instância/atividade e abre confirmação de presença.")
@app_commands.describe(
    nome="Nome da instância/atividade",
    data="Data (DD/MM ou DD/MM/AAAA -- assume o ano atual se omitido)",
    hora="Horário, 24h (ex: 20:00)",
    vagas="Número de vagas, se houver limite -- opcional",
    obs="Observações extras -- opcional",
    mencionar="Quem chamar no aviso (padrão: @everyone)",
)
@app_commands.choices(mencionar=MENCIONAR_CHOICES)
@permissao_ou_excecao("instancia", manage_messages=True)
async def instancia_command(
    interaction: discord.Interaction,
    nome: str,
    data: str,
    hora: str,
    vagas: int = None,
    obs: str = None,
    mencionar: app_commands.Choice[str] = None,
):
    channel = discord.utils.get(interaction.guild.text_channels, name="anuncio-de-instancias")
    if channel is None:
        await interaction.response.send_message(
            "Canal 'anuncio-de-instancias' não encontrado -- crie esse canal manualmente no Discord com esse nome exato.", ephemeral=True
        )
        return

    try:
        agendado = _parse_data_hora(data, hora)
    except (ValueError, IndexError):
        await interaction.response.send_message(
            "Não entendi a data/hora. Use `data: DD/MM` (ou `DD/MM/AAAA`) e `hora: HH:MM`.", ephemeral=True
        )
        return

    unix_agendado = int(agendado.timestamp())
    unix_prazo = int((agendado + timedelta(minutes=INSTANCIA_PRAZO_MINUTOS)).timestamp())

    descricao = f"**Quando:** <t:{unix_agendado}:F> (<t:{unix_agendado}:R>)"
    if vagas is not None:
        descricao += f"\n**Vagas:** {vagas}"
    if obs:
        descricao += f"\n{obs}"
    descricao += (
        f"\n\n*Organizado por {interaction.user.mention} — respostas encerram "
        f"{INSTANCIA_PRAZO_MINUTOS}min após o horário marcado*"
    )

    embed = discord.Embed(title=f"🗡️ Instância: {nome}", description=descricao, color=discord.Color.blurple())
    embed.add_field(name="✅ Vou (0)", value="-", inline=True)
    embed.add_field(name="❌ Não vou (0)", value="-", inline=True)
    embed.add_field(name="🤔 Talvez (0)", value="-", inline=True)
    embed.set_footer(text=f"{INSTANCIA_MARKER}|{json.dumps({'prazo': unix_prazo})}")

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
@permissao_ou_excecao("cronograma", manage_messages=True)
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
            "Canal 'anuncio-de-instancias' não encontrado -- crie esse canal manualmente no Discord com esse nome exato.", ephemeral=True
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
@permissao_ou_excecao("comunicado", manage_messages=True)
async def comunicado_command(
    interaction: discord.Interaction,
    imagem: discord.Attachment = None,
    mencionar: app_commands.Choice[str] = None,
):
    channel = discord.utils.get(interaction.guild.text_channels, name="comunicados-da-guilda")
    if channel is None:
        await interaction.response.send_message(
            "Canal 'comunicados-da-guilda' não encontrado -- crie esse canal manualmente no Discord com esse nome exato.", ephemeral=True
        )
        return

    imagem_url = imagem.url if imagem else None
    await interaction.response.send_modal(
        ComunicadoModal(channel, imagem_url, _conteudo_mencao(mencionar))
    )


@tree.command(name="permissao", description="Dá ou tira acesso extra a um comando, pra uma pessoa ou cargo específico.")
@app_commands.describe(
    acao="Adicionar ou remover acesso",
    comando="Qual comando",
    alvo="Pessoa ou cargo que vai ganhar/perder o acesso extra",
)
@app_commands.choices(
    acao=[
        app_commands.Choice(name="Adicionar", value="add"),
        app_commands.Choice(name="Remover", value="remove"),
    ],
    comando=[app_commands.Choice(name=c, value=c) for c in COMANDOS_GERENCIAVEIS],
)
@permissao_ou_excecao("permissao", manage_messages=True)
async def permissao_command(
    interaction: discord.Interaction,
    acao: app_commands.Choice[str],
    comando: app_commands.Choice[str],
    alvo: discord.Member | discord.Role,
):
    dados = _permissoes_extra.setdefault(comando.value, {"users": set(), "roles": set()})
    chave = "roles" if isinstance(alvo, discord.Role) else "users"

    if acao.value == "add":
        dados[chave].add(alvo.id)
        verbo = "ganhou acesso extra a"
    else:
        dados[chave].discard(alvo.id)
        verbo = "perdeu o acesso extra a"

    await _salvar_permissoes_extra(interaction.guild)
    await interaction.response.send_message(
        f"{alvo.mention} agora {verbo} `/{comando.value}`. ✅\n"
        "-# Isso é além do acesso padrão (Moderação+/Liderança) -- não tira permissão de "
        "quem já tinha pelo cargo normal.",
        ephemeral=True,
    )


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, (app_commands.MissingPermissions, app_commands.CheckFailure)):
        msg = "Você não tem permissão pra usar esse comando."
    else:
        log.exception("Erro não tratado num comando de barra.", exc_info=error)
        msg = "Deu um erro inesperado rodando esse comando. Chama a Liderança."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except discord.HTTPException:
        pass


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
