-- =============================================================
-- Inventario - schema do banco (Supabase / Postgres)
-- Cole este arquivo inteiro no SQL Editor do Supabase e rode.
-- =============================================================

-- ---------- profiles (1-1 com auth.users) ----------
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now()
);

-- Cria um profile automaticamente quando um usuario novo se cadastra
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data->>'display_name', split_part(new.email, '@', 1)));
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------- products ----------
create table if not exists public.products (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  sku text unique,
  unit text not null default 'un',
  current_stock numeric not null default 0,
  min_stock numeric not null default 0,
  created_by uuid references public.profiles(id),
  created_at timestamptz not null default now()
);

create index if not exists products_name_idx on public.products (name);

-- ---------- stock_movements ----------
create table if not exists public.stock_movements (
  id uuid primary key default gen_random_uuid(),
  product_id uuid not null references public.products(id) on delete cascade,
  type text not null check (type in ('entry','withdrawal')),
  quantity numeric not null check (quantity > 0),
  note text,
  performed_by uuid references public.profiles(id),
  performed_at timestamptz not null default now()
);

create index if not exists stock_movements_performed_at_idx on public.stock_movements (performed_at desc);
create index if not exists stock_movements_product_id_idx on public.stock_movements (product_id);

-- Trigger: ao inserir um movimento, atualiza current_stock automaticamente
create or replace function public.apply_stock_movement()
returns trigger
language plpgsql
as $$
begin
  if new.type = 'entry' then
    update public.products
      set current_stock = current_stock + new.quantity
      where id = new.product_id;
  elsif new.type = 'withdrawal' then
    update public.products
      set current_stock = current_stock - new.quantity
      where id = new.product_id;
  end if;
  return new;
end;
$$;

drop trigger if exists on_stock_movement_insert on public.stock_movements;
create trigger on_stock_movement_insert
  after insert on public.stock_movements
  for each row execute function public.apply_stock_movement();

-- ---------- Row Level Security ----------
alter table public.profiles enable row level security;
alter table public.products enable row level security;
alter table public.stock_movements enable row level security;

-- profiles: todos autenticados podem ver; só o próprio pode editar
drop policy if exists "profiles_select_all_authenticated" on public.profiles;
create policy "profiles_select_all_authenticated" on public.profiles
  for select to authenticated using (true);

drop policy if exists "profiles_update_self" on public.profiles;
create policy "profiles_update_self" on public.profiles
  for update to authenticated using (auth.uid() = id);

-- products: leitura para autenticados; insert para autenticados; update/delete só pelo criador
drop policy if exists "products_select_authenticated" on public.products;
create policy "products_select_authenticated" on public.products
  for select to authenticated using (true);

drop policy if exists "products_insert_authenticated" on public.products;
create policy "products_insert_authenticated" on public.products
  for insert to authenticated with check (auth.uid() = created_by);

drop policy if exists "products_update_creator" on public.products;
create policy "products_update_creator" on public.products
  for update to authenticated using (auth.uid() = created_by);

drop policy if exists "products_delete_creator" on public.products;
create policy "products_delete_creator" on public.products
  for delete to authenticated using (auth.uid() = created_by);

-- stock_movements: leitura para autenticados; insert para qualquer autenticado (registrando seu próprio uid)
drop policy if exists "movements_select_authenticated" on public.stock_movements;
create policy "movements_select_authenticated" on public.stock_movements
  for select to authenticated using (true);

drop policy if exists "movements_insert_authenticated" on public.stock_movements;
create policy "movements_insert_authenticated" on public.stock_movements
  for insert to authenticated with check (auth.uid() = performed_by);
