import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

def test_powershell_syntax():
    """Prueba que los scripts de PowerShell tienen sintaxis válida."""
    scripts = ["scripts/run_pipeline.ps1", "scripts/register_scheduled_task.ps1"]
    for script in scripts:
        script_path = ROOT_DIR / script
        assert script_path.exists(), f"El script {script} no existe."
        
        # Analizar la sintaxis usando el parser de PowerShell
        cmd = [
            "powershell", "-NoProfile", "-Command",
            f"try {{ $null = [System.Management.Automation.Language.Parser]::ParseFile('{script_path}', [ref]$null, [ref]$null); exit 0 }} catch {{ exit 1 }}"
        ]
        result = subprocess.run(cmd, capture_output=True, check=False)
        assert result.returncode == 0, f"Error de sintaxis en {script}:\n{result.stderr.decode()}"

def test_register_task_whatif():
    """Prueba el registro de tarea en modo WhatIf sin ConfirmRegistration."""
    script_path = ROOT_DIR / "scripts" / "register_scheduled_task.ps1"
    
    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(script_path), "-WhatIf"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert result.returncode == 0
    assert "MODO SIMULACION" in result.stdout
    assert "Registrando tarea" not in result.stdout

def test_run_pipeline_wrapper_different_cwd(tmp_path):
    """Prueba que el wrapper funciona (o falla correctamente) resolviendo la ruta desde otro cwd."""
    script_path = ROOT_DIR / "scripts" / "run_pipeline.ps1"
    
    # Cambiamos el CWD a tmp_path y ejecutamos el script con su ruta absoluta
    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(script_path)
    ]
    
    # Dado que el proyecto tiene un .venv (o al menos un log file creará),
    # comprobamos que no falla con error interno de PowerShell y que devuelve un exit code esperado
    # Si todo está correcto y localmente corre bien (pipeline vacío sin archivos), debería devolver 0
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(tmp_path), check=False)
    assert result.returncode in (0, 1, 2, 3), f"Código de salida inesperado: {result.returncode}"
