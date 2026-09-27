THEME_DARK = """
QMainWindow, QWidget { 
    background: #07111f; 
    color: #eaf2ff; 
    font-size: 13px; 
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif; 
}
QLabel#HeroBanner { 
    background: #07111f; 
    border: 1px solid #1d4265; 
    border-radius: 8px; 
    font-size: 16px; 
    font-weight: bold; 
    color: #eaf2ff;
}
QLabel#AccordionNumber { 
    color: #f5faff; 
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #173b60, stop:1 #0b1b2d); 
    border: 1px solid #2595ff; 
    border-radius: 7px; 
    font-size: 18px; 
    font-weight: 700; 
}
QFrame#AccordionCard { 
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #10263d, stop:0.55 #0b1b2d, stop:1 #0d2034); 
    border: 1px solid #23649a; 
    border-radius: 9px; 
}
QFrame#AccordionBody { 
    background: transparent; 
    border: none; 
}
QToolButton#AccordionHeader { 
    background: transparent; 
    color: #f3f7ff; 
    border: none; 
    padding: 1px 2px; 
    text-align: left; 
    font-size: 17px; 
    font-weight: 700; 
}
QToolButton#AccordionHeader:hover { color: #69bdff; }
QLabel#AccordionSubtitle { color: #a7b9cf; font-size: 12px; }

QLineEdit, QComboBox { 
    background: #07111e; 
    color: #edf5ff; 
    border: 1px solid #355574; 
    border-radius: 5px; 
    padding: 8px 11px; 
    selection-background-color: #0877dc; 
    min-height: 20px; 
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #168cff; }

QPushButton { 
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #213a55, stop:1 #13273d); 
    color: #eaf3ff; 
    border: 1px solid #3b5e80; 
    border-radius: 5px; 
    padding: 9px 15px; 
    font-weight: 600; 
}
QPushButton:hover { background: #20466c; border-color: #168cff; }
QPushButton:pressed, QPushButton:disabled { background: #0b1b2d; color: #556677; border-color: #1a2a3a; }
QPushButton#PrimaryButton { 
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #168cff, stop:1 #075db1); 
    border: 1px solid #48b2ff; 
    font-weight: 700; 
    font-size: 13px;
}
QPushButton#PrimaryButton:hover { background: #168cff; }

QScrollArea { border: none; background: transparent; }
QScrollArea QWidget { background: transparent; }
QCheckBox { spacing: 8px; color: #dce8f7; }
QCheckBox::indicator { width: 17px; height: 17px; background: #07111e; border: 1px solid #526b85; border-radius: 3px; }
QCheckBox::indicator:checked { background: #0878d1; border: 1px solid #55b7ff; }

QLabel#StatusLabel { color: #78d8ff; }
QLabel#pluginStatusActive { color: #3FB950; font-weight: bold; }
QLabel#pluginCount { color: #55b7ff; font-weight: bold; font-size: 13px; }

QLabel[originType="Engine"] { color: #a7b9cf; font-weight: bold; }
QLabel[originType="Project"] { color: #c482fa; font-weight: bold; background: rgba(196, 130, 250, 0.15); padding: 2px 6px; border-radius: 4px; }
QLabel[originType="Custom"] { color: #55b7ff; font-weight: bold; background: rgba(85, 183, 255, 0.15); padding: 2px 6px; border-radius: 4px; }

QPlainTextEdit#logView { 
    background: #040a12; 
    color: #8fe3ff; 
    border: 1px solid #23415e; 
    border-radius: 5px; 
    padding: 12px; 
    font-family: Consolas, Menlo, monospace; 
}

QTabWidget::pane { border: 1px solid #355574; border-radius: 5px; background: #07111e; }
QTabBar::tab { background: #13273d; border: 1px solid #3b5e80; padding: 9px 18px; border-top-left-radius: 5px; border-top-right-radius: 5px; color: #a7b9cf; margin-right: 2px; }
QTabBar::tab:selected { background: #07111e; color: #edf5ff; border-top: 2px solid #168cff; font-weight: bold; }
QTabBar::tab:hover:!selected { background: #20466c; color: #fff; }

QGroupBox { background: transparent; border: 1px solid #23649a; border-radius: 6px; margin-top: 14px; padding: 14px; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #69bdff; font-weight: bold; }
QScrollBar:vertical { border: none; background: #07111f; width: 10px; }
QScrollBar::handle:vertical { background: #355574; min-height: 20px; border-radius: 5px; }
"""

