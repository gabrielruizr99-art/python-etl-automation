import hashlib
import os
from pathlib import Path


def calculate_sha256(file_path: Path, chunk_size: int = 8192) -> str:
    """
    Calcula el hash SHA-256 de un archivo leyendo en bloques.
    Verifica que el archivo no haya sido modificado durante la lectura.
    """
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
        
    initial_stat = os.stat(file_path)
    
    sha256_hash = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(chunk_size):
            sha256_hash.update(chunk)
            
    final_stat = os.stat(file_path)
    if initial_stat.st_size != final_stat.st_size or initial_stat.st_mtime != final_stat.st_mtime:
        raise ValueError("File modified during hash calculation")
        
    return sha256_hash.hexdigest()
