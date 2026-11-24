-- Run once in the Supabase SQL Editor for the Streaming Radar project.
-- Stores private command usage only; message text is never collected.
create table if not exists public.bot_events (
    id bigint generated always as identity primary key,
    telegram_id bigint not null,
    username text,
    first_name text,
    command text not null check (command in (
        '/start', '/stop', '/latest', '/random', '/info'
    )),
    created_at timestamptz not null default now()
);

create index if not exists bot_events_telegram_id_created_at_idx
    on public.bot_events (telegram_id, created_at desc);
create index if not exists bot_events_command_created_at_idx
    on public.bot_events (command, created_at desc);

alter table public.bot_events enable row level security;
grant insert, select on table public.bot_events to service_role;
grant usage, select on sequence public.bot_events_id_seq to service_role;

-- Summary by user, with the most recently observed Telegram name.
create or replace view public.bot_command_usage_by_user
with (security_invoker = true) as
with latest_profile as (
    select distinct on (telegram_id)
        telegram_id, username, first_name
    from public.bot_events
    order by telegram_id, created_at desc, id desc
), totals as (
    select
        telegram_id,
        count(*) as total_commands,
        count(*) filter (where command = '/latest') as latest_uses,
        count(*) filter (where command = '/random') as random_uses,
        count(*) filter (where command = '/info') as info_uses,
        count(*) filter (where command = '/start') as start_uses,
        count(*) filter (where command = '/stop') as stop_uses,
        max(created_at) as last_interaction_at
    from public.bot_events
    group by telegram_id
)
select totals.*, latest_profile.username, latest_profile.first_name
from totals
left join latest_profile using (telegram_id);

-- Summary by command for overall usage.
create or replace view public.bot_command_usage_totals
with (security_invoker = true) as
select
    command,
    count(*) as total_uses,
    count(distinct telegram_id) as unique_users,
    max(created_at) as last_used_at
from public.bot_events
group by command;

grant select on public.bot_command_usage_by_user to service_role;
grant select on public.bot_command_usage_totals to service_role;
