import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class BibliographyBase(BaseModel):
    type: str = Field(
        ..., description="Tipo de fuente: libro, articulo, web, tesis, etc."
    )
    author: str = Field(..., description="Autores (puede ser JSON string o texto)")
    year: Optional[int] = Field(None, description="Año de publicación")
    title: str = Field(..., description="Título de la obra")
    source: Optional[str] = Field(
        None, description="Editorial, Revista, Sitio Web, etc."
    )
    doi: Optional[str] = None
    url: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None

    @field_validator("author")
    @classmethod
    def validate_author(cls, v: str) -> str:
        # Si es un string JSON válido, lo dejamos tal cual, si no, lo aceptamos como texto
        try:
            if v.strip().startswith("[") or v.strip().startswith("{"):
                json.loads(v)
        except (json.JSONDecodeError, ValueError):
            pass
        return v


class BibliographyCreate(BibliographyBase):
    pass


class BibliographyUpdate(BaseModel):
    type: Optional[str] = None
    author: Optional[str] = None
    year: Optional[int] = None
    title: Optional[str] = None
    source: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None


class Bibliography(BibliographyBase):
    id: int
    project_id: int
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
