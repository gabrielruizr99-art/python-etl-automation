import sys
from unittest.mock import MagicMock

from scripts.pipeline_status import main


def test_pipeline_status_read_only(monkeypatch, capsys):
    """Prueba que pipeline_status ejecuta en modo READ ONLY y finaliza sin errores."""
    mock_get_settings = MagicMock()
    mock_get_settings.return_value.get_psycopg_connection_info.return_value = {"dbname": "test"}
    monkeypatch.setattr("scripts.pipeline_status.get_settings", mock_get_settings)
    
    mock_conn = MagicMock()
    mock_conn_entered = mock_conn.__enter__.return_value
    mock_cur = mock_conn_entered.cursor.return_value.__enter__.return_value
    
    # Simular retornos de las consultas
    # 1. file_registry
    mock_cur.fetchall.side_effect = [
        [("processed", 10), ("failed", 2)], # files by status
        [(1, "completed", None, None)], # last runs
        [("DATA_ERROR", 5)], # rejections
    ]
    # 3. sales
    mock_cur.fetchone.side_effect = [
        (100, "2026-04-15"), # sales count and max date
        ("test.csv", None), # last file processed
        (2, None, None), # last failed run
    ]
    
    mock_psycopg_connect = MagicMock(return_value=mock_conn)
    monkeypatch.setattr("scripts.pipeline_status.psycopg.connect", mock_psycopg_connect)
    
    # Evitar exit(0)
    def mock_exit(code):
        if code != 0:
            raise SystemExit(code)
    
    monkeypatch.setattr(sys, "exit", mock_exit)
    
    main()
    
    # Verificar que read_only = True
    assert mock_conn_entered.read_only is True
    
    # Verificar salida (capsys no falló y tiene contenido)
    captured = capsys.readouterr()
    assert "ESTADO DE ARCHIVOS" in captured.out
    assert "WAREHOUSE SALES" in captured.out
