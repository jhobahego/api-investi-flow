"""
Servicio para extracción de contenido de documentos .docx a HTML
Compatible con TipTap editor
"""
import re
from pathlib import Path
from typing import List, Optional

try:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph
except ImportError:
    raise ImportError(
        "python-docx no está instalado. " "Ejecuta: pip install python-docx"
    )

from fastapi import HTTPException


class DocumentExtractionService:
    """Servicio para extraer contenido de documentos y convertirlo a HTML"""

    # Configuración de páginas
    CHARS_PER_PAGE = 3000  # Aproximadamente 3000 caracteres por página A4

    @staticmethod
    def extract_docx_to_html(file_path: str) -> str:
        """
        Extrae el contenido de un archivo .docx y lo convierte a HTML
        compatible con TipTap editor

        Args:
            file_path: Ruta al archivo .docx

        Returns:
            str: Contenido HTML del documento

        Raises:
            HTTPException: Si el archivo no existe o no se puede leer
        """
        path = Path(file_path)

        if not path.exists():
            raise HTTPException(
                status_code=404, detail=f"Archivo no encontrado: {file_path}"
            )

        if not path.suffix.lower() == ".docx":
            raise HTTPException(
                status_code=400, detail="Solo se soportan archivos .docx"
            )

        try:
            document = Document(file_path)
            html_content = DocumentExtractionService._convert_document_to_html(document)
            return html_content

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al extraer contenido del documento: {str(e)}",
            )

    @staticmethod
    def extract_docx_to_pages(file_path: str) -> List[str]:
        """
        Extrae el contenido de un archivo .docx y lo divide en páginas HTML

        Args:
            file_path: Ruta al archivo .docx

        Returns:
            List[str]: Lista de páginas HTML del documento

        Raises:
            HTTPException: Si el archivo no existe o no se puede leer
        """
        path = Path(file_path)

        if not path.exists():
            raise HTTPException(
                status_code=404, detail=f"Archivo no encontrado: {file_path}"
            )

        if not path.suffix.lower() == ".docx":
            raise HTTPException(
                status_code=400, detail="Solo se soportan archivos .docx"
            )

        try:
            document = Document(file_path)
            pages = DocumentExtractionService._convert_document_to_pages(document)
            return pages

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al extraer contenido del documento: {str(e)}",
            )

    @staticmethod
    def _convert_document_to_html(document: Document) -> str:
        """
        Convierte un objeto Document de python-docx a HTML

        Args:
            document: Objeto Document de python-docx

        Returns:
            str: HTML generado
        """
        html_parts = []

        for element in document.element.body:
            # Procesar párrafos
            if element.tag.endswith("p"):
                para = Paragraph(element, document)
                html_parts.append(DocumentExtractionService._paragraph_to_html(para))
            # Procesar tablas
            elif element.tag.endswith("tbl"):
                table = Table(element, document)
                html_parts.append(DocumentExtractionService._table_to_html(table))

        # Si no hay contenido, devolver párrafo vacío
        if not html_parts or all(part.strip() == "" for part in html_parts):
            return "<p></p>"

        return "".join(html_parts)

    @staticmethod
    def _convert_document_to_pages(document: Document) -> List[str]:
        """
        Convierte un objeto Document de python-docx a lista de páginas HTML

        Args:
            document: Objeto Document de python-docx

        Returns:
            List[str]: Lista de páginas HTML
        """
        all_elements = []

        # Recolectar todos los elementos HTML
        for element in document.element.body:
            # Procesar párrafos
            if element.tag.endswith("p"):
                para = Paragraph(element, document)
                html = DocumentExtractionService._paragraph_to_html(para)
                if html.strip():
                    all_elements.append(html)
            # Procesar tablas
            elif element.tag.endswith("tbl"):
                table = Table(element, document)
                html = DocumentExtractionService._table_to_html(table)
                if html.strip():
                    all_elements.append(html)

        # Si no hay contenido, devolver una página vacía
        if not all_elements:
            return ["<p></p>"]

        # Dividir en páginas
        pages: List[str] = []
        current_page: List[str] = []
        current_length = 0

        for element_html in all_elements:
            # Calcular longitud de texto del elemento
            element_text = re.sub(r"<[^>]+>", "", element_html)
            element_length = len(element_text)

            # Si agregar este elemento excede el límite, crear nueva página
            if (
                current_length + element_length
                > DocumentExtractionService.CHARS_PER_PAGE
                and current_page
            ):
                pages.append("".join(current_page))
                current_page = [element_html]
                current_length = element_length
            else:
                current_page.append(element_html)
                current_length += element_length

        # Agregar última página
        if current_page:
            pages.append("".join(current_page))

        return pages if pages else ["<p></p>"]

    @staticmethod
    def _paragraph_to_html(paragraph: Paragraph) -> str:
        """
        Convierte un párrafo de docx a HTML con formato

        Args:
            paragraph: Objeto Paragraph de python-docx

        Returns:
            str: HTML del párrafo
        """
        text = paragraph.text.strip()

        # Si el párrafo está vacío, devolver un párrafo HTML vacío
        if not text:
            return "<p></p>"

        # Detectar nivel de encabezado
        style = paragraph.style.name.lower() if paragraph.style else ""

        if "heading 1" in style or "título 1" in style:
            return f"<h1>{DocumentExtractionService._format_runs(paragraph)}</h1>"
        elif "heading 2" in style or "título 2" in style:
            return f"<h2>{DocumentExtractionService._format_runs(paragraph)}</h2>"
        elif "heading 3" in style or "título 3" in style:
            return f"<h3>{DocumentExtractionService._format_runs(paragraph)}</h3>"

        # Detectar listas
        if paragraph._element.pPr is not None:
            numPr = paragraph._element.pPr.find(
                ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numPr"
            )
            if numPr is not None:
                # Es un elemento de lista
                ilvl = numPr.find(
                    ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}ilvl"
                )
                numId = numPr.find(
                    ".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}numId"
                )

                if ilvl is not None and numId is not None:
                    # Determinar si es lista ordenada o no ordenada
                    # (simplificación: se usa ul por defecto)
                    return (
                        f"<li>{DocumentExtractionService._format_runs(paragraph)}</li>"
                    )

        # Párrafo normal
        return f"<p>{DocumentExtractionService._format_runs(paragraph)}</p>"

    @staticmethod
    def _format_runs(paragraph: Paragraph) -> str:
        """
        Procesa los runs de un párrafo aplicando formato en línea

        Args:
            paragraph: Objeto Paragraph de python-docx

        Returns:
            str: Texto con formato HTML
        """
        html_text = []

        for run in paragraph.runs:
            text = run.text

            # Aplicar formato en línea
            if run.bold:
                text = f"<strong>{text}</strong>"
            if run.italic:
                text = f"<em>{text}</em>"
            if run.underline:
                text = f"<u>{text}</u>"

            html_text.append(text)

        return "".join(html_text)

    @staticmethod
    def _table_to_html(table: Table) -> str:
        """
        Convierte una tabla de docx a HTML

        Args:
            table: Objeto Table de python-docx

        Returns:
            str: HTML de la tabla
        """
        html = ["<table>"]

        for i, row in enumerate(table.rows):
            html.append("<tr>")
            for cell in row.cells:
                tag = "th" if i == 0 else "td"
                cell_text = cell.text.strip()
                html.append(f"<{tag}>{cell_text}</{tag}>")
            html.append("</tr>")

        html.append("</table>")
        return "".join(html)

    @staticmethod
    def get_document_preview(file_path: str, max_chars: int = 200) -> str:
        """
        Obtiene una vista previa del contenido del documento (texto plano)

        Args:
            file_path: Ruta al archivo .docx
            max_chars: Número máximo de caracteres para la vista previa

        Returns:
            str: Vista previa del documento
        """
        try:
            document = Document(file_path)
            full_text = "\n".join([para.text for para in document.paragraphs])

            if len(full_text) <= max_chars:
                return full_text

            return full_text[:max_chars] + "..."

        except Exception as e:
            return f"Error al obtener vista previa: {str(e)}"


# Instancia del servicio
document_extraction_service = DocumentExtractionService()
