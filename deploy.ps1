# DeepResearch deployment driver (idempotent)
$ErrorActionPreference = 'Continue'

# Refresh PATH so docker is found even in a fresh shell
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')

$ProjectRoot = Join-Path $PSScriptRoot 'deep_research'
$LogFile     = Join-Path $PSScriptRoot 'deploy.log'
$EnvFile     = Join-Path $ProjectRoot '.env.docker'
$EnvExample  = Join-Path $ProjectRoot '.env.docker.example'

function Write-Log {
    param([string]$Message)
    $line = '[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
    Write-Output $line
}

function Set-EnvLine {
    param([string]$Content, [string]$Name, [string]$Value)
    $pattern = '(?m)^' + [regex]::Escape($Name) + '=.*$'
    $replacement = $Name + '=' + $Value.Replace('$', '$$')
    return [regex]::Replace($Content, $pattern, $replacement)
}

function Test-Http {
    param([string]$Uri)
    try {
        return Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 15
    } catch {
        return $null
    }
}

Set-Location $ProjectRoot

Write-Log '=== deploy.ps1 start ==='

# 1) .env.docker
if (-not (Test-Path $EnvFile)) {
    Copy-Item -LiteralPath $EnvExample -Destination $EnvFile
    Write-Log 'Created .env.docker from .env.docker.example'
}
$content = Get-Content -Raw -Encoding UTF8 $EnvFile
$m = [regex]::Match($content, '(?m)^DASHSCOPE_API_KEY=(.*)$')
$currentKey = if ($m.Success) { $m.Groups[1].Value.Trim() } else { '' }
$dash = ''
if ($currentKey -and $currentKey -ne 'sk-请填写你的Key') {
    $dash = $currentKey
    Write-Log 'DASHSCOPE_API_KEY preserved from .env.docker'
} elseif ($env:DASHSCOPE_API_KEY) {
    $dash = $env:DASHSCOPE_API_KEY.Trim()
    Write-Log 'DASHSCOPE_API_KEY set from session environment'
} else {
    Write-Log 'WARN DASHSCOPE_API_KEY missing; deployment continues but backend research will fail until key is added'
}
if ($dash) {
    $content = Set-EnvLine $content 'DASHSCOPE_API_KEY' $dash
}
$content = Set-EnvLine $content 'BOCHA_API_KEY' ''
[System.IO.File]::WriteAllText($EnvFile, $content, (New-Object System.Text.UTF8Encoding($false)))
Write-Log '.env.docker ready'

# 2) build + up
Write-Log 'Running: docker compose --env-file .env.docker up -d --build (5-15 min)'
& docker compose --env-file .env.docker up -d --build *>> $LogFile
$code = $LASTEXITCODE
if ($code -ne 0) {
    Write-Log "FAIL compose up exit=$code"
    exit 1
}
Write-Log 'compose up returned OK'

# 3) wait for services
$deadline = (Get-Date).AddMinutes(12)
$ready = $false
while ((Get-Date) -lt $deadline) {
    $rows = & docker compose --env-file .env.docker ps --format '{{.Service}}`t{{.State}}`t{{.Health}}' 2>$null
    $bad = $rows | Where-Object { $_ -match '\t(unhealthy|restarting|exited)\t' }
    if ($bad) {
        Write-Log ('FAIL container state: ' + ($bad -join ' | '))
        exit 1
    }
    $be = Test-Http 'http://localhost:8000/health'
    $fe = Test-Http 'http://localhost:8080'
    $states = ($rows | ForEach-Object { ($_ -split "`t")[0] + '=' + ($_ -split "`t")[2] }) -join ' '
    if ($rows -and $be -and $fe) {
        $ready = $true
        Write-Log ('All targets up. ' + $states)
        break
    }
    Write-Log ('waiting... ' + $states)
    Start-Sleep -Seconds 20
}
if (-not $ready) {
    Write-Log 'FAIL services did not become healthy in time'
    & docker compose --env-file .env.docker ps *>> $LogFile
    exit 1
}

# 4) health check summary
$summary = @()
function Add-Check {
    param([string]$Name, [string]$Result)
    $script:summary += ('{0}: {1}' -f $Name, $Result)
    Write-Log ('CHECK {0}: {1}' -f $Name, $Result)
}

$r = Test-Http 'http://localhost:8000/health'
if ($r -and $r.StatusCode -eq 200) { Add-Check 'backend /health' ($r.Content) } else { Add-Check 'backend /health' 'FAIL' }

$r = Test-Http 'http://localhost:8080'
if ($r) { Add-Check 'frontend 8080' ('HTTP ' + $r.StatusCode) } else { Add-Check 'frontend 8080' 'FAIL' }

$pg = & docker compose --env-file .env.docker exec -T postgres pg_isready -U deepresearch -d deepresearch 2>&1
Add-Check 'postgres' (($pg -join ' ').Trim())

$re = & docker compose --env-file .env.docker exec -T redis redis-cli -a deepresearch ping 2>&1
Add-Check 'redis' (($re -join ' ').Trim())

$mv = Test-Http 'http://localhost:9091/healthz'
if ($mv) { Add-Check 'milvus /healthz' ($mv.Content) } else { Add-Check 'milvus /healthz' 'FAIL' }

$et = & docker compose --env-file .env.docker exec -T etcd etcdctl endpoint health 2>&1
Add-Check 'etcd' (($et -join ' ').Trim())

$mi = Test-Http 'http://localhost:9000/minio/health/live'
if ($mi) { Add-Check 'minio health' ('HTTP ' + $mi.StatusCode) } else { Add-Check 'minio health' 'FAIL' }

# 5) optional ingest
$docsDir = Join-Path $ProjectRoot 'docs'
$docFiles = @()
if (Test-Path $docsDir) {
    $docFiles = Get-ChildItem -Path $docsDir -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -in '.md', '.txt', '.markdown' }
}
if ($docFiles.Count -gt 0) {
    Write-Log ("Docs found: {0}; running ingest..." -f $docFiles.Count)
    & docker compose --env-file .env.docker --profile ingest run --rm ingest 2>&1 | Tee-Object -FilePath $LogFile -Append
    $ingCode = $LASTEXITCODE
    Write-Log ("ingest exit=$ingCode")
    Add-Check 'ingest' ("exit=$ingCode")
} else {
    Add-Check 'ingest' 'skipped (no docs)'
}

Write-Log '=== deploy.ps1 done ==='
$summary | ForEach-Object { Write-Output $_ }
