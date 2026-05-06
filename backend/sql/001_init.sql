create extension if not exists vector;

create table if not exists source_records (
    id bigserial primary key,
    source_type text not null check (source_type in ('file', 'url', 'manual')),
    file_name text,
    file_type text,
    source_url text,
    storage_path text,
    raw_html text,
    raw_text text,
    parse_status text not null default 'pending',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists parsed_documents (
    id bigserial primary key,
    source_record_id bigint references source_records(id) on delete set null,
    title text not null,
    document_type text,
    province text,
    city text,
    publish_date date,
    effective_date date,
    clean_text text,
    parse_confidence numeric(5, 4),
    created_at timestamptz not null default now()
);

create table if not exists procurement_projects (
    id bigserial primary key,
    project_name text not null,
    province text,
    alliance_name text,
    batch_no text,
    publish_date date,
    effective_date date,
    organization text,
    status text,
    created_at timestamptz not null default now()
);

create table if not exists products (
    id bigserial primary key,
    standard_name text not null,
    alias_name text,
    category_level_1 text,
    category_level_2 text,
    category_level_3 text,
    specification text,
    model text,
    unit text,
    registration_no text,
    created_at timestamptz not null default now()
);

create table if not exists enterprises (
    id bigserial primary key,
    standard_name text not null,
    alias_name text,
    enterprise_type text,
    created_at timestamptz not null default now()
);

create table if not exists bid_results (
    id bigserial primary key,
    project_id bigint references procurement_projects(id) on delete set null,
    product_id bigint references products(id) on delete set null,
    enterprise_id bigint references enterprises(id) on delete set null,
    source_record_id bigint references source_records(id) on delete set null,
    province text,
    winning_price numeric(18, 4),
    planned_volume numeric(18, 4),
    actual_volume numeric(18, 4),
    price_unit text,
    volume_unit text,
    publish_date date,
    execution_start_date date,
    execution_end_date date,
    created_at timestamptz not null default now()
);

create table if not exists document_chunks (
    id bigserial primary key,
    document_id bigint references parsed_documents(id) on delete cascade,
    chunk_text text not null,
    section_title text,
    chunk_index integer not null default 0,
    province text,
    publish_date date,
    effective_date date,
    policy_type text,
    embedding vector(1536),
    created_at timestamptz not null default now()
);

create table if not exists qa_logs (
    id bigserial primary key,
    question text not null,
    route_type text,
    sql_query text,
    answer text,
    sources jsonb,
    created_at timestamptz not null default now()
);

create index if not exists idx_source_records_source_type on source_records(source_type);
create index if not exists idx_parsed_documents_province on parsed_documents(province);
create index if not exists idx_parsed_documents_publish_date on parsed_documents(publish_date);
create index if not exists idx_bid_results_province on bid_results(province);
create index if not exists idx_bid_results_publish_date on bid_results(publish_date);
create index if not exists idx_document_chunks_document_id on document_chunks(document_id);
create index if not exists idx_document_chunks_province on document_chunks(province);
