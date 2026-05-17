# Start SSH port forward: Windows localhost -> PostgreSQL on Linux server.
# Leave this window open while developing. Run Flask in a second terminal.
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$EnvFile = Join-Path $ProjectRoot ".env"

if (-not (Test-Path $EnvFile)) {
    Write-Error "Missing .env in project root. Copy .env.example to .env and set SSH_TUNNEL_* values."
}

Get-Content $EnvFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -eq "" -or $line.StartsWith("#")) { return }
    $idx = $line.IndexOf("=")
    if ($idx -lt 1) { return }
    $name = $line.Substring(0, $idx).Trim()
    $value = $line.Substring($idx + 1).Trim().Trim("'", '"')
    Set-Item -Path "Env:$name" -Value $value
}

if (-not $env:SSH_TUNNEL_HOST) { Write-Error "Set SSH_TUNNEL_HOST in .env (Linux server hostname or IP)." }
if (-not $env:SSH_TUNNEL_USER) { Write-Error "Set SSH_TUNNEL_USER in .env (your SSH login on the server)." }

$LocalPort = if ($env:SSH_TUNNEL_LOCAL_PORT) { $env:SSH_TUNNEL_LOCAL_PORT } else { "5432" }
$RemoteHost = if ($env:SSH_TUNNEL_REMOTE_HOST) { $env:SSH_TUNNEL_REMOTE_HOST } else { "127.0.0.1" }
$RemotePort = if ($env:SSH_TUNNEL_REMOTE_PORT) { $env:SSH_TUNNEL_REMOTE_PORT } else { "5432" }

$Target = "$($env:SSH_TUNNEL_USER)@$($env:SSH_TUNNEL_HOST)"
$Forward = "${LocalPort}:${RemoteHost}:${RemotePort}"

Write-Host "SSH tunnel: localhost:$LocalPort -> $Target ($RemoteHost`:$RemotePort)"
Write-Host "Press Ctrl+C to stop. Keep this window open while using the app."
Write-Host ""

ssh -N -L $Forward $Target
