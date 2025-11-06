"""
Factories para generación de datos de prueba.

Este módulo contiene funciones factory que generan datos de prueba
realistas y variados para usar en los tests.
"""

import random
from datetime import datetime, timedelta
from typing import Optional


def create_user_data(
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    password: str = "TestPassword123",
    phone_number: Optional[str] = None,
) -> dict:
    """
    Genera datos de prueba para crear un usuario.

    Args:
        email: Email del usuario (se genera uno aleatorio si no se proporciona)
        full_name: Nombre completo (se genera uno aleatorio si no se proporciona)
        password: Contraseña del usuario
        phone_number: Teléfono (se genera uno aleatorio si no se proporciona)

    Returns:
        dict: Diccionario con datos del usuario
    """
    random_id = random.randint(1000, 9999)

    return {
        "email": email or f"user{random_id}@example.com",
        "full_name": full_name or f"Test User {random_id}",
        "password": password,
        "phone_number": phone_number or f"+57300{random_id:07d}",
    }


def create_project_data(
    name: Optional[str] = None,
    description: Optional[str] = None,
    research_type: str = "experimental",
    status: str = "planning",
) -> dict:
    """
    Genera datos de prueba para crear un proyecto.

    Args:
        name: Nombre del proyecto (se genera uno aleatorio si no se proporciona)
        description: Descripción del proyecto
        research_type: Tipo de investigación
        status: Estado del proyecto

    Returns:
        dict: Diccionario con datos del proyecto
    """
    random_id = random.randint(1000, 9999)

    return {
        "name": name or f"Test Project {random_id}",
        "description": description or f"Test project description {random_id}",
        "research_type": research_type,
        "institution": "Test University",
        "research_group": "Test Research Group",
        "category": "Technology",
        "status": status,
    }


def create_phase_data(
    name: Optional[str] = None,
    project_id: int = 1,
    position: int = 0,
    color: Optional[str] = None,
) -> dict:
    """
    Genera datos de prueba para crear una fase.

    Args:
        name: Nombre de la fase (se genera uno aleatorio si no se proporciona)
        project_id: ID del proyecto al que pertenece
        position: Posición de la fase
        color: Color de la fase (se genera uno aleatorio si no se proporciona)

    Returns:
        dict: Diccionario con datos de la fase
    """
    random_id = random.randint(1000, 9999)
    default_colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#33FFF3"]

    return {
        "name": name or f"Test Phase {random_id}",
        "description": f"Test phase description {random_id}",
        "position": position,
        "color": color or random.choice(default_colors),
        "project_id": project_id,
    }


def create_task_data(
    title: Optional[str] = None,
    phase_id: int = 1,
    position: int = 0,
    status: str = "pending",
    completed: bool = False,
    with_dates: bool = False,
) -> dict:
    """
    Genera datos de prueba para crear una tarea.

    Args:
        title: Título de la tarea (se genera uno aleatorio si no se proporciona)
        phase_id: ID de la fase a la que pertenece
        position: Posición de la tarea
        status: Estado de la tarea
        completed: Si la tarea está completada
        with_dates: Si se deben incluir fechas de inicio y fin

    Returns:
        dict: Diccionario con datos de la tarea
    """
    random_id = random.randint(1000, 9999)

    data = {
        "title": title or f"Test Task {random_id}",
        "description": f"Test task description {random_id}",
        "position": position,
        "status": status,
        "completed": completed,
        "phase_id": phase_id,
    }

    if with_dates:
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(days=7)
        data["start_date"] = start_date
        data["end_date"] = end_date

    return data


def create_attachment_data(
    filename: Optional[str] = None,
    file_type: str = "application/pdf",
    task_id: Optional[int] = None,
    project_id: Optional[int] = None,
) -> dict:
    """
    Genera datos de prueba para crear un adjunto.

    Args:
        filename: Nombre del archivo (se genera uno aleatorio si no se proporciona)
        file_type: Tipo de archivo
        task_id: ID de la tarea a la que pertenece (opcional)
        project_id: ID del proyecto al que pertenece (opcional)

    Returns:
        dict: Diccionario con datos del adjunto
    """
    random_id = random.randint(1000, 9999)

    data = {
        "filename": filename or f"document_{random_id}.pdf",
        "file_path": f"/uploads/documents/document_{random_id}.pdf",
        "file_type": file_type,
        "file_size": random.randint(1024, 1024000),  # 1KB a 1MB
    }

    if task_id:
        data["task_id"] = task_id
    if project_id:
        data["project_id"] = project_id

    return data


def create_bibliography_data(
    tipo: str = "articulo",
    titulo: Optional[str] = None,
    autores: Optional[list] = None,
    anio: Optional[int] = None,
) -> dict:
    """
    Genera datos de prueba para una referencia bibliográfica.

    Args:
        tipo: Tipo de fuente (articulo, libro, tesis, web)
        titulo: Título de la fuente
        autores: Lista de autores
        anio: Año de publicación

    Returns:
        dict: Diccionario con datos de la bibliografía
    """
    random_id = random.randint(1000, 9999)
    current_year = datetime.now().year

    return {
        "tipo": tipo,
        "titulo": titulo or f"Test Article Title {random_id}",
        "autores": autores
        or [
            {"apellido": "Smith", "nombre": "J."},
            {"apellido": "Doe", "nombre": "A."},
        ],
        "anio": anio or random.randint(2015, current_year),
        "revista": "Test Journal",
        "volumen": random.randint(1, 50),
        "numero": random.randint(1, 12),
        "paginas": f"{random.randint(1, 200)}-{random.randint(201, 300)}",
        "doi": f"10.1234/test.{random_id}",
        "url": f"https://example.com/article/{random_id}",
    }


def create_multiple_users_data(count: int = 3) -> list[dict]:
    """
    Genera múltiples datos de usuarios para pruebas.

    Args:
        count: Número de usuarios a generar

    Returns:
        list[dict]: Lista de diccionarios con datos de usuarios
    """
    return [create_user_data() for _ in range(count)]


def create_multiple_projects_data(count: int = 3) -> list[dict]:
    """
    Genera múltiples datos de proyectos para pruebas.

    Args:
        count: Número de proyectos a generar

    Returns:
        list[dict]: Lista de diccionarios con datos de proyectos
    """
    return [create_project_data() for _ in range(count)]


def create_multiple_tasks_data(count: int = 3, phase_id: int = 1) -> list[dict]:
    """
    Genera múltiples datos de tareas para pruebas.

    Args:
        count: Número de tareas a generar
        phase_id: ID de la fase para las tareas

    Returns:
        list[dict]: Lista de diccionarios con datos de tareas
    """
    statuses = ["pending", "in_progress", "completed"]
    return [
        create_task_data(
            phase_id=phase_id,
            position=i,
            status=statuses[i % len(statuses)],
        )
        for i in range(count)
    ]
