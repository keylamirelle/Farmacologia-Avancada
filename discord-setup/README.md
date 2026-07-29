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

Edite `config.yaml` e depois:

- Rode `/sync` no próprio Discord (comando de barra, só admins) — aplica na
  hora, sem precisar reiniciar o bot; **ou**
- Reinicie o processo `bot.py` — ele sincroniza automaticamente ao subir.

O sync nunca deleta canais/cargos que saíram do arquivo — ele só cria e
atualiza o que está descrito. Se remover algo do `config.yaml`, apague
manualmente no Discord.

### Editando o resumo fixado de um canal (sem mexer no config)

O Discord não deixa ninguém editar mensagem de outra pessoa/bot pela
interface, nem quem é Administrador — então o texto fixado no topo de cada
canal (o `resumo` do `config.yaml`) só é aplicado **uma vez**, na criação do
canal. Depois disso, editar é feito com o comando `/resumo`, direto no
canal que você quer mudar:

```
/resumo texto: <novo texto> imagem: <opcional, anexe uma imagem>
```

- Disponível pra quem tem permissão de **Moderação+** (ou Liderança).
- Rodar sem `texto` só troca a imagem, mantendo o texto atual.
- Rodar sem `imagem` mantém a imagem atual (se tiver).

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
