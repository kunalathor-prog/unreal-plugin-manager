"""Generate an original geometric pipeline icon; no third-party artwork."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import struct
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter, QPen

app = QGuiApplication.instance() or QGuiApplication([])
frames = []
for size in (16, 32, 48, 64, 128, 256):
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(QColor('#091827'))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(size / 256, size / 256)
    painter.setPen(QPen(QColor('#49baff'), 16))
    painter.drawLine(64, 64, 192, 64)
    painter.drawLine(192, 64, 192, 192)
    painter.drawLine(192, 192, 64, 192)
    for x, y in ((40, 40), (168, 40), (168, 168), (40, 168)):
        painter.setPen(QPen(QColor('#8edbff'), 5))
        painter.setBrush(QColor('#1768ad'))
        painter.drawRoundedRect(QRectF(x, y, 48, 48), 10, 10)
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, 'PNG')
    frames.append((size, bytes(data)))
offset = 6 + 16 * len(frames)
headers = []
for size, data in frames:
    headers.append(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
    offset += len(data)
output = Path(__file__).resolve().parents[1] / 'app/resources/pipeline.ico'
output.write_bytes(struct.pack('<HHH', 0, 1, len(frames)) + b''.join(headers) + b''.join(data for _, data in frames))
