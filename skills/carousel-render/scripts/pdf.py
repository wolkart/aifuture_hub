#!/usr/bin/env python3
"""PNG-карточки → один PDF-документ. Только stdlib.

Зачем: LinkedIn берёт карусель документом (PDF), а не набором картинок.
Instagram — наоборот, картинками. Поэтому PDF собирается из тех же PNG, а не
рендерится отдельно: карточка обязана быть одна и та же на обеих площадках.

Как: PNG уже сжат zlib'ом со строчными фильтрами, и PDF умеет читать ровно
это — `FlateDecode` + `Predictor 15`. Поэтому пиксели не трогаются вообще:
поток IDAT переносится в PDF байт в байт. Ни перекодирования, ни потери
качества, ни сторонних библиотек.

Ограничение: только 8 бит на канал, RGB, без чересстрочности и без палитры —
именно такие PNG отдаёт наш рендер. Другой формат — честная ошибка, а не
молчаливая перекодировка во что попало.
"""
import argparse
import struct
import zlib
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
COLOR_RGB = 2


class UnsupportedPNG(ValueError):
    """PNG, который нельзя перенести в PDF без перекодирования."""


def read_png(path):
    """Заголовок + сырой поток IDAT. Без распаковки пикселей."""
    data = Path(path).read_bytes()
    if data[:8] != PNG_SIGNATURE:
        raise UnsupportedPNG(f"{path}: не PNG")

    width, height, depth, color, compression, filt, interlace = struct.unpack(
        ">IIBBBBB", data[16:29])
    if depth != 8 or color != COLOR_RGB:
        raise UnsupportedPNG(
            f"{path}: нужен 8-битный RGB, а здесь глубина {depth}, тип {color}")
    if interlace:
        raise UnsupportedPNG(f"{path}: чересстрочный PNG не переносится")
    if compression or filt:
        raise UnsupportedPNG(f"{path}: нестандартное сжатие или фильтрация")

    # IDAT может быть разбит на любое число чанков — их надо склеить в один
    # поток, иначе zlib увидит обрубок.
    chunks, pos = [], 8
    while pos + 8 <= len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        if kind == b"IDAT":
            chunks.append(data[pos + 8:pos + 8 + length])
        elif kind == b"IEND":
            break
        pos += 12 + length

    if not chunks:
        raise UnsupportedPNG(f"{path}: нет данных изображения")
    return {"ширина": width, "высота": height, "поток": b"".join(chunks)}


def build_pdf(images):
    """Собирает PDF: страница на картинку, размер страницы = размер картинки.

    Точка PDF равна пикселю (72 dpi), поэтому 1080×1350 px даёт страницу
    1080×1350 pt с той же пропорцией 4:5 — ровно то, что ждёт LinkedIn.
    """
    if not images:
        raise ValueError("нечего собирать: список картинок пуст")

    objects = {}
    page_ids = []
    for index, img in enumerate(images):
        page_id = 3 + index * 3
        content_id, image_id = page_id + 1, page_id + 2
        page_ids.append(page_id)
        w, h = img["ширина"], img["высота"]

        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {w} {h}] "
            f"/Resources << /XObject << /Im0 {image_id} 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode("ascii")

        # Матрица растягивает единичный квадрат картинки на всю страницу.
        stream = f"q {w} 0 0 {h} 0 0 cm /Im0 Do Q".encode("ascii")
        objects[content_id] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream + b"\nendstream")

        head = (
            f"<< /Type /XObject /Subtype /Image /Width {w} /Height {h} "
            f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode "
            f"/DecodeParms << /Predictor 15 /Colors 3 /BitsPerComponent 8 "
            f"/Columns {w} >> /Length {len(img['поток'])} >>\nstream\n"
        ).encode("ascii")
        objects[image_id] = head + img["поток"] + b"\nendstream"

    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = (f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>"
                  ).encode("ascii")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for num in sorted(objects):
        offsets[num] = len(out)
        out += f"{num} 0 obj\n".encode("ascii") + objects[num] + b"\nendobj\n"

    xref_at = len(out)
    total = max(objects) + 1
    out += f"xref\n0 {total}\n".encode("ascii")
    out += b"0000000000 65535 f \n"
    for num in range(1, total):
        out += f"{offsets.get(num, 0):010d} 00000 n \n".encode("ascii")
    out += (f"trailer\n<< /Size {total} /Root 1 0 R >>\nstartxref\n{xref_at}\n"
            "%%EOF\n").encode("ascii")
    return bytes(out)


def pngs_to_pdf(png_paths, out_pdf):
    """Читает PNG по порядку и пишет PDF. Возвращает путь и число страниц."""
    images = [read_png(p) for p in png_paths]
    Path(out_pdf).write_bytes(build_pdf(images))
    return Path(out_pdf), len(images)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pngs", nargs="+", help="карточки по порядку")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    path, pages = pngs_to_pdf(args.pngs, args.out)
    print(f"{path} страниц: {pages}")


if __name__ == "__main__":
    main()
