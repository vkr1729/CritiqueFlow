import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from core.file_reader import list_files, read_file

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_list_files_returns_only_supported():
    files = list_files(str(FIXTURES_DIR))
    assert "sample.md" in files
    assert "sample.txt" in files
    assert "sample.xlsx" in files
    assert "sample.docx" in files
    assert "sample.pdf" in files
    assert all(Path(f).suffix.lower() in {".md", ".txt", ".xlsx", ".xls", ".docx", ".pdf"} for f in files)


def test_list_files_returns_sorted():
    files = list_files(str(FIXTURES_DIR))
    assert files == sorted(files)


def test_list_files_rejects_nonexistent_directory():
    with pytest.raises(FileNotFoundError):
        list_files(os.path.join(os.path.abspath(os.sep), "nonexistent", "path", "12345"))


def test_list_files_rejects_relative_path():
    with pytest.raises(ValueError, match="absolute"):
        list_files("relative/path")


def test_read_file_markdown():
    result = read_file(str(FIXTURES_DIR), "sample.md")
    assert result["filename"] == "sample.md"
    assert "Valuation Risk Model" in result["content"]


def test_read_file_txt():
    result = read_file(str(FIXTURES_DIR), "sample.txt")
    assert result["filename"] == "sample.txt"
    assert "Hull-White" in result["content"]


def test_read_file_xlsx():
    result = read_file(str(FIXTURES_DIR), "sample.xlsx")
    assert result["filename"] == "sample.xlsx"
    assert "Model" in result["content"]
    assert "Heston" in result["content"]


def test_read_file_docx():
    result = read_file(str(FIXTURES_DIR), "sample.docx")
    assert result["filename"] == "sample.docx"
    assert "Model Validation Report" in result["content"]


def test_read_file_pdf():
    result = read_file(str(FIXTURES_DIR), "sample.pdf")
    assert result["filename"] == "sample.pdf"


def test_read_file_rejects_path_traversal():
    with pytest.raises(ValueError):
        read_file(str(FIXTURES_DIR), "../etc/passwd")


def test_read_file_rejects_slash_in_filename():
    with pytest.raises(ValueError):
        read_file(str(FIXTURES_DIR), "etc/passwd")


def test_read_file_rejects_backslash_in_filename():
    with pytest.raises(ValueError):
        read_file(str(FIXTURES_DIR), "etc\\passwd")


def test_read_file_rejects_unsupported_extension():
    with pytest.raises(ValueError, match="Unsupported"):
        read_file(str(FIXTURES_DIR), "sample.md.bak")


def test_read_file_rejects_missing_file():
    with pytest.raises(FileNotFoundError):
        read_file(str(FIXTURES_DIR), "nonexistent.md")


def test_read_file_char_cap_enforced(tmp_path):
    from core.file_reader import _read_text

    big_content = "x" * 1000
    p = tmp_path / "big.txt"
    p.write_text(big_content)
    result = _read_text(p, 50)
    assert len(result) == 50


def test_read_file_row_cap_enforced(tmp_path):
    from openpyxl import Workbook

    p = tmp_path / "big.xlsx"
    wb = Workbook()
    ws = wb.active
    for i in range(150):
        ws.cell(row=i + 1, column=1, value=f"row{i}")
    wb.save(str(p))

    from core.file_reader import _read_xlsx
    result = _read_xlsx(p, 5)
    lines = result.split("\n")
    assert len(lines) == 5


def test_read_file_rejects_prefix_sibling(tmp_path):
    """BF-2: Sibling directory with matching name prefix must not be readable."""
    target_dir = tmp_path / "audit"
    sibling_dir = tmp_path / "audit_evil"
    target_dir.mkdir()
    sibling_dir.mkdir()
    (sibling_dir / "secret.md").write_text("secret data")
    # Attempting to traverse from target_dir to sibling via ../ must be blocked
    with pytest.raises((ValueError, FileNotFoundError)):
        read_file(str(target_dir), "../audit_evil/secret.md")
