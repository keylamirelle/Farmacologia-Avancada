# Inventario - Protótipo

App mobile (iOS + Android) para gerenciamento simples de estoque, com cadastro de
produtos, registro de entradas e retiradas e histórico diário. Construído com
**Expo + React Native + TypeScript** no frontend e **Supabase** (Postgres +
Auth) no backend.

Este é um protótipo para validar o conceito com uma equipe pequena (2–10
pessoas). A equipe testa direto pelo **Expo Go** escaneando um QR Code, sem
precisar publicar nas lojas.

---

## 1. O que você precisa antes de começar

- **Node.js 20+** ([download](https://nodejs.org)) e `npm` no computador onde
  o servidor de desenvolvimento vai rodar.
- Uma conta gratuita no **[Supabase](https://supabase.com)**.
- **Expo Go** instalado nos celulares da equipe que vai testar:
  - [Android (Play Store)](https://play.google.com/store/apps/details?id=host.exp.exponent)
  - [iOS (App Store)](https://apps.apple.com/app/expo-go/id982107779)

---

## 2. Configurar o Supabase

1. Em https://supabase.com, crie um novo projeto (escolha região mais próxima e
   defina uma senha do banco — não vamos precisar dela depois).
2. Aguarde o projeto provisionar (~1-2 minutos).
3. Vá em **SQL Editor → New query**, abra o arquivo
   `supabase/schema.sql` deste repositório, cole o conteúdo inteiro e clique em
   **Run**. Isso cria as tabelas, triggers e políticas de segurança.
4. (Opcional, mas recomendado para protótipo) Em **Authentication → Providers →
   Email**, desligue *Confirm email* para que os usuários consigam entrar
   imediatamente após o cadastro.
5. Em **Project Settings → API**, copie:
   - **Project URL**
   - **anon public** key
6. (Opcional) Crie alguns usuários de teste em **Authentication → Users → Add
   user** (email + senha), ou deixe que cada pessoa se cadastre pelo próprio
   app.

---

## 3. Configurar o projeto local

```bash
git clone https://github.com/keylamirelle/farmacologia-avancada.git
cd farmacologia-avancada
git checkout claude/inventory-management-app-d52f8
npm install
cp .env.example .env
```

Edite o `.env` e cole as duas chaves do Supabase:

```
EXPO_PUBLIC_SUPABASE_URL=https://SEU-PROJETO.supabase.co
EXPO_PUBLIC_SUPABASE_ANON_KEY=eyJh...
```

---

## 4. Rodar para a equipe testar

```bash
npx expo start --tunnel
```

O `--tunnel` faz com que celulares em redes diferentes da sua também consigam
conectar (não é necessário estar no mesmo Wi-Fi). Vai aparecer um **QR Code**
no terminal e no navegador.

Cada pessoa da equipe:

1. Abre o **Expo Go** no celular
2. Escaneia o QR Code (Android: dentro do próprio app; iOS: pela câmera)
3. O app carrega → tela de Login
4. Cadastra-se com email + senha (ou usa um usuário que você criou no Supabase)
5. Pronto — cadastrar produtos, registrar entradas/retiradas, ver histórico

---

## 5. Fluxo do app

- **Aba Produtos**: lista todos os produtos com busca. Item fica com selo
  *"estoque baixo"* quando `estoque atual ≤ estoque mínimo`. Botões rápidos
  para criar produto, registrar entrada ou retirada.
- **Aba Histórico**: movimentações registradas hoje, com nome de quem fez
  cada uma. Atualiza em tempo real (Supabase Realtime).
- **+ Novo produto**: nome, SKU (opcional), unidade, estoque mínimo.
- **Entrada**: aumenta o estoque do produto escolhido.
- **Retirada**: diminui o estoque (bloqueia se for maior que o disponível).

---

## 6. Estrutura do código

```
.
├── App.tsx                       Componente raiz
├── index.ts                      Entry point (registerRootComponent)
├── app.json                      Config do Expo
├── package.json
├── supabase/
│   └── schema.sql                Tabelas + triggers + RLS para colar no Supabase
└── src/
    ├── lib/
    │   ├── supabase.ts           Cliente Supabase com persistencia no AsyncStorage
    │   └── types.ts              Tipos Product, StockMovement, Profile
    ├── context/
    │   └── AuthContext.tsx       Provider de sessao + hook useAuth
    ├── navigation/
    │   ├── RootNavigator.tsx     Switch entre Auth e App stack
    │   └── AppTabs.tsx           Bottom tabs (Produtos | Historico)
    ├── screens/
    │   ├── LoginScreen.tsx
    │   ├── ProductsScreen.tsx
    │   ├── ProductFormScreen.tsx
    │   ├── EntryScreen.tsx       (usa MovementForm com type="entry")
    │   ├── WithdrawalScreen.tsx  (usa MovementForm com type="withdrawal")
    │   ├── MovementForm.tsx      Form compartilhado por entrada/retirada
    │   └── HistoryScreen.tsx
    ├── components/
    │   ├── ProductCard.tsx
    │   ├── MovementRow.tsx
    │   └── QuantityInput.tsx
    └── hooks/
        ├── useProducts.ts        Lista + realtime
        └── useMovements.ts       Movimentacoes do dia + realtime
```

---

## 7. Fora do escopo deste protótipo

(Dá para adicionar depois se a equipe validar a ideia)

- Leitor de código de barras / QR
- Relatórios exportáveis (CSV / PDF)
- Múltiplos depósitos / filiais
- Permissões por papel (admin vs operador)
- Sincronização offline
- Notificações push de estoque baixo
- Foto do produto
- Build standalone para Play Store / App Store (EAS Build)
- Testes automatizados

---

## 8. Problemas comuns

- **"EXPO_PUBLIC_SUPABASE_URL ausente"** → você esqueceu de criar o `.env` ou
  está rodando antes de salvar. Pare o servidor (Ctrl+C), salve o `.env` e
  rode `npx expo start --tunnel` de novo.
- **Login falha com "Email not confirmed"** → desative *Confirm email* nas
  configurações de Auth do Supabase (item 2.4 acima).
- **Retirada bloqueada** → o app não deixa retirar mais do que o estoque atual.
  Faça uma entrada primeiro.
- **QR Code não conecta** → use `--tunnel` em vez do modo LAN; se ainda
  falhar, verifique se o computador tem acesso à internet.
