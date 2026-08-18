# Configuração do Discord da comunidade

Este diretório contém tudo que define e aplica a estrutura do servidor:
cargos, canais (texto e voz), regras e o fluxo de boas-vindas de quem entra.

- `config.yaml` — a fonte da verdade. Edite este arquivo sempre que o escopo
  mudar (novo cargo, novo canal, texto de regra diferente etc).
- `bot.py` — processo que **precisa ficar rodando continuamente** (não é um
  script de "rodar uma vez"). Ele aplica o `config.yaml` no servidor e cuida
  do onboarding em tempo real (mensagem de boas-vindas, apelido, liberação
  de acesso ao confirmar as regras).

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

Na primeira execução ele cria toda a estrutura (cargos, categorias, canais)
e posta a mensagem de regras com o botão de confirmação em `#regras`.

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
   aparecer `Conectado como <nome-do-bot>` e depois `Pronto. Cargos
   ativos: ...`.

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

## 5. Atualizar quando o escopo mudar

**Redeploy e reinício do bot NUNCA mexem na estrutura do Discord por conta
própria.** Isso é de propósito: subir código novo (uma correção de bug, um
comando novo) não tem nada a ver com querer criar cargo/canal, e reiniciar
o processo sozinho não deveria arriscar tocar em nada que já existe. A
única forma de aplicar o `config.yaml` no servidor é rodar `/sync` — uma
ação deliberada, no Discord, quando você realmente quer isso.

Passo a passo:

1. Edite `config.yaml` com o que quer adicionar.
2. Redeploy normal (push no Railway) — o bot sobe, conecta, mas **não** mexe
   em cargo/canal nenhum sozinho.
3. Rode `/sync` no Discord. Ele mostra uma **prévia** do que pretende criar
   (só o que ainda não existe) e pede confirmação com um botão antes de
   criar qualquer coisa.
4. Confira a lista: se aparecer algo que você *sabia* que já existia, **não
   confirme** — cancele e investigue antes (pode ser sinal de um bug
   parecido com o que já aconteceu uma vez). Se a lista bater com o que
   você esperava, clique em **"Confirmar e criar"**.

**O sync só cria o que ainda não existe.** Cargo, categoria ou canal que
já existe no Discord (foi o bot que criou antes, ou foi feito à mão) fica
**100% intocado** -- cor, permissão, posição, categoria, tudo. O `/sync`
nunca edita nada que já está lá, só adiciona o que está no `config.yaml`
e ainda não tem correspondente no servidor. Também nunca deleta o que
saiu do arquivo -- isso continua sendo manual.

Na prática isso significa: depois que um cargo/canal é criado uma vez,
qualquer ajuste nele (nome, permissão, posição, cor...) só muda de novo
se você mudar **direto no Discord** -- editar o `config.yaml` e rodar
`/sync` de novo não vai reaplicar nada nele. O `config.yaml` só serve
pra descrever o que **ainda falta criar**.

### Por que às vezes aparece um canal "duplicado" depois do sync

O bot reconhece um canal já existente **pelo nome exato** que está no
`config.yaml`. Se alguém renomeia esse canal manualmente no Discord
(emoji, tradução, correção de digitação...), o próximo `/sync` não
reconhece mais aquele canal como "o mesmo" — e cria um **novo**, com o
nome original do config, do lado do que foi renomeado (já que agora o
sync nunca mexe em canal existente, esse é o único cenário em que algo
"extra" pode aparecer).

Pra saber exatamente o que aconteceu, olhe o log do deploy (Railway →
Deployments → View Logs) depois de um `/sync`. Cada linha deixa claro o
que houve com cada canal/categoria:

- `CRIADO (novo)` — não achou nada com esse nome exato e criou um novo.
  Se isso aparecer pra um canal que você *sabia* que já existia, é
  sinal de que ele foi renomeado.
- `já existia (id=..., em '...'), mantido sem alterações` — achou e não
  tocou em nada.
- No fim do sync, uma linha de **Resumo** soma tudo: quantas
  categorias/canais novos vs. quantos já existiam.

Se identificar um caso desses, o conserto é manual: apague o canal
duplicado (o novo, vazio) e, se quiser manter o nome customizado,
ajuste o `name:` dele no `config.yaml` pra bater com o que está no
Discord.

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
- Precisa existir uma mensagem de regras antes (`/sync` cria na
  primeira vez) -- se você apagar essa mensagem do Discord, rode
  `/sync` de novo pra recriar a partir do `config.yaml`, e depois
  `/regras` pra ajustar.

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

### Mudando apelido de quem também é Liderança

A mesma trava de hierarquia vale pra editar apelido de outra pessoa: só
funciona se o seu cargo mais alto for **maior** que o dela -- então
Liderança não consegue mudar o apelido de outra Liderança pela
interface normal, nem o Dono ajuda aqui, é regra fixa do Discord. Mover
o cargo do bot **não** resolve isso: essa restrição é entre as duas
pessoas humanas, o bot nem entra na conta quando é você editando
diretamente pela tela do Discord.

Use `/apelido` -- o bot muda por você, do mesmo jeito que o `/promover`:

```
/apelido membro: @Fulano nick: Novo Apelido
```

Deixar `nick` em branco remove o apelido customizado (volta ao nome
original da conta).

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

A visibilidade dos canais continua "em cascata" (quem é Moderação
enxerga tudo que Membros e Participantes veem), mas isso é resolvido
pelo bot na hora de montar as permissões do canal — cada canal libera
explicitamente todos os cargos daquele nível pra cima. Não depende da
pessoa acumular cargos.

Os "benefícios" de cada cargo (a lista do que cada um pode fazer/acessar)
só aparecem escritos no canal `#beneficios-membros`, visível apenas para
Membros+ — Participantes não têm como ver essa lista em lugar nenhum do
servidor, conforme pedido ("deve ser algo merecido, não almejado").

## Pontos que exigem confirmação sua

- **Canais de voz "Geral"**: sua mensagem original foi cortada em
  `03-Geral`. Criei só até o 03 — se o padrão era até o 05 (como
  Ragnarok/LoL), adicione `04-Geral` e `05-Geral` no `config.yaml` e rode
  `/sync`.
- **Canais "integrados com o LATAM"** (`patch-notes-br`,
  `anuncios-oficiais`): o bot só cria os canais vazios. A integração real
  (canal "seguindo" o canal oficial do servidor LATAM) é um recurso nativo
  do Discord que só um humano com acesso aos dois servidores consegue
  ativar: no canal de origem (no servidor LATAM), clicar em **"Seguir
  Canal"** e apontar para o canal criado aqui. Não é possível automatizar
  isso via bot.
- Os textos de regras, cargos e canais estão em `config.yaml` exatamente
  como você descreveu (com os ajustes pedidos: itens 6+10 unificados, item
  8 movido para o final, e a ressalva sobre ausência/presença confirmada).
  Revise antes do primeiro `python bot.py` — é só editar o YAML.
