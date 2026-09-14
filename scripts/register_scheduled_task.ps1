[CmdletBinding(SupportsShouldProcess)]
param (
    [string]$TaskName = "Python ETL Automation",
    [string]$Time = "20:00",
    [string]$ProjectPath = "",
    [switch]$ConfirmRegistration
)

if ([string]::IsNullOrWhiteSpace($ProjectPath)) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $ProjectPath = Split-Path -Parent $ScriptDir
}

$ActionArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$ProjectPath\scripts\run_pipeline.ps1`""
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $ActionArgs -WorkingDirectory $ProjectPath
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable -DontStopOnIdleEnd
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

if ($ConfirmRegistration) {
    if ($PSCmdlet.ShouldProcess($TaskName, "Register Scheduled Task (Daily at $Time)")) {
        Write-Host "Registrando tarea programada: $TaskName"
        Register-ScheduledTask -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -TaskName $TaskName -Description "Ejecuta el pipeline ETL diariamente." -Force
        Write-Host "Tarea registrada con éxito."
    }
} else {
    Write-Host "MODO SIMULACION (Ejecuta con -ConfirmRegistration para aplicar realmente)"
    Write-Host "Configuracion que se aplicaria:"
    Write-Host "- Nombre de la Tarea: $TaskName"
    Write-Host "- Hora de ejecucion: $Time"
    Write-Host "- Directorio de Trabajo: $ProjectPath"
    Write-Host "- Comando: powershell.exe $ActionArgs"
    Write-Host "- Usuario: $env:USERNAME (Run only when user is logged on)"
    Write-Host ""
    Write-Host "Para registrar la tarea, ejecuta:"
    Write-Host ".\scripts\register_scheduled_task.ps1 -ConfirmRegistration"
    Write-Host ""
    Write-Host "Para eliminar manualmente la tarea en el futuro, ejecuta:"
    Write-Host "Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
}
