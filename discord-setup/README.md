# Configuração do Discord da comunidade

Este diretório contém o bot que dá os comandos utilitários (edição de
conteúdo, avisos, promoção de cargo) e o fluxo de boas-vindas/regras de
quem entra no servidor.

**O bot não cria nem edita cargos, categorias ou canais.** Toda a estrutura
do servidor (cargos "Participantes/Membros/Moderação/Liderança", categorias,
canais de texto e voz) é montada **manualmente no Discord**, com os nomes
exatos que os comandos esperam (ver seção "Cargos e canais que o bot
espera" mais abaixo). Isso é de propósito -- já tivemos um incidente em que
lógica automática de criação/reconciliação de estrutura recriou canais que
já existiam, perdendo mensagens. Não vale o risco.

- `config.yaml` — guarda só o que os comandos realmente usam: o ID do
  servidor, o fluxo de boas-vindas (onboarding) e o texto-base das regras
  (editável depois via `/regras`, sem precisar mexer aqui).
- `bot.py` — processo que **precisa ficar rodando continuamente** (não é um
  script de "rodar uma vez"). Ele cuida dos comandos, do onboarding em
  tempo real (mensagem de boas-vindas, apelido, liberação de acesso ao
  confirmar as regras) e posta a mensagem de regras em `#regras` (só se
  ela ainda não existir).

## 1. Criar o bot no Discord

1. Acesse https://discord.com/developers/applications → **New Application**.
2. Na aba **Bot**, clique em **Reset Token** para gerar o token (ele só
   aparece uma vez — copie e guarde).
3. Ainda na aba **Bot**, em **Privileged Gateway Intents**, ative:
   - **Server Members Intent** (necessário para detectar quem entrou)
   - **Message Content Intent** (necessário para ler a resposta da DM com
     nick/classe)
4. Em **OAuth2 → URL Generator**: marque o escopo `bot`, e nas permissões
   marque pelo menos `Manage Roles`, `Manage Channels`, `Manage Nicknames`,
   `Kick Members`, `Moderate Members`, `Send Messages`, `Embed Links`,
   `View Channels`, `Mention @everyone, @here and All Roles` (necessário
   pro `/xprate` conseguir avisar o cargo Participantes). Abra o link
   gerado e adicione o bot ao seu servidor.
5. **Importante**: depois de adicionar, vá em *Configurações do Servidor →
   Cargos* e arraste o cargo do bot para **acima** do cargo "Liderança".
   Sem isso o bot não consegue gerenciar os cargos abaixo dele.
   - Se o bot já estava no servidor antes dessa permissão de menção
     existir, não precisa reconvidar: vá em *Configurações do Servidor →
     Cargos → (cargo do bot)* e ative manualmente **"Mencionar
     @everyone, @here e Todos os Cargos"**.

## 2. Configurar o projeto

```bash
cd discord-setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edite `.env` e preencha `DISCORD_BOT_TOKEN` e `DISCORD_GUILD_ID` (ID do seu
servidor — ative o "Modo desenvolvedor" em Configurações do Discord →
Avançado, depois botão direito no servidor → Copiar ID).

## 3. Rodar localmente (teste)

```bash
python bot.py
```

**Antes de rodar**, crie manualmente no Discord os cargos e canais que os
comandos esperam (ver seção "Cargos e canais que o bot espera" mais
abaixo) -- o bot não cria nada disso sozinho. Na primeira execução ele só
posta a mensagem de regras com o botão de confirmação em `#regras` (se
esse canal já existir e a mensagem ainda não tiver sido criada).

O processo **precisa continuar rodando** para o onboarding funcionar (DM de
boas-vindas, apelido automático, liberação de acesso). Rodar `python bot.py`
direto no seu terminal só funciona enquanto o terminal estiver aberto —
serve pra testar, não pra produção.

## 4. Hospedagem definitiva (produção)

Pra rodar 24/7 de verdade, escolha uma opção:

### Opção recomendada: Railway (gratuito p/ uso leve, sem cartão pra começar)

1. Suba este repositório no GitHub (ou use o que já está aqui).
2. Em https://railway.app → **New Project → Deploy from GitHub repo** →
   selecione o repositório.
3. Em **Settings → Root Directory**, aponte para `discord-setup`.
4. Railway detecta o `Procfile` automaticamente e sobe o processo `worker:
   python bot.py`. Se pedir, defina o **Start Command** manualmente como
   `python bot.py`.
5. Em **Settings → Deploy**, garanta que o **Builder** instala
   `requirements.txt` (padrão do Railway com Nixpacks já faz isso
   sozinho).
6. Em **Variables**, adicione `DISCORD_BOT_TOKEN` e `DISCORD_GUILD_ID`
   (os mesmos valores do seu `.env` local — **não** suba o `.env` pro
   GitHub, ele já está no `.gitignore`).
7. Deploy. Acompanhe os logs em **Deployments → View Logs** — deve
   aparecer `Conectado como <nome-do-bot>` e depois `Pronto -- conectado
   em '<nome-do-servidor>'.`.

Esse serviço fica em **worker**, não **web** — não precisa expor porta
HTTP nenhuma, é só o processo do bot conectado ao Discord.

### Alternativa: VPS / PC próprio sempre ligado

```bash
# dentro de discord-setup/, com o venv já criado
nohup python bot.py > bot.log 2>&1 &
```

Ou, melhor, como serviço do systemd (Linux) pra reiniciar sozinho se cair:

```ini
# /etc/systemd/system/discord-comunidade.service
[Unit]
Description=Bot Discord da comunidade
After=network.target

[Service]
WorkingDirectory=/caminho/para/discord-setup
ExecStart=/caminho/para/discord-setup/.venv/bin/python bot.py
Restart=always
EnvironmentFile=/caminho/para/discord-setup/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now discord-comunidade
```

## 5. Cargos e canais que o bot espera

O bot procura cargos e canais **pelo nome exato**. Crie-os manualmente no
Discord antes de usar os comandos correspondentes -- se o nome não bater
exatamente, o comando avisa que não encontrou, em vez de criar algo
sozinho.

**Cargos** (usados por `/promover`; `Participantes` também é o cargo
liberado ao confirmar as regras):

- `Participantes`, `Membros`, `Moderação`, `Liderança`

**Canais de texto:**

- `regras` — onde a mensagem de regras é postada (o bot cria só a
  *mensagem*, o canal em si precisa já existir)
- `boas-vindas` — usado como aviso alternativo se a DM de boas-vindas falhar
- `comunicacao-lideranca` — o `/permissao` guarda o estado interno dele aqui
- `xp-drop-status` — usado pelo `/xprate`
- `anuncio-de-instancias` — usado pelo `/instancia` e `/cronograma`
- `comunicados-da-guilda` — usado pelo `/comunicado`

Qualquer outro canal/categoria (Comércio, LATAM, salas de voz etc.) é só
organização visual sua -- o bot não interage com eles, então o nome não
importa pra ele funcionar.

Se um novo comando no futuro precisar de outro canal, eu aviso qual nome
exato criar antes de subir o código.

### Editando as regras (sem mexer no config)

Assim como o resumo dos canais, o texto de `#regras` só é aplicado a
partir do `config.yaml` **uma vez**, na criação da mensagem. Depois
disso, editar é feito com `/regras`:

```
/regras
```

Abre um formulário com o texto atual já preenchido, dividido em duas
partes (o Discord limita o tamanho de um campo de texto de formulário
a 4000 caracteres, e as regras passam disso). Edite à vontade, com
quebra de linha normal, e envie -- o bot atualiza a mensagem existente
sem mexer no botão "Li e concordo com as regras", que continua
funcionando igual.

- Disponível pra quem tem permissão de **Moderação+** (ou Liderança).
- Se o texto ficar grande demais pro Discord aceitar (limite de 6000
  caracteres somados em todos os embeds da mensagem), o bot avisa em
  vez de travar -- é só encurtar um pouco e tentar de novo.
- Precisa existir uma mensagem de regras antes (o bot cria sozinho, a
  partir do `config.yaml`, na primeira vez que conecta -- desde que o
  canal `#regras` já exista). Se você apagar essa mensagem do Discord,
  reinicie o bot pra ele recriar, e depois use `/regras` pra ajustar.

**Se você já usou `/resumo` em `#regras` por engano** (ele funciona em
qualquer canal de texto, não só nos que têm resumo configurado): isso
criou uma mensagem separada, sem o botão de confirmação, e que não é
mostrada pra quem ainda não confirmou as regras. Copie o texto que
você escreveu lá, cole no formulário do `/regras` (ou na primeira
parte dele, se for curto), e depois apague manualmente a mensagem
solta que o `/resumo` criou.

