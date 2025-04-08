import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional


# Ruta de la base de datos
DB_PATH = os.path.join(os.path.dirname(__file__), "../chat_history.db")


def init_db():
    """Inicializa la base de datos si no existe."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Crear tabla de conversaciones
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS conversations (
        session_id TEXT PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    )

    # Crear tabla de mensajes
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        content TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES conversations (session_id)
    )
    """
    )

    conn.commit()
    conn.close()


def save_message(session_id: str, role: str, content: str):
    """Guarda un mensaje en la base de datos.

    Args:
        session_id: ID de la sesión/conversación
        role: Rol del mensaje (human, ai)
        content: Contenido del mensaje
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Comprobar si la conversación existe, si no, crearla
    cursor.execute("SELECT 1 FROM conversations WHERE session_id = ?", (session_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO conversations (session_id) VALUES (?)", (session_id,)
        )
    else:
        # Actualizar timestamp de última actualización
        cursor.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE session_id = ?",
            (session_id,),
        )

    # Guardar el mensaje
    cursor.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content),
    )

    conn.commit()
    conn.close()


def get_conversation_history(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Obtiene el historial de conversación para una sesión determinada.

    Args:
        session_id: ID de la sesión/conversación
        limit: Número máximo de mensajes a recuperar

    Returns:
        Lista de mensajes ordenados cronológicamente
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role, content, timestamp 
        FROM messages 
        WHERE session_id = ? 
        ORDER BY timestamp ASC
        LIMIT ?
        """,
        (session_id, limit),
    )

    messages = []
    for row in cursor.fetchall():
        messages.append({"role": row[0], "content": row[1], "timestamp": row[2]})

    conn.close()
    return messages


def format_messages_for_context(messages: List[Dict[str, Any]]) -> str:
    """Formatea los mensajes para enviarlos como contexto.

    Args:
        messages: Lista de mensajes

    Returns:
        String con los mensajes formateados
    """
    if not messages:
        return ""

    formatted = "📜 HISTORIAL DE LA CONVERSACIÓN 📜\n\n"

    for msg in messages:
        role_str = "👤 Usuario" if msg["role"] == "human" else "🤖 Asistente"
        formatted += f"{role_str}: {msg['content']}\n\n"

    formatted += "--------------------------------\n\n"

    return formatted


# Inicializar la base de datos al importar
init_db()
