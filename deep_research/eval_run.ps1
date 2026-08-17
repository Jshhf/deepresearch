# DeepResearch eval launcher
# Usage:
#   .\eval_run.ps1                          interactive menu
#   .\eval_run.ps1 -Action internal -Limit 5
# Actions: internal, metrics, review, llm-judge, http, stress, rebuild, health, all

[CmdletBinding()]
param(
    [ValidateSet('internal', 'metrics', 'review', 'llm-judge', 'http', 'stress', 'rebuild', 'health', 'all')]
    [string]$Action = '',
    [int]$Limit = 5,
    [int]$Total = 10,
    [int]$Concurrency = 2,
    [string]$Query = 'AI Agent framework trend 2026',
    [string]$BaseUrl = 'http://localhost:8000',
    [string]$Queries = 'app/eval/sample_queries.jsonl'
)

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot
$env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
$ErrorActionPreference = 'Continue'

function Invoke-EvalAction {
    param([string]$Name)

    switch ($Name) {
        'internal' {
            Write-Host "==> internal eval (backend container) limit=$Limit"
            & docker compose --env-file .env.docker exec -T backend python app/eval/run_eval.py --queries $Queries --out output/eval_results --limit $Limit
            if ($LASTEXITCODE -ne 0) { throw 'internal eval failed' }
        }
        'metrics' {
            Write-Host '==> compute metrics'
            & python app/eval/compute_metrics.py --results-dir output/eval_results
            if ($LASTEXITCODE -ne 0) { throw 'compute metrics failed' }
        }
        'review' {
            Write-Host '==> generate review sheet'
            & python app/eval/judge_reports.py --results-dir output/eval_results --out output/eval_review.csv
            if ($LASTEXITCODE -ne 0) { throw 'generate review sheet failed' }
        }
        'llm-judge' {
            Write-Host '==> Qwen LLM judge (backend container)'
            & docker compose --env-file .env.docker exec -T backend python app/eval/judge_reports.py --results-dir output/eval_results --out output/eval_review.csv --llm-judge
            if ($LASTEXITCODE -ne 0) { throw 'llm judge failed' }
        }
        'http' {
            Write-Host "==> http black-box eval base=$BaseUrl limit=$Limit concurrency=$Concurrency"
            & python app/eval/run_http_eval.py --queries $Queries --base-url $BaseUrl --out output/eval_http --limit $Limit --concurrency $Concurrency
            if ($LASTEXITCODE -ne 0) { throw 'http eval failed' }
        }
        'stress' {
            Write-Host "==> stress test base=$BaseUrl total=$Total concurrency=$Concurrency"
            & python app/eval/stress_test.py --base-url $BaseUrl --query $Query --total $Total --concurrency $Concurrency --out output/eval_stress.json
            if ($LASTEXITCODE -ne 0) { throw 'stress test failed' }
        }
        'rebuild' {
            Write-Host '==> rebuild backend'
            & docker compose --env-file .env.docker up -d --build backend
            if ($LASTEXITCODE -ne 0) { throw 'rebuild backend failed' }
        }
        'health' {
            Write-Host '==> container status'
            & docker compose --env-file .env.docker ps
            if ($LASTEXITCODE -ne 0) { throw 'docker compose ps failed' }
        }
        'all' {
            Invoke-EvalAction 'internal'
            Invoke-EvalAction 'metrics'
            Invoke-EvalAction 'review'
        }
    }
}

if ($Action) {
    try {
        Invoke-EvalAction $Action
    } catch {
        Write-Error $_
        exit 1
    }
    exit 0
}

while ($true) {
    Write-Host ''
    Write-Host '======== DeepResearch Eval Launcher ========'
    Write-Host ' 1) internal eval (backend container)'
    Write-Host ' 2) compute metrics'
    Write-Host ' 3) generate review sheet'
    Write-Host ' 4) Qwen LLM judge (backend container)'
    Write-Host ' 5) HTTP black-box eval'
    Write-Host ' 6) stress test'
    Write-Host ' 7) rebuild backend'
    Write-Host ' 8) container status'
    Write-Host ' 0) exit'
    $choice = Read-Host 'choose number'
    try {
        switch ($choice) {
            '1' { Invoke-EvalAction 'internal' }
            '2' { Invoke-EvalAction 'metrics' }
            '3' { Invoke-EvalAction 'review' }
            '4' { Invoke-EvalAction 'llm-judge' }
            '5' { Invoke-EvalAction 'http' }
            '6' { Invoke-EvalAction 'stress' }
            '7' { Invoke-EvalAction 'rebuild' }
            '8' { Invoke-EvalAction 'health' }
            '0' { Write-Host 'bye'; exit 0 }
            default { Write-Host 'invalid choice' }
        }
    } catch {
        Write-Error $_
    }
}
