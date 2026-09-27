from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QToolButton
)

class AccordionSection(QWidget):
    def __init__(self, title: str, subtitle: str = "", expanded: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        number, separator, clean_title = title.partition("·")
        number = number.strip() if separator else ""
        clean_title = clean_title.strip() if separator else title

        self.card = QFrame()
        self.card.setObjectName("AccordionCard")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(18, 14, 18, 16)
        card_layout.setSpacing(6)

        heading = QHBoxLayout()
        heading.setSpacing(14)
        self.number_badge = QLabel(number or "•")
        self.number_badge.setObjectName("AccordionNumber")
        self.number_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.number_badge.setFixedSize(54, 44)
        heading.addWidget(self.number_badge, 0, Qt.AlignmentFlag.AlignTop)

        title_column = QVBoxLayout()
        title_column.setSpacing(3)
        self.toggle = QToolButton()
        self.toggle.setText(clean_title)
        self.toggle.setCheckable(True)
        self.toggle.setChecked(expanded)
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.toggle.setObjectName("AccordionHeader")
        title_column.addWidget(self.toggle)

        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("AccordionSubtitle")
        self.subtitle.setWordWrap(True)
        if subtitle:
            title_column.addWidget(self.subtitle)
        heading.addLayout(title_column, 1)
        card_layout.addLayout(heading)

        self.body = QFrame()
        self.body.setObjectName("AccordionBody")
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 12, 0, 0)
        self.body_layout.setSpacing(12)
        card_layout.addWidget(self.body)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.card)

        self.toggle.toggled.connect(self._set_expanded)
        self._set_expanded(expanded)

    def _set_expanded(self, expanded: bool) -> None:
        self.body.setVisible(expanded)
        self.toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)