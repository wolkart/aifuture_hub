import struct
import zlib

import pytest

import pdf


def make_png(path, width=4, height=3, color=(10, 20, 30), depth=8,
             color_type=2, interlace=0, split_idat=False):
    """Настоящий PNG нужного вида — без сторонних библиотек."""
    raw = b"".join(b"\x00" + bytes(color) * width for _ in range(height))
    compressed = zlib.compress(raw)

    def chunk(kind, payload):
        return (struct.pack(">I", len(payload)) + kind + payload
                + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", width, height, depth, color_type, 0, 0, interlace)
    parts = [pdf.PNG_SIGNATURE, chunk(b"IHDR", ihdr)]
    if split_idat:
        middle = len(compressed) // 2
        parts += [chunk(b"IDAT", compressed[:middle]),
                  chunk(b"IDAT", compressed[middle:])]
    else:
        parts.append(chunk(b"IDAT", compressed))
    parts.append(chunk(b"IEND", b""))
    path.write_bytes(b"".join(parts))
    return path, compressed


def test_поток_переносится_байт_в_байт(tmp_path):
    """Смысл всего файла: пиксели не перекодируются."""
    path, compressed = make_png(tmp_path / "a.png")
    assert pdf.read_png(path)["поток"] == compressed


def test_разрезанный_idat_склеивается(tmp_path):
    """Chrome отдаёт IDAT десятками чанков — обрубок сломал бы картинку."""
    path, compressed = make_png(tmp_path / "a.png", split_idat=True)
    assert pdf.read_png(path)["поток"] == compressed


def test_страница_на_карточку_и_размер_страницы(tmp_path):
    pngs = [make_png(tmp_path / f"{i}.png", width=1080, height=1350)[0]
            for i in range(3)]
    out, pages = pdf.pngs_to_pdf(pngs, tmp_path / "out.pdf")
    data = out.read_bytes()
    assert pages == 3
    assert data.count(b"/Type /Page ") == 3
    assert data.count(b"/MediaBox [0 0 1080 1350]") == 3
    assert b"/Count 3" in data


def test_pdf_начинается_и_кончается_как_pdf(tmp_path):
    path, _ = make_png(tmp_path / "a.png")
    out, _ = pdf.pngs_to_pdf([path], tmp_path / "out.pdf")
    data = out.read_bytes()
    assert data.startswith(b"%PDF-1.4")
    assert data.rstrip().endswith(b"%%EOF")
    assert b"startxref" in data


def test_смещения_в_xref_указывают_на_объекты(tmp_path):
    """Битый xref открывается не везде — проверяем адреса, а не наличие."""
    path, _ = make_png(tmp_path / "a.png")
    out, _ = pdf.pngs_to_pdf([path], tmp_path / "out.pdf")
    data = out.read_bytes()
    table = data.split(b"xref\n")[-1].split(b"trailer")[0].strip().splitlines()
    entries = [line for line in table if line.endswith(b"n ")]
    for num, line in enumerate(entries, start=1):
        offset = int(line.split()[0])
        assert data[offset:offset + 8].startswith(f"{num} 0 obj".encode())


def test_картинка_объявлена_с_png_предсказателем(tmp_path):
    """Без Predictor 15 PDF покажет кашу вместо карточки."""
    path, _ = make_png(tmp_path / "a.png", width=1080, height=1350)
    out, _ = pdf.pngs_to_pdf([path], tmp_path / "out.pdf")
    data = out.read_bytes()
    assert b"/Predictor 15" in data
    assert b"/Colors 3" in data
    assert b"/Columns 1080" in data
    assert b"/Filter /FlateDecode" in data


@pytest.mark.parametrize("kwargs,кусок", [
    ({"color_type": 6}, "тип 6"),
    ({"depth": 16}, "глубина 16"),
    ({"interlace": 1}, "чересстрочный"),
])
def test_неподходящий_png_отвергается_с_объяснением(tmp_path, kwargs, кусок):
    """Молчаливая перекодировка хуже ошибки: автор должен знать, что не так."""
    path, _ = make_png(tmp_path / "a.png", **kwargs)
    with pytest.raises(pdf.UnsupportedPNG) as err:
        pdf.read_png(path)
    assert кусок in str(err.value)


def test_пустой_список_не_даёт_пустой_pdf(tmp_path):
    with pytest.raises(ValueError):
        pdf.build_pdf([])
