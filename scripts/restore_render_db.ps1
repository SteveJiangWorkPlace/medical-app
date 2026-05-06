param(
    [string]$DumpPath = ".\medical_rag.dump"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $DumpPath)) {
    throw "Dump file not found: $DumpPath"
}

$resolvedDump = Resolve-Path -LiteralPath $DumpPath
$dumpDirectory = Split-Path -Parent $resolvedDump
$dumpFileName = Split-Path -Leaf $resolvedDump

$secureUrl = Read-Host "Paste Render External Database URL" -AsSecureString
$databaseUrl = [System.Net.NetworkCredential]::new("", $secureUrl).Password
if ([string]::IsNullOrWhiteSpace($databaseUrl)) {
    throw "Render External Database URL is required"
}

if ($databaseUrl -notmatch "sslmode=") {
    $separator = "?"
    if ($databaseUrl.Contains("?")) {
        $separator = "&"
    }
    $databaseUrl = "$databaseUrl${separator}sslmode=require"
}

$envFile = New-TemporaryFile
try {
    "RENDER_DATABASE_URL=$databaseUrl" | Set-Content -LiteralPath $envFile -Encoding ASCII

    docker run --rm `
        --env-file $envFile `
        -v "${dumpDirectory}:/backup:ro" `
        postgres:17 `
        pg_restore `
        --clean `
        --if-exists `
        --no-owner `
        --no-acl `
        --dbname "`$RENDER_DATABASE_URL" `
        "/backup/$dumpFileName"

    docker run --rm `
        --env-file $envFile `
        postgres:17 `
        psql `
        "`$RENDER_DATABASE_URL" `
        -c "select exists(select 1 from pg_extension where extname='vector') as vector_enabled;"

    docker run --rm `
        --env-file $envFile `
        postgres:17 `
        psql `
        "`$RENDER_DATABASE_URL" `
        -c "select 'source_records' table_name, count(*) from source_records union all select 'parsed_documents', count(*) from parsed_documents union all select 'document_chunks', count(*) from document_chunks union all select 'embedded_chunks', count(*) from document_chunks where embedding is not null union all select 'enterprises', count(*) from enterprises union all select 'procurement_projects', count(*) from procurement_projects union all select 'products', count(*) from products union all select 'bid_results', count(*) from bid_results union all select 'device_price_catalogs', count(*) from device_price_catalogs order by table_name;"

    docker run --rm `
        --env-file $envFile `
        postgres:17 `
        psql `
        "`$RENDER_DATABASE_URL" `
        -c "select vector_dims(embedding) as dims, count(*) from document_chunks where embedding is not null group by vector_dims(embedding);"
}
finally {
    if (Test-Path -LiteralPath $envFile) {
        Remove-Item -LiteralPath $envFile -Force
    }
}
