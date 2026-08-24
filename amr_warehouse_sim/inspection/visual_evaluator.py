from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import struct
import zlib


class InvalidImageError(ValueError):
    pass


@dataclass(frozen=True)
class VisualEvaluation:
    red_ratio: float
    threshold: float
    finding: str
    severity: str | None
    reason: str


_ENCODINGS = {
    'rgb8': (3, (0, 1, 2)),
    'bgr8': (3, (2, 1, 0)),
    'rgba8': (4, (0, 1, 2)),
    'bgra8': (4, (2, 1, 0)),
}


def decode_rgb_bytes(
    *,
    width: int,
    height: int,
    encoding: str,
    step: int,
    data: bytes,
) -> bytes:
    normalized = encoding.lower()
    contract = _ENCODINGS.get(normalized)
    if contract is None:
        raise InvalidImageError(f'unsupported_image_encoding:{encoding}')
    if width <= 0 or height <= 0:
        raise InvalidImageError('image_dimensions_must_be_positive')

    bytes_per_pixel, channel_order = contract
    minimum_step = width * bytes_per_pixel
    if step < minimum_step:
        raise InvalidImageError('image_step_smaller_than_row_width')
    if len(data) < step * height:
        raise InvalidImageError('image_data_is_truncated')

    output = bytearray(width * height * 3)
    output_offset = 0
    for row_index in range(height):
        row = memoryview(data)[row_index * step:row_index * step + minimum_step]
        for pixel_offset in range(0, minimum_step, bytes_per_pixel):
            output[output_offset] = row[pixel_offset + channel_order[0]]
            output[output_offset + 1] = row[pixel_offset + channel_order[1]]
            output[output_offset + 2] = row[pixel_offset + channel_order[2]]
            output_offset += 3
    return bytes(output)


def evaluate_red_ratio(rgb: bytes, *, threshold: float) -> VisualEvaluation:
    if len(rgb) == 0 or len(rgb) % 3 != 0:
        raise InvalidImageError('packed_rgb_length_is_invalid')
    if not 0.0 <= threshold <= 1.0:
        raise ValueError('threshold must be between 0 and 1')

    red_dominant = 0
    pixel_count = len(rgb) // 3
    view = memoryview(rgb)
    for offset in range(0, len(rgb), 3):
        red = view[offset]
        green = view[offset + 1]
        blue = view[offset + 2]
        if red >= 150 and red >= green + 35 and red >= blue + 35:
            red_dominant += 1
    ratio = red_dominant / pixel_count
    warning = ratio > threshold
    return VisualEvaluation(
        red_ratio=ratio,
        threshold=threshold,
        finding='warning' if warning else 'pass',
        severity='warning' if warning else None,
        reason=(
            'red_ratio_above_threshold'
            if warning
            else 'red_ratio_within_threshold'
        ),
    )


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    body = chunk_type + payload
    return struct.pack('>I', len(payload)) + body + struct.pack(
        '>I', zlib.crc32(body) & 0xFFFFFFFF
    )


def write_rgb_png(path: Path, *, width: int, height: int, rgb: bytes) -> str:
    expected = width * height * 3
    if width <= 0 or height <= 0 or len(rgb) != expected:
        raise InvalidImageError('packed_rgb_dimensions_do_not_match')
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    row_size = width * 3
    for row_index in range(height):
        start = row_index * row_size
        rows.append(b'\x00' + rgb[start:start + row_size])
    payload = (
        b'\x89PNG\r\n\x1a\n'
        + _png_chunk(
            b'IHDR',
            struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0),
        )
        + _png_chunk(b'IDAT', zlib.compress(b''.join(rows), level=6))
        + _png_chunk(b'IEND', b'')
    )
    path.write_bytes(payload)
    return sha256(payload).hexdigest()
