# Controle de Materiais - Protótipo

App mobile (iOS + Android) para controle de **empréstimo/uso de materiais
que saem para escolas**. Você cadastra responsáveis, escolas e materiais,
e registra cada retirada (quem está levando o quê, para qual escola, em
que data). O dashboard mostra em tempo real o que está em uso, por quem
e onde.

Stack: **Expo + React Native + TypeScript** no frontend e **Supabase**
(Postgres + Realtime) no backend. **Modo kiosk: sem login** — qualquer
um que abrir o app pode registrar retiradas em nome de qualquer
responsável cadastrado.

---

## 1. O que você precisa antes de começar

- **Node.js 20+** ([download](https://nodejs.org)) e `npm` no computador onde
  o servidor de desenvolvimento vai rodar
- Uma conta gratuita no **[Supabase](https://supabase.com)**
- **Expo Go** instalado nos celulares da equipe:
  - [Android](https://play.google.com/store/apps/details?id=host.exp.exponent)
  - [iOS](https://apps.apple.com/app/expo-go/id982107779)

---

## 2. Configurar o Supabase (uma vez só)

1. Em https://supabase.com → **Start your project** → login com GitHub ou email
2. **New project** → nome (ex: `materiais`), gere uma senha do banco, região
   *South America (São Paulo)*, plano **Free**
3. Aguarde ~1-2 min o projeto subir
4. Menu lateral → **SQL Editor** → **+ New query**
5. Abra `supabase/schema.sql` deste repositório, copie tudo, cole no editor,
   clique **Run**. Deve aparecer *"Success. No rows returned"*
6. Menu lateral → **Project Settings** → **API**. Copie:
   - **Project URL**
   - **anon public** key

> Note que este protótipo está em **modo kiosk** (sem login). O schema
> desabilita Row Level Security para que o app funcione sem
> autenticação. Para uso real com dados sensíveis, será necessário
> reativar e adicionar Auth.

---

## 3. Configurar o projeto local

```bash
git clone https://github.com/keylamirelle/farmacologia-avancada.git
cd farmacologia-avancada
git checkout claude/inventory-management-app-d52f8
npm install
cp .env.example .env
```

Edite o `.env` com as duas chaves do Supabase:

```
EXPO_PUBLIC_SUPABASE_URL=https://SEU-PROJETO.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=eyJh...
```

---

## 4. Rodar para a equipe testar

```bash
npx expo start --tunnel
```

Aparece um QR Code no terminal e no navegador. Cada pessoa da equipe:

- **Android**: abre o Expo Go → **Scan QR code**
- **iPhone**: abre a **Câmera** → aponta para o QR → toca no banner

A primeira vez demora ~30s para carregar.

---

## 5. Fluxo do app

### 5.1) Cadastros (aba **C**)

Antes de fazer a primeira retirada, cadastre:

- **Pessoas (responsáveis)**: quem pode retirar materiais. Nome (obrigatório),
  função/cargo e telefone (opcionais).
- **Escolas**: para onde os materiais vão. Nome (obrigatório), cidade
  (opcional).
- **Materiais**: o que está disponível. Nome, unidade (`un`, `kg`, `cx`...),
  **quantidade total** e flag **"retorna após uso"**:
  - **Retorna** (ligado): emprestável. Ex.: jogos, livros, microscópio. O
    material fica *"em uso"* até alguém marcar como devolvido, depois volta ao
    disponível.
  - **Consumível** (desligado): sai e não volta. Ex.: papel, lapiseira. A
    retirada diminui o disponível permanentemente.

### 5.2) Registrar uma retirada (aba **R** → **+ Nova retirada**)

1. Escolhe **responsável** (lista cadastrada de pessoas)
2. Escolhe **escola**
3. Escolhe **material** (mostra quanto está disponível)
4. Digita a **quantidade**
5. (Opcional) Adiciona uma **observação**
6. Toca em **Registrar retirada**

A data/hora é gravada automaticamente. O material aparece imediatamente como
*"em uso"* no dashboard.

### 5.3) Marcar como devolvido (aba **R**)

Na lista de **Retiradas Ativas**, cada cartão de material retornável tem o
botão **"Marcar devolvido"**. Ao tocar, a quantidade volta ao disponível e a
retirada some das ativas (continua aparecendo no filtro **"Todas"** com data
de devolução).

### 5.4) Dashboard (aba **D**)

No topo: total de materiais, unidades em uso, retiradas ativas.

Três visões alternáveis:

- **Por material**: cada item mostra total / em uso / disponível.
- **Por pessoa**: agrupa retiradas ativas pela pessoa que retirou (você vê de
  uma vez tudo o que cada responsável está com).
- **Por escola**: agrupa retiradas ativas por escola (você vê o que cada
  escola tem no momento).

Tudo atualiza em tempo real via Supabase Realtime — se alguém em outro
celular registra uma retirada, aparece imediatamente nos outros aparelhos.

---

## 6. Estrutura do código

```
.
├── App.tsx                          Componente raiz
├── index.ts                         Entry point
├── app.json                         Config do Expo
├── package.json
├── supabase/
│   └── schema.sql                   Tabelas + view + grants para colar no Supabase
└── src/
    ├── lib/
    │   ├── supabase.ts              Cliente Supabase
    │   └── types.ts                 Person, School, Material, Withdrawal
    ├── navigation/
    │   ├── RootNavigator.tsx        Stack raiz
    │   └── AppTabs.tsx              Tabs: Dashboard | Retiradas | Cadastros
    ├── screens/
    │   ├── DashboardScreen.tsx      3 visoes (material/pessoa/escola)
    │   ├── WithdrawalsScreen.tsx    Lista ativa/hoje/todas com devolucao
    │   ├── NewWithdrawalScreen.tsx  Form de nova retirada
    │   ├── CadastrosScreen.tsx      Menu (pessoas | escolas | materiais)
    │   ├── PeopleListScreen.tsx
    │   ├── PersonFormScreen.tsx
    │   ├── SchoolsListScreen.tsx
    │   ├── SchoolFormScreen.tsx
    │   ├── MaterialsListScreen.tsx
    │   └── MaterialFormScreen.tsx
    ├── components/
    │   ├── MaterialSummaryCard.tsx
    │   ├── WithdrawalCard.tsx
    │   └── QuantityInput.tsx
    └── hooks/
        ├── usePeople.ts             Lista + realtime
        ├── useSchools.ts
        ├── useMaterials.ts          Inclui useMaterialStatus (view agregada)
        └── useWithdrawals.ts        Filter: active | today | all
```

---

## 7. Modelo de dados (resumo)

| Tabela        | Campos principais                                          |
| ------------- | ---------------------------------------------------------- |
| `people`      | `name`, `role`, `phone`, `active`                          |
| `schools`     | `name`, `city`, `active`                                   |
| `materials`   | `name`, `unit`, `total_quantity`, `returnable`             |
| `withdrawals` | `person_id`, `school_id`, `material_id`, `quantity`, `withdrawn_at`, `returned_at` (null = ativa) |

A view `material_status` calcula automaticamente:
- `in_use` (em uso agora): soma das retiradas ativas de materiais retornáveis
- `consumed` (consumido): soma das retiradas de materiais não-retornáveis
- `available` = `total_quantity - in_use - consumed`

---

## 8. Fora do escopo (protótipo)

(Dá para adicionar depois)

- Login / permissões por usuário
- Leitor de código de barras / QR para selecionar material
- Relatórios exportáveis (CSV, PDF)
- Devolução parcial (devolver só parte de uma retirada)
- Múltiplas unidades de medida por material
- Foto / anexo no cadastro
- Notificações para responsáveis com material há muito tempo
- Build standalone para Play Store / App Store
- Testes automatizados

---

## 9. Problemas comuns

- **"EXPO_PUBLIC_SUPABASE_URL ausente"** → falta criar/preencher o `.env`.
- **App abre mas as listas ficam vazias** → o SQL do schema não foi rodado, ou
  os grants para `anon` falharam. Reabra o `supabase/schema.sql` no SQL Editor
  e rode novamente.
- **"new row violates row-level security"** ao salvar → o `disable row level
  security` do schema não foi executado. Rode o schema todo de novo.
- **Não consigo selecionar um material em "Nova retirada"** → o material está
  com 0 disponível (todo em uso ou consumido). Aumente o `total_quantity` em
  Cadastros > Materiais.
- **QR Code não conecta** → use sempre `--tunnel`.
