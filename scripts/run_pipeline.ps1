$ErrorActionPreference = 'Stop'

# 1. Resolver el directorio raíz del proyecto
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location -Path $ProjectRoot

$LogDir = Join-Path $ProjectRoot "logs"
if (!(Test-Path -Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}
$LogFile = Join-Path $LogDir "scheduler.log"

$StartTime = Get-Date
$StartTimeStr = $StartTime.ToString("yyyy-MM-dd HH:mm:ss")
Add-Content -Path $LogFile -Value "[$StartTimeStr] START pipeline execution"

# 3. Comprobar requisitos
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$EnvFile = Join-Path $ProjectRoot ".env"

if (!(Test-Path -Path $VenvPython)) {
    Add-Content -Path $LogFile -Value "[$StartTimeStr] ERROR - El entorno virtual no existe."
    exit 2
}

if (!(Test-Path -Path $EnvFile)) {
    Add-Content -Path $LogFile -Value "[$StartTimeStr] ERROR - El archivo .env no existe."
    exit 2
}

# 4. Ejecutar orquestador Python
try {
    & $VenvPython "scripts\run_pipeline.py"
    $ExitCode = $LASTEXITCODE
} catch {
    $ExitCode = 1
}

# 6. Registrar métricas finales
$EndTime = Get-Date
$EndTimeStr = $EndTime.ToString("yyyy-MM-dd HH:mm:ss")
$DurationSeconds = [math]::Round(($EndTime - $StartTime).TotalSeconds, 2)

Add-Content -Path $LogFile -Value "[$EndTimeStr] END - ExitCode: $ExitCode - Duration: ${DurationSeconds}s"

# 5. Propagar código de salida
exit $ExitCode
