from unittest.mock import MagicMock

import pytest

from scripts.run_pipeline import main


def test_run_pipeline_success(monkeypatch):
    """Prueba que el pipeline finaliza con 0 si todo va bien y libera el lock."""
    mock_get_settings = MagicMock()
    mock_get_settings.return_value.get_psycopg_connection_info.return_value = {"dbname": "test"}
    monkeypatch.setattr("scripts.run_pipeline.get_settings", mock_get_settings)
    
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    mock_cur.fetchone.return_value = [True]  # Lock adquirido
    
    mock_psycopg_connect = MagicMock(return_value=mock_conn)
    monkeypatch.setattr("scripts.run_pipeline.psycopg.connect", mock_psycopg_connect)
    
    # Mockear servicios para evitar ejecución real
    monkeypatch.setattr("scripts.run_pipeline.ETLRepository", MagicMock())
    
    mock_disc_res = MagicMock()
    mock_disc_res.status = 'completed'
    mock_disc_res.duplicate_paths = []
    mock_disc_svc = MagicMock()
    mock_disc_svc.return_value.run_discovery.return_value = mock_disc_res
    
    monkeypatch.setattr("scripts.run_pipeline.DiscoveryService", mock_disc_svc)
    
    mock_val_res = MagicMock()
    mock_val_res.status = 'completed'
    mock_val_res.valid_rows_total = 100
    mock_load_res = MagicMock()
    mock_load_res.rows_inserted = 100
    mock_val_svc = MagicMock()
    mock_val_svc.return_value.run_validation.return_value = mock_val_res
    mock_load_svc = MagicMock()
    mock_load_svc.return_value.run_load.return_value = mock_load_res
    
    monkeypatch.setattr("scripts.run_pipeline.ValidationService", mock_val_svc)
    monkeypatch.setattr("scripts.run_pipeline.LoadService", mock_load_svc)
    monkeypatch.setattr("scripts.run_pipeline.setup_logging", MagicMock())
    
    with pytest.raises(SystemExit) as exc:
        main()
        
    assert exc.value.code == 0
    # Verificar que se intentó liberar el lock
    lock_release_calls = [c for c in mock_cur.execute.call_args_list if "pg_advisory_unlock" in c[0][0]]
    assert len(lock_release_calls) > 0
    mock_conn.close.assert_called()

def test_run_pipeline_lock_occupied(monkeypatch):
    """Prueba el exit code 3 cuando el lock no se puede obtener."""
    mock_get_settings = MagicMock()
    monkeypatch.setattr("scripts.run_pipeline.get_settings", mock_get_settings)
    
    mock_conn = MagicMock()
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    mock_cur.fetchone.return_value = [False]  # Lock OCUPADO
    
    mock_psycopg_connect = MagicMock(return_value=mock_conn)
    monkeypatch.setattr("scripts.run_pipeline.psycopg.connect", mock_psycopg_connect)
    monkeypatch.setattr("scripts.run_pipeline.setup_logging", MagicMock())
    
    with pytest.raises(SystemExit) as exc:
        main()
        
    assert exc.value.code == 3
    # Si no se obtuvo el lock, igual debe pasar por el finally, pero el unlock no es peligroso si se llama, 
    # aunque en la implementación actual se llama igual, o no, dependiendo de la estructura. 
    # Lo importante es el código de salida.

def test_run_pipeline_bad_config(monkeypatch):
    """Prueba el exit code 2 ante configuración inválida."""
    monkeypatch.setattr("scripts.run_pipeline.setup_logging", MagicMock())
    def mock_raise():
        raise ValueError("Bad config")
    monkeypatch.setattr("scripts.run_pipeline.get_settings", mock_raise)
    
    with pytest.raises(SystemExit) as exc:
        main()
        
    assert exc.value.code == 2

def test_run_pipeline_general_error(monkeypatch):
    """Prueba el exit code 1 y que el lock se libera ante excepciones imprevistas."""
    mock_get_settings = MagicMock()
    monkeypatch.setattr("scripts.run_pipeline.get_settings", mock_get_settings)
    
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cur = mock_conn.cursor.return_value.__enter__.return_value
    mock_cur.fetchone.return_value = [True]  # Lock adquirido
    
    mock_psycopg_connect = MagicMock(return_value=mock_conn)
    monkeypatch.setattr("scripts.run_pipeline.psycopg.connect", mock_psycopg_connect)
    monkeypatch.setattr("scripts.run_pipeline.setup_logging", MagicMock())
    
    def raise_error(*args, **kwargs):
        raise RuntimeError("Unexpected failure")
        
    monkeypatch.setattr("scripts.run_pipeline.ETLRepository", raise_error)
    
    with pytest.raises(SystemExit) as exc:
        main()
        
    assert exc.value.code == 1
    
    # Verificar que el lock se liberó a pesar de la excepción
    lock_release_calls = [c for c in mock_cur.execute.call_args_list if "pg_advisory_unlock" in c[0][0]]
    assert len(lock_release_calls) > 0
    mock_conn.close.assert_called()