### Editando o resumo fixado de um canal (sem mexer no config)

O Discord não deixa ninguém editar mensagem de outra pessoa/bot pela
interface, nem quem é Administrador — então o texto fixado no topo de cada
canal (o `resumo` do `config.yaml`) só é aplicado **uma vez**, na criação do
canal. Depois disso, editar é feito com o comando `/resumo`, direto no
canal que você quer mudar:

```
/resumo imagem: <opcional, anexe uma imagem>
```

Isso abre um **formulário** (modal) com um campo de texto grande pra você
escrever o resumo — nesse campo sim dá pra quebrar linha normalmente
(Enter/Shift+Enter funciona, diferente dos campos de comando de barra
comuns). Se já existir um resumo, o formulário já abre com o texto atual
preenchido, pronto pra editar.

- Disponível pra quem tem permissão de **Moderação+** (ou Liderança).
- `imagem` continua sendo escolhida no comando (antes de abrir o
  formulário) — Discord não permite anexar arquivo dentro de um modal.
  Rodar sem `imagem` mantém a imagem atual, se tiver.

Depois que o `/resumo` for usado num canal, o `config.yaml` deixa de ter
efeito sobre aquela mensagem — ele só serve como rascunho inicial.

### Avisando as taxas de EXP/Drop/Penalidade vigentes

