"""Tests para el servicio de extracción de documentos"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.document_extraction_service import DocumentExtractionService


@pytest.fixture
def mock_docx_document():
    """Mock de un documento Word"""
    mock_doc = MagicMock()

    # Mock de párrafos
    mock_para1 = MagicMock()
    mock_para1.text = "Título Principal"
    mock_para1.style.name = "Heading 1"
    mock_para1.runs = []

    mock_para2 = MagicMock()
    mock_para2.text = "Este es un párrafo con texto normal."
    mock_para2.style.name = "Normal"

    # Mock de runs para el párrafo 2
    mock_run1 = MagicMock()
    mock_run1.text = "Este es un párrafo "
    mock_run1.bold = False
    mock_run1.italic = False
    mock_run1.underline = False

    mock_run2 = MagicMock()
    mock_run2.text = "con texto"
    mock_run2.bold = True
    mock_run2.italic = False
    mock_run2.underline = False

    mock_run3 = MagicMock()
    mock_run3.text = " normal."
    mock_run3.bold = False
    mock_run3.italic = False
    mock_run3.underline = False

    mock_para2.runs = [mock_run1, mock_run2, mock_run3]

    # Mock del elemento body
    mock_element1 = MagicMock()
    mock_element1.tag = (
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
    )

    mock_element2 = MagicMock()
    mock_element2.tag = (
        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
    )

    mock_doc.element.body = [mock_element1, mock_element2]
    mock_doc.paragraphs = [mock_para1, mock_para2]

    return mock_doc


class TestDocumentExtractionService:
    """Pruebas para el servicio de extracción de documentos"""

    def test_extract_docx_to_html_success(self, mock_docx_document, tmp_path):
        """Probar extracción exitosa de documento DOCX a HTML"""
        # Crear un archivo temporal
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy content")

        with patch(
            "app.services.document_extraction_service.Document"
        ) as mock_doc_class:
            mock_doc_class.return_value = mock_docx_document

            result = DocumentExtractionService.extract_docx_to_html(str(test_file))

            assert isinstance(result, str)
            assert len(result) > 0

    def test_extract_docx_to_html_file_not_found(self):
        """Probar extracción con archivo que no existe"""
        with pytest.raises(HTTPException) as exc_info:
            DocumentExtractionService.extract_docx_to_html("/path/to/nonexistent.docx")

        assert exc_info.value.status_code == 404
        assert "Archivo no encontrado" in exc_info.value.detail

    def test_extract_docx_to_html_invalid_extension(self, tmp_path):
        """Probar extracción con archivo que no es DOCX"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("dummy content")

        with pytest.raises(HTTPException) as exc_info:
            DocumentExtractionService.extract_docx_to_html(str(test_file))

        assert exc_info.value.status_code == 400
        assert "Solo se soportan archivos .docx" in exc_info.value.detail

    def test_extract_docx_to_pages_success(self, mock_docx_document, tmp_path):
        """Probar extracción exitosa de documento DOCX a páginas"""
        # Crear un archivo temporal
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy content")

        with patch(
            "app.services.document_extraction_service.Document"
        ) as mock_doc_class:
            mock_doc_class.return_value = mock_docx_document

            result = DocumentExtractionService.extract_docx_to_pages(str(test_file))

            assert isinstance(result, list)
            assert len(result) > 0
            assert all(isinstance(page, str) for page in result)

    def test_extract_docx_to_pages_file_not_found(self):
        """Probar extracción a páginas con archivo que no existe"""
        with pytest.raises(HTTPException) as exc_info:
            DocumentExtractionService.extract_docx_to_pages("/path/to/nonexistent.docx")

        assert exc_info.value.status_code == 404
        assert "Archivo no encontrado" in exc_info.value.detail

    def test_convert_document_to_html_empty_document(self):
        """Probar conversión de documento vacío"""
        mock_doc = MagicMock()
        mock_doc.element.body = []

        result = DocumentExtractionService._convert_document_to_html(mock_doc)

        assert result == "<p></p>"

    def test_convert_document_to_pages_empty_document(self):
        """Probar conversión a páginas de documento vacío"""
        mock_doc = MagicMock()
        mock_doc.element.body = []

        result = DocumentExtractionService._convert_document_to_pages(mock_doc)

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "<p></p>"

    def test_paragraph_to_html_heading1(self):
        """Probar conversión de párrafo con estilo Heading 1"""
        mock_para = MagicMock()
        mock_para.text = "Título Principal"
        mock_para.style.name = "Heading 1"
        mock_para.runs = []
        mock_run = MagicMock()
        mock_run.text = "Título Principal"
        mock_run.bold = False
        mock_run.italic = False
        mock_run.underline = False
        mock_para.runs = [mock_run]

        result = DocumentExtractionService._paragraph_to_html(mock_para)

        assert result == "<h1>Título Principal</h1>"

    def test_paragraph_to_html_heading2(self):
        """Probar conversión de párrafo con estilo Heading 2"""
        mock_para = MagicMock()
        mock_para.text = "Subtítulo"
        mock_para.style.name = "Heading 2"
        mock_para.runs = []
        mock_run = MagicMock()
        mock_run.text = "Subtítulo"
        mock_run.bold = False
        mock_run.italic = False
        mock_run.underline = False
        mock_para.runs = [mock_run]

        result = DocumentExtractionService._paragraph_to_html(mock_para)

        assert result == "<h2>Subtítulo</h2>"

    def test_paragraph_to_html_empty(self):
        """Probar conversión de párrafo vacío"""
        mock_para = MagicMock()
        mock_para.text = ""
        mock_para.style.name = "Normal"
        mock_para.runs = []

        result = DocumentExtractionService._paragraph_to_html(mock_para)

        assert result == "<p></p>"

    def test_format_runs_with_bold(self):
        """Probar formateo de runs con texto en negrita"""
        mock_para = MagicMock()

        mock_run1 = MagicMock()
        mock_run1.text = "Texto normal "
        mock_run1.bold = False
        mock_run1.italic = False
        mock_run1.underline = False

        mock_run2 = MagicMock()
        mock_run2.text = "texto en negrita"
        mock_run2.bold = True
        mock_run2.italic = False
        mock_run2.underline = False

        mock_para.runs = [mock_run1, mock_run2]

        result = DocumentExtractionService._format_runs(mock_para)

        assert "Texto normal " in result
        assert "<strong>texto en negrita</strong>" in result

    def test_format_runs_with_italic(self):
        """Probar formateo de runs con texto en cursiva"""
        mock_para = MagicMock()

        mock_run = MagicMock()
        mock_run.text = "texto en cursiva"
        mock_run.bold = False
        mock_run.italic = True
        mock_run.underline = False

        mock_para.runs = [mock_run]

        result = DocumentExtractionService._format_runs(mock_para)

        assert "<em>texto en cursiva</em>" in result

    def test_format_runs_with_underline(self):
        """Probar formateo de runs con texto subrayado"""
        mock_para = MagicMock()

        mock_run = MagicMock()
        mock_run.text = "texto subrayado"
        mock_run.bold = False
        mock_run.italic = False
        mock_run.underline = True

        mock_para.runs = [mock_run]

        result = DocumentExtractionService._format_runs(mock_para)

        assert "<u>texto subrayado</u>" in result

    def test_format_runs_with_multiple_formats(self):
        """Probar formateo de runs con múltiples formatos"""
        mock_para = MagicMock()

        mock_run = MagicMock()
        mock_run.text = "texto formateado"
        mock_run.bold = True
        mock_run.italic = True
        mock_run.underline = False

        mock_para.runs = [mock_run]

        result = DocumentExtractionService._format_runs(mock_para)

        assert "<strong>" in result
        assert "<em>" in result
        assert "texto formateado" in result

    def test_table_to_html(self):
        """Probar conversión de tabla a HTML"""
        mock_table = MagicMock()

        # Mock de filas y celdas
        mock_cell1 = MagicMock()
        mock_cell1.text = "Encabezado 1"

        mock_cell2 = MagicMock()
        mock_cell2.text = "Encabezado 2"

        mock_row1 = MagicMock()
        mock_row1.cells = [mock_cell1, mock_cell2]

        mock_cell3 = MagicMock()
        mock_cell3.text = "Dato 1"

        mock_cell4 = MagicMock()
        mock_cell4.text = "Dato 2"

        mock_row2 = MagicMock()
        mock_row2.cells = [mock_cell3, mock_cell4]

        mock_table.rows = [mock_row1, mock_row2]

        result = DocumentExtractionService._table_to_html(mock_table)

        assert "<table>" in result
        assert "</table>" in result
        assert "<th>Encabezado 1</th>" in result
        assert "<th>Encabezado 2</th>" in result
        assert "<td>Dato 1</td>" in result
        assert "<td>Dato 2</td>" in result

    def test_get_document_preview_success(self, tmp_path):
        """Probar obtención de vista previa exitosa"""
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy content")

        mock_doc = MagicMock()
        mock_para1 = MagicMock()
        mock_para1.text = "Línea 1"
        mock_para2 = MagicMock()
        mock_para2.text = "Línea 2"
        mock_doc.paragraphs = [mock_para1, mock_para2]

        with patch(
            "app.services.document_extraction_service.Document"
        ) as mock_doc_class:
            mock_doc_class.return_value = mock_doc

            result = DocumentExtractionService.get_document_preview(
                str(test_file), max_chars=100
            )

            assert isinstance(result, str)
            assert "Línea 1" in result

    def test_get_document_preview_truncated(self, tmp_path):
        """Probar que la vista previa se trunca correctamente"""
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy content")

        mock_doc = MagicMock()
        mock_para = MagicMock()
        mock_para.text = "A" * 300  # Texto largo
        mock_doc.paragraphs = [mock_para]

        with patch(
            "app.services.document_extraction_service.Document"
        ) as mock_doc_class:
            mock_doc_class.return_value = mock_doc

            result = DocumentExtractionService.get_document_preview(
                str(test_file), max_chars=100
            )

            assert len(result) <= 103  # 100 + "..."
            assert result.endswith("...")

    def test_get_document_preview_error(self, tmp_path):
        """Probar vista previa con error en lectura"""
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy content")

        with patch(
            "app.services.document_extraction_service.Document"
        ) as mock_doc_class:
            mock_doc_class.side_effect = Exception("Error de lectura")

            result = DocumentExtractionService.get_document_preview(str(test_file))

            assert "Error al obtener vista previa" in result
