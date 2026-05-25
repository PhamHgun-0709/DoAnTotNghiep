#!/usr/bin/env pwsh
<#
.SYNOPSIS
Docker Compose Helper Script

.DESCRIPTION
Tiện ích để chạy docker compose từ thư mục root project

.EXAMPLE
./docker-up.ps1
./docker-up.ps1 -Action "down"
./docker-up.ps1 -Action "logs"
#>

param(
    [ValidateSet("up", "down", "ps", "logs", "build", "restart")]
    [string]$Action = "up",
    [switch]$Detach = $true,
    [string]$Service = ""
)

$dockerComposePath = "infra/docker/docker-compose.yml"
$projectRoot = $PSScriptRoot

# Kiểm tra file
if (-not (Test-Path $dockerComposePath)) {
    Write-Host "[ERROR] Khong tim thay: $dockerComposePath" -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Docker Compose Helper" -ForegroundColor Cyan
Write-Host "[INFO] Thu muc: $(Get-Location)" -ForegroundColor Gray

switch ($Action) {
    "up" {
        Write-Host "[INFO] Khoi dong services..." -ForegroundColor Green
        if ($Detach) {
            docker compose -f $dockerComposePath up -d
        } else {
            docker compose -f $dockerComposePath up
        }
    }
    "down" {
        Write-Host "[INFO] Dung services..." -ForegroundColor Yellow
        docker compose -f $dockerComposePath down
    }
    "ps" {
        Write-Host "[INFO] Trang thai services:" -ForegroundColor Green
        docker compose -f $dockerComposePath ps
    }
    "logs" {
        Write-Host "[INFO] Logs:" -ForegroundColor Green
        if ($Service) {
            docker compose -f $dockerComposePath logs -f $Service
        } else {
            docker compose -f $dockerComposePath logs -f
        }
    }
    "build" {
        Write-Host "[INFO] Build images..." -ForegroundColor Green
        docker compose -f $dockerComposePath build --no-cache
    }
    "restart" {
        Write-Host "[INFO] Restart services..." -ForegroundColor Green
        docker compose -f $dockerComposePath restart
    }
}

Write-Host "[OK] Xong!" -ForegroundColor Green