Essas taxas só aparecem dentro do próprio jogo (tela "Taxa de E X P /
Taxa de DROP / Pen. de Morte", cada uma como Normal + Bônus + Nidhogg) --
não existe site/API pra consultar de fora, então não dá pra automatizar.
É preciso alguém ver o valor no jogo e replicar no Discord. O comando
`/xprate` reproduz esse mesmo formato e guarda os valores atuais na
própria mensagem fixada -- então só precisa informar o que **mudou**,
o resto continua com o último valor registrado:

```
/xprate exp_nidhogg: 100
```

Todos os campos são opcionais e independentes:

- `exp_bonus`, `exp_nidhogg` — taxa de EXP
- `drop_bonus`, `drop_nidhogg` — taxa de DROP
- `penalidade_bonus`, `penalidade_nidhogg` — Penalidade de Morte
- `avisar` — manda um aviso novo no canal (padrão: sim; rode com
  `avisar: False` pra só atualizar a mensagem fixada, em silêncio)
- `mencionar` — quem chamar no aviso: `@everyone` (padrão), `@here` (só
  quem está online) ou o cargo Participantes

O "Normal" de cada taxa é sempre 100% (igual ao jogo) e o total é
calculado automaticamente (Normal + Bônus + Nidhogg). Disponível pra
quem tem permissão de **Moderação+** (ou Liderança). Atualiza sempre a
mesma mensagem fixada em `#status-xp-drop-penalidade`, sem acumular.

### Anunciando uma instância com confirmação de presença

```
/instancia nome: OGH data: 31/07 hora: 20:00 vagas: 12
```

Posta um aviso novo em `#anuncio-de-instancias` com três botões --
**✅ Vou**, **❌ Não vou**, **🤔 Talvez**. Ao clicar em qualquer um deles,
abre um formulário pra adicionar uma observação opcional (ex: "chego
15min atrasado"); o bot atualiza a lista de nomes (com a observação,
se tiver) em cada categoria direto na mensagem. Clicar em outro botão
depois **substitui** a resposta anterior -- só a mais recente conta.

- `data` aceita `DD/MM` (assume o ano atual) ou `DD/MM/AAAA`; `hora` é
  24h (`HH:MM`). O horário é mostrado no fuso de Brasília e o Discord
  já adapta pra cada pessoa ver na hora local dela.
- **As respostas fecham sozinhas 30 minutos depois do horário marcado** -- os
  botões somem da mensagem (fica só o registro de quem respondeu o
  quê) e o título ganha um 🔒. Isso é conferido tanto no clique do
  botão quanto por uma checagem automática a cada 5 minutos, então
  funciona mesmo que o bot reinicie no meio do caminho.
- `vagas` e `obs` são opcionais, e `mencionar` funciona igual ao
  `/xprate` (`@everyone` por padrão).
- Disponível pra **Moderação+**.

### Cronograma semanal de instâncias

Mensagem fixada em `#anuncio-de-instancias`, no mesmo esquema do
`/xprate`: cada chamada só precisa informar os dias que mudaram, o
resto mantém o valor anterior.

```
/cronograma sabado: War Room 19h domingo: OGH 20h
```

- Um parâmetro por dia da semana (`segunda` a `domingo`).
- `limpar: True` apaga o cronograma inteiro (ignora os outros campos).
- Disponível pra **Moderação+**.

### Comunicados da guilda

```
/comunicado imagem: <opcional> mencionar: <opcional>
```

Abre um formulário (modal) com campos pra **Título** (uma linha) e
**Texto** (área grande, com quebra de linha normal). Publica uma
mensagem nova em `#comunicados-da-guilda` (não fica editando, fica um
histórico), com imagem opcional e escolha de menção
(`@everyone`/`@here`/nenhuma, igual ao `/xprate`). A imagem e a escolha
de menção são pedidas no comando, antes de abrir o formulário (modal
não aceita anexo de arquivo). Disponível pra **Moderação+**.

### Promovendo alguém (inclusive a Liderança)

O Discord tem uma trava rígida: **ninguém** consegue atribuir manualmente,
pela interface, um cargo que esteja na mesma posição ou acima do próprio
cargo mais alto -- nem quem tem Administrator. Só o Dono real da conta do
servidor escapa disso. Ou seja: quem só tem o cargo Liderança não
consegue dar Liderança pra outra pessoa arrastando na tela de membros.

Use `/promover` em vez disso -- o bot faz a atribuição por você, porque o
cargo dele está posicionado acima de todos:

```
/promover membro: @Fulano cargo: Liderança
```

- Precisa ter **Administrator** (ou seja, já ser Liderança) pra chamar.
- Cada pessoa tem só **um** dos quatro cargos por vez -- o comando **troca**:
  remove qualquer um dos outros três que a pessoa já tinha e dá só o novo.
  Não acumula.

## Como funciona o fluxo de entrada

1. Pessoa entra no servidor → só enxerga a categoria **ENTRADA**
   (`#boas-vindas`, `#regras`) — nada mais, porque todo o resto exige o
   cargo "Participantes".
2. O bot manda uma **DM** perguntando nick e classe principal
   (`Nick, Classe`).
3. Ao responder, o bot ajusta o apelido dela no servidor
   (`[Classe] Nick`) e manda o próximo passo por DM: ir em `#regras`.
4. Em `#regras` ela lê o texto e clica em **"Li e concordo com as
   regras"** → o bot concede o cargo **Participantes**, que libera o
   resto dos canais.
5. Cargos acima de Participantes (Membros, Moderação, Liderança) são
   **atribuídos manualmente** pela liderança, usando `/promover` — não há
   critério automático definido no escopo atual.

Caso a pessoa tenha DMs fechadas para membros do servidor, o bot avisa em
`#boas-vindas` pedindo que ela abra as DMs e mande uma mensagem para ele
tentar de novo.

## Cargos: um por pessoa, visibilidade em cascata

Cada pessoa tem **um só** dos quatro cargos por vez (Participantes,
Membros, Moderação ou Liderança) — trocar de cargo é troca mesmo, não
soma. `/promover` já cuida disso: tira o cargo antigo e dá o novo.

A visibilidade dos canais (quem vê o quê) é configurada **manualmente no
Discord**, nas permissões de cada categoria/canal -- o bot não mexe nisso.
Pra manter a visibilidade "em cascata" (quem é Moderação enxerga tudo que
Membros e Participantes veem), configure a permissão de cada canal
liberando explicitamente todos os cargos daquele nível pra cima, já que
`/promover` nunca deixa a pessoa acumular mais de um cargo.

Os "benefícios" de cada cargo (a lista do que cada um pode fazer/acessar)
devem ficar escritos só num canal visível pra Membros+ (ex:
`#beneficios-membros`), configurado manualmente pra Participantes não
conseguirem ver, conforme pedido ("deve ser algo merecido, não
almejado").

## Texto das regras

O texto-base das 13 regras (com os ajustes já aplicados: itens 6+10
unificados, item 8 movido para o final, e a ressalva sobre
ausência/presença confirmada) mora em `config.yaml`, seção `rules:`. Ele
só serve de rascunho inicial -- depois que a mensagem em `#regras` é
criada, ajustes futuros são feitos com `/regras` direto no Discord, não
editando esse arquivo.
