-- =============================================================
-- Controle de Materiais (modelo de emprestimo / uso)
-- Cole este arquivo inteiro no SQL Editor do Supabase e rode.
-- =============================================================
--
-- Como o app funciona:
--   * Cadastra-se uma lista de PESSOAS (responsaveis), ESCOLAS e MATERIAIS.
--   * Quando alguem retira um material para levar a uma escola, cria-se
--     uma linha em "withdrawals" com (pessoa, escola, material, qtd).
--   * Se o material e "returnable" (volta apos uso), ele fica EM USO
--     ate alguem marcar returned_at = now(). Ai volta para "disponivel".
--   * Se o material NAO e "returnable" (consumivel), ele e contabilizado
--     como saido permanentemente (reduz o disponivel para sempre).
-- =============================================================

-- ---------- people (responsaveis) ----------
create table if not exists public.people (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  role text,
  phone text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists people_name_idx on public.people (name);

-- ---------- schools ----------
create table if not exists public.schools (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  city text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists schools_name_idx on public.schools (name);

-- ---------- materials ----------
create table if not exists public.materials (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  unit text not null default 'un',
  total_quantity numeric not null default 0,
  returnable boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists materials_name_idx on public.materials (name);

-- ---------- withdrawals (retiradas) ----------
create table if not exists public.withdrawals (
  id uuid primary key default gen_random_uuid(),
  person_id uuid not null references public.people(id),
  school_id uuid not null references public.schools(id),
  material_id uuid not null references public.materials(id),
  quantity numeric not null check (quantity > 0),
  note text,
  withdrawn_at timestamptz not null default now(),
  returned_at timestamptz
);

create index if not exists withdrawals_active_idx
  on public.withdrawals (material_id) where returned_at is null;
create index if not exists withdrawals_withdrawn_at_idx
  on public.withdrawals (withdrawn_at desc);
create index if not exists withdrawals_person_idx on public.withdrawals (person_id);
create index if not exists withdrawals_school_idx on public.withdrawals (school_id);

-- ---------- view: status agregado por material ----------
create or replace view public.material_status as
select
  m.id,
  m.name,
  m.unit,
  m.total_quantity,
  m.returnable,
  coalesce(sum(
    case when w.returned_at is null and m.returnable then w.quantity else 0 end
  ), 0) as in_use,
  coalesce(sum(
    case when not m.returnable then w.quantity else 0 end
  ), 0) as consumed,
  m.total_quantity - coalesce(sum(
    case
      when (w.returned_at is null and m.returnable) or not m.returnable then w.quantity
      else 0
    end
  ), 0) as available
from public.materials m
left join public.withdrawals w on w.material_id = m.id
group by m.id;

-- =============================================================
-- Modo kiosk: sem login, acesso anonimo permitido.
-- (Para um prototipo. Em producao, ative RLS e use auth.)
-- =============================================================
alter table public.people disable row level security;
alter table public.schools disable row level security;
alter table public.materials disable row level security;
alter table public.withdrawals disable row level security;

grant usage on schema public to anon;
grant select, insert, update, delete on public.people to anon;
grant select, insert, update, delete on public.schools to anon;
grant select, insert, update, delete on public.materials to anon;
grant select, insert, update, delete on public.withdrawals to anon;
grant select on public.material_status to anon;