THEME_LIGHT = """
QMainWindow, QWidget { 
    background: #f4f7fb; 
    color: #0b1b2d; 
    font-size: 13px; 
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif; 
}
QLabel#HeroBanner { 
    background: #ffffff; 
    border: 1px solid #b8cde3; 
    border-radius: 8px; 
    font-size: 16px; 
    font-weight: bold; 
    color: #0b1b2d;
}
QLabel#AccordionNumber { 
    color: #0b1b2d; 
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #eaf2ff, stop:1 #dce8f7); 
    border: 1px solid #168cff; 
    border-radius: 7px; 
    font-size: 18px; 
    font-weight: 700; 
}
QFrame#AccordionCard { 
    background: #ffffff; 
    border: 1px solid #cbdbe9; 
    border-radius: 9px; 
}
QFrame#AccordionBody { 
    background: transparent; 
    border: none; 
}
QToolButton#AccordionHeader { 
    background: transparent; 
    color: #07111e; 
    border: none; 
    padding: 1px 2px; 
    text-align: left; 
    font-size: 17px; 
    font-weight: 700; 
}
QToolButton#AccordionHeader:hover { color: #168cff; }
QLabel#AccordionSubtitle { color: #526b85; font-size: 12px; }

QLineEdit, QComboBox { 
    background: #ffffff; 
    color: #07111e; 
    border: 1px solid #cbdbe9; 
    border-radius: 5px; 
    padding: 8px 11px; 
    selection-background-color: #0877dc; 
    min-height: 20px; 
}
QLineEdit:focus, QComboBox:focus { border: 1px solid #168cff; }

QPushButton { 
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #ffffff, stop:1 #eef3f9); 
    color: #07111e; 
    border: 1px solid #b8cde3; 
    border-radius: 5px; 
    padding: 9px 15px; 
    font-weight: 600; 
}
QPushButton:hover { background: #e0ecf8; border-color: #168cff; }
QPushButton:pressed, QPushButton:disabled { background: #dce8f7; color: #8899aa; border-color: #ccd; }
QPushButton#PrimaryButton { 
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #168cff, stop:1 #075db1); 
    color: #ffffff; 
    border: 1px solid #075db1; 
    font-weight: 700; 
    font-size: 13px;
}
QPushButton#PrimaryButton:hover { background: #168cff; }

QScrollArea { border: none; background: transparent; }
QScrollArea QWidget { background: transparent; }
QCheckBox { spacing: 8px; color: #07111e; }
QCheckBox::indicator { width: 17px; height: 17px; background: #ffffff; border: 1px solid #b8cde3; border-radius: 3px; }
QCheckBox::indicator:checked { background: #0878d1; border: 1px solid #075db1; }

QLabel#StatusLabel { color: #075db1; }
QLabel#pluginStatusActive { color: #059669; font-weight: bold; }
QLabel#pluginCount { color: #0284C7; font-weight: bold; font-size: 13px; }

QLabel[originType="Engine"] { color: #64748B; font-weight: bold; }
QLabel[originType="Project"] { color: #7E22CE; font-weight: bold; background: #F3E8FF; padding: 2px 6px; border-radius: 4px; }
QLabel[originType="Custom"] { color: #0369A1; font-weight: bold; background: #E0F2FE; padding: 2px 6px; border-radius: 4px; }

QPlainTextEdit#logView { 
    background: #f8fafc; 
    color: #07111f; 
    border: 1px solid #cbdbe9; 
    border-radius: 5px; 
    padding: 12px; 
    font-family: Consolas, Menlo, monospace; 
}

QTabWidget::pane { border: 1px solid #cbdbe9; border-radius: 5px; background: #ffffff; }
QTabBar::tab { background: #eef3f9; border: 1px solid #cbdbe9; padding: 9px 18px; border-top-left-radius: 5px; border-top-right-radius: 5px; color: #526b85; margin-right: 2px; }
QTabBar::tab:selected { background: #ffffff; color: #0b1b2d; border-top: 2px solid #168cff; font-weight: bold; }
QTabBar::tab:hover:!selected { background: #e0ecf8; color: #07111e; }

QGroupBox { background: transparent; border: 1px solid #cbdbe9; border-radius: 6px; margin-top: 14px; padding: 14px; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #075db1; font-weight: bold; }
QScrollBar:vertical { border: none; background: #f4f7fb; width: 10px; }
QScrollBar::handle:vertical { background: #cbdbe9; min-height: 20px; border-radius: 5px; }
"""