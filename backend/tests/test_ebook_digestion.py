import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from backend.modules.digester import SimpleChunkDigester, EPUBMOBIHTMLParser

def test_epub_mobi_html_parser():
    html = """
    <html>
        <head><title>Ignored Head</title></head>
        <body>
            <script>ignored_script();</script>
            <style>body { color: red; }</style>
            <h1>Chapter 1: Rhizomes</h1>
            <p>This is a paragraph with <a href="#">a link</a>.</p>
            <div>Div content block</div>
        </body>
    </html>
    """
    parser = EPUBMOBIHTMLParser()
    parser.feed(html)
    text = parser.get_text()
    
    assert "Ignored Head" not in text
    assert "ignored_script" not in text
    assert "Chapter 1: Rhizomes" in text
    assert "This is a paragraph" in text
    assert "Div content block" in text


@patch("ebooklib.epub.read_epub")
def test_extract_epub(mock_read_epub):
    # Mocking ebooklib and epub module
    mock_book = MagicMock()
    mock_read_epub.return_value = mock_book
    
    mock_item = MagicMock()
    # ebooklib.ITEM_DOCUMENT value is 9
    mock_item.get_type.return_value = 9
    mock_item.get_content.return_value = b"<html><body><p>Hello EPUB content!</p></body></html>"
    
    mock_book.get_items.return_value = [mock_item]

    digester = SimpleChunkDigester()
    res = digester.extract(Path("test_book.epub"), "epub")
    
    assert "Hello EPUB content!" in res
    mock_read_epub.assert_called_once_with("test_book.epub")


@patch("mobi.extract")
@patch("shutil.rmtree")
@patch("builtins.open", new_callable=mock_open, read_data="<html><body><p>Hello MOBI content!</p></body></html>")
def test_extract_mobi(mock_file, mock_shutil, mock_mobi):
    mock_mobi.return_value = ("/tmp/tempdir", "/tmp/tempdir/book.html")
    
    digester = SimpleChunkDigester()
    res = digester.extract(Path("test_book.mobi"), "mobi")
    
    assert "Hello MOBI content!" in res
    mock_mobi.assert_called_once_with("test_book.mobi")
    mock_shutil.assert_called_once_with("/tmp/tempdir", ignore_errors=True)
