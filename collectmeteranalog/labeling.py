import os
import sys
import math
import shutil

import numpy as np
import pandas as pd
from PIL import Image
from PIL.ImageQt import ImageQt

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QGraphicsLineItem, QGraphicsTextItem,
    QPushButton, QSlider, QLabel, QVBoxLayout, QHBoxLayout,
    QGridLayout, QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, QLineF, QPointF
from PySide6.QtGui import (
    QPixmap, QImage, QPen, QColor, QFont, QKeySequence, QShortcut,
    QPainter, QBrush
)

from collectmeteranalog.predict import predict
from collectmeteranalog.__version__ import __version__


def ziffer_data_files(input_dir):
    '''return a list of all images in given input dir in all subdirectories'''
    imgfiles = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith(".jpg"):
                imgfiles.append(root + "/" + file)
    imgfiles = sorted(imgfiles, key=lambda x: os.path.basename(x))
    return imgfiles


def load_image(files, i, startlabel=-1):
    while i < len(files):
        base = os.path.basename(files[i])
        if base[1] == ".":
            target = base[0:3]
        else:
            target = base[0:1]
        try:
            category = float(target)
        except Exception:
            category = 0
        if category >= startlabel:
            filename = files[i]
            test_image = Image.open(filename)
            return test_image, category, filename, i
        i = i + 1
    raise SystemExit(f"No images found matching startlabel >= {startlabel}")


class PolarOverlayView(QGraphicsView):
    """QGraphicsView that displays a meter image with a polar dial overlay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("background: #2b2b2b; border: none;")

        self._pixmap_item = None
        self._grid_visible = True
        self._filelabel = 0.0
        self._ticksteps = 1

    def set_image(self, pil_image):
        """Display a PIL image."""
        self._current_qimage = ImageQt(pil_image.convert("RGBA"))
        pixmap = QPixmap.fromImage(self._current_qimage)
        if self._pixmap_item is None:
            self._pixmap_item = self._scene.addPixmap(pixmap)
        else:
            self._pixmap_item.setPixmap(pixmap)
        self._pixmap_item.setZValue(0)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)

    def update_overlay(self, filelabel, ticksteps):
        """Store overlay parameters and trigger repaint."""
        self._filelabel = filelabel
        self._ticksteps = ticksteps
        self.viewport().update()

    def set_grid_visible(self, visible):
        self._grid_visible = visible
        self.viewport().update()

    def _get_viewport_center_and_radius(self):
        """Get the center and radius of the image in viewport coordinates."""
        if self._pixmap_item is None:
            return None, None, None
        img_rect = self._pixmap_item.boundingRect()
        # Map image corners to viewport
        top_left = self.mapFromScene(img_rect.topLeft())
        bottom_right = self.mapFromScene(img_rect.bottomRight())
        cx = (top_left.x() + bottom_right.x()) / 2.0
        cy = (top_left.y() + bottom_right.y()) / 2.0
        w = bottom_right.x() - top_left.x()
        h = bottom_right.y() - top_left.y()
        radius = min(w, h) / 2.0 * 0.95
        return cx, cy, radius

    def drawForeground(self, painter, rect):
        """Draw polar overlay in viewport coordinates (independent of image size)."""
        super().drawForeground(painter, rect)
        if self._pixmap_item is None:
            return

        # Reset transform to draw in viewport (pixel) coordinates
        painter.resetTransform()
        painter.setRenderHint(QPainter.Antialiasing)

        cx, cy, radius = self._get_viewport_center_and_radius()
        if radius is None or radius < 5:
            return

        tick_len = radius * 0.03
        major_tick_len = radius * 0.055

        # Pointer line
        angle_rad = 2 * math.pi * self._filelabel / 10.0
        px = cx + radius * math.sin(angle_rad)
        py = cy - radius * math.cos(angle_rad)
        painter.setPen(QPen(QColor(0, 200, 0), max(2, radius * 0.015)))
        painter.drawLine(QPointF(cx, cy), QPointF(px, py))

        if not self._grid_visible:
            return

        # Ticks and labels
        num_ticks = int(100 / self._ticksteps)
        minor_pen = QPen(QColor(255, 255, 0, 180), max(1, radius * 0.004))
        major_pen = QPen(QColor(255, 255, 0, 220), max(1.5, radius * 0.007))

        font_size = max(10, int(radius * 0.05))
        font = QFont("sans-serif", font_size)
        font.setBold(True)
        painter.setFont(font)
        fm = painter.fontMetrics()

        for k in range(num_ticks):
            val = k * self._ticksteps / 10.0
            a = 2 * math.pi * val / 10.0
            sin_a = math.sin(a)
            cos_a = math.cos(a)
            is_major = abs(val - round(val)) < 0.01

            # Tick mark
            tl = major_tick_len if is_major else tick_len
            painter.setPen(major_pen if is_major else minor_pen)
            x1 = cx + (radius - tl) * sin_a
            y1 = cy - (radius - tl) * cos_a
            x2 = cx + radius * sin_a
            y2 = cy - radius * cos_a
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

            # Text labels only at major ticks (0, 1, ..., 9)
            if is_major:
                label_text = f"{int(val)}"
                label_dist = radius + major_tick_len + 4
                lx = cx + label_dist * sin_a
                ly = cy - label_dist * cos_a
                tw = fm.horizontalAdvance(label_text)
                th = fm.height()

                # Dark background
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
                painter.drawRoundedRect(
                    int(lx - tw / 2 - 2), int(ly - th / 2 - 1),
                    tw + 4, th + 2, 3, 3
                )

                # Yellow text
                painter.setPen(QColor(255, 255, 0))
                painter.setBrush(Qt.NoBrush)
                painter.drawText(
                    int(lx - tw / 2), int(ly - th / 2 + fm.ascent()),
                    label_text
                )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap_item is not None:
            self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            cx, cy, radius = self._get_viewport_center_and_radius()
            if cx is not None:
                dx = event.pos().x() - cx
                dy = -(event.pos().y() - cy)
                angle = math.atan2(dx, dy)
                if angle < 0:
                    angle += 2 * math.pi
                val = round(angle * 10 / (2 * math.pi), 1) % 10
                window = self.window()
                if isinstance(window, LabelingWindow):
                    window.set_filelabel(val)
        super().mousePressEvent(event)


class LabelingWindow(QMainWindow):
    """Main labeling window replacing the old matplotlib-based UI."""

    def __init__(self, files, startlabel, ticksteps, labelfile_prediction):
        super().__init__()
        self.files = files
        self.ticksteps = ticksteps
        self.labelfile_prediction = labelfile_prediction
        self.i = 0
        self.filelabel = 0.0
        self.filename = ""
        self.usegrid = True

        self._setup_ui()
        self._setup_shortcuts()

        # Load first image
        img, self.filelabel, self.filename, self.i = load_image(
            self.files, self.i, startlabel
        )
        self._show_image(img)
        self._update_title()

    def _setup_ui(self):
        self.setWindowTitle(f"collectmeteranalog v{__version__}")
        self.setStyleSheet("background: #353535; color: #e0e0e0;")

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # Graphics view (center)
        self.view = PolarOverlayView()
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.view, stretch=1)

        # Right panel
        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)

        # Prediction label
        self.pred_label = QLabel("Prediction\ndisabled")
        self.pred_label.setAlignment(Qt.AlignCenter)
        self.pred_label.setStyleSheet(
            "background: #f8f8f8; color: #333; padding: 8px; "
            "border-radius: 4px; font-size: 13px;"
        )
        right_panel.addWidget(self.pred_label)

        right_panel.addStretch()

        # Grid toggle
        btn_grid = QPushButton("Grid")
        btn_grid.clicked.connect(self._on_toggle_grid)
        right_panel.addWidget(btn_grid)

        right_panel.addStretch()

        # +/- buttons
        btn_layout = QGridLayout()
        btn_dec1 = QPushButton("-1.0")
        btn_dec01 = QPushButton("-0.1")
        btn_inc01 = QPushButton("+0.1")
        btn_inc1 = QPushButton("+1.0")
        btn_dec1.clicked.connect(lambda: self._change_label(-1.0))
        btn_dec01.clicked.connect(lambda: self._change_label(-0.1))
        btn_inc01.clicked.connect(lambda: self._change_label(0.1))
        btn_inc1.clicked.connect(lambda: self._change_label(1.0))
        btn_layout.addWidget(btn_dec1, 0, 0)
        btn_layout.addWidget(btn_inc1, 0, 1)
        btn_layout.addWidget(btn_dec01, 1, 0)
        btn_layout.addWidget(btn_inc01, 1, 1)
        right_panel.addLayout(btn_layout)

        right_panel.addStretch()

        # Previous / Update / Delete
        btn_previous = QPushButton("Previous")
        btn_update = QPushButton("Update")
        btn_delete = QPushButton("Delete")
        btn_delete.setStyleSheet(
            "QPushButton { background: #c0392b; color: white; padding: 6px; }"
            "QPushButton:hover { background: #e74c3c; }"
        )
        btn_previous.clicked.connect(self._on_previous)
        btn_update.clicked.connect(self._on_next)
        btn_delete.clicked.connect(self._on_remove)
        right_panel.addWidget(btn_previous)
        right_panel.addWidget(btn_update)
        right_panel.addWidget(btn_delete)

        main_layout.addLayout(right_panel)

        # Slider (bottom)
        slider_layout = QHBoxLayout()
        self.slider_value_label = QLabel("0.0")
        self.slider_value_label.setMinimumWidth(35)
        self.slider_value_label.setAlignment(Qt.AlignCenter)
        self.slider_value_label.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 99)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(10)
        self.slider.setValue(0)
        self.slider.valueChanged.connect(self._on_slider_changed)

        slider_label = QLabel("Label:")
        slider_label.setStyleSheet("font-size: 12px;")
        slider_layout.addWidget(slider_label)
        slider_layout.addWidget(self.slider, stretch=1)
        slider_layout.addWidget(self.slider_value_label)

        # Wrap main_layout and slider in a vertical layout
        outer = QVBoxLayout()
        content_widget = QWidget()
        content_widget.setLayout(main_layout)
        outer.addWidget(content_widget, stretch=1)
        outer.addLayout(slider_layout)

        wrapper = QWidget()
        wrapper.setLayout(outer)
        self.setCentralWidget(wrapper)

        # Style buttons
        for btn in [btn_grid, btn_dec1, btn_dec01, btn_inc01, btn_inc1,
                    btn_previous, btn_update]:
            btn.setStyleSheet(
                "QPushButton { background: #555; color: white; padding: 6px; "
                "border-radius: 3px; }"
                "QPushButton:hover { background: #777; }"
            )

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Right), self, self._on_next)
        QShortcut(QKeySequence(Qt.Key_Left), self, self._on_previous)
        QShortcut(QKeySequence(Qt.Key_Up), self, lambda: self._change_label(0.1))
        QShortcut(QKeySequence(Qt.Key_Down), self, lambda: self._change_label(-0.1))
        QShortcut(QKeySequence(Qt.Key_PageUp), self, lambda: self._change_label(1.0))
        QShortcut(QKeySequence(Qt.Key_PageDown), self, lambda: self._change_label(-1.0))
        QShortcut(QKeySequence(Qt.Key_Return), self, self._on_next)
        QShortcut(QKeySequence(Qt.Key_Enter), self, self._on_next)
        QShortcut(QKeySequence(Qt.Key_Delete), self, self._on_remove)

    def _show_image(self, img):
        """Display image and overlay."""
        self._current_pil_image = img  # prevent garbage collection
        self.view.set_image(img)
        self._update_overlay()
        self._update_slider()
        self._update_prediction(img)

    def _update_overlay(self):
        self.view.update_overlay(self.filelabel, self.ticksteps)

    def _update_slider(self):
        self.slider.blockSignals(True)
        self.slider.setValue(int(round(self.filelabel * 10)))
        self.slider.blockSignals(False)
        self.slider_value_label.setText(f"{self.filelabel:.1f}")

    def _update_title(self):
        self.setWindowTitle(
            f"collectmeteranalog v{__version__}   |   "
            f"Image: {self.i + 1} / {len(self.files)}"
        )

    def _update_prediction(self, img):
        prediction = predict(img)
        if (prediction == -1 and self.labelfile_prediction is not None
                and isinstance(self.labelfile_prediction, (list, np.ndarray))
                and self.i < len(self.labelfile_prediction)
                and self.labelfile_prediction[self.i] is not None
                and not pd.isna(self.labelfile_prediction[self.i])):
            prediction = self.labelfile_prediction[self.i]
        if prediction != -1:
            self.pred_label.setText(f"Prediction:\n{prediction:.1f}")
        else:
            self.pred_label.setText("Prediction\ndisabled")

    def set_filelabel(self, val):
        """Set filelabel from external source (e.g. mouse click)."""
        self.filelabel = val
        self._update_slider()
        self._update_overlay()

    def _change_label(self, delta):
        self.filelabel = round((self.filelabel + delta) % 10, 1)
        self._update_slider()
        self._update_overlay()

    def _on_slider_changed(self, value):
        self.filelabel = round(value / 10.0, 1)
        self.slider_value_label.setText(f"{self.filelabel:.1f}")
        self._update_overlay()

    def _on_previous(self):
        self.i = (self.i - 1) % len(self.files)
        self._load_current()

    def _on_next(self):
        # Save current label by renaming file
        basename = os.path.basename(self.filename).split('_', 1)
        basename = basename[-1]
        new_path = os.path.join(
            os.path.dirname(self.filename),
            f"{self.filelabel:.1f}_{basename}"
        )
        if self.filename != new_path:
            self.files[self.i] = new_path
            shutil.move(self.filename, new_path)
        self.i = (self.i + 1) % len(self.files)
        self._load_current()

    def _on_remove(self):
        os.remove(self.filename)
        self.files.pop(self.i)
        if len(self.files) == 0:
            print("No more images.")
            self.close()
            return
        self.i = self.i % len(self.files)
        self._load_current()

    def _on_toggle_grid(self):
        self.usegrid = not self.usegrid
        self.view.set_grid_visible(self.usegrid)
        self._update_overlay()

    def _load_current(self):
        img, self.filelabel, self.filename, self.i = load_image(
            self.files, self.i
        )
        self._show_image(img)
        self._update_title()


def label(path, startlabel=0.0, labelfile_path=None, ticksteps=1):
    labelfile_prediction = None

    if labelfile_path is not None:
        try:
            print(f"Loading image file list | labelfile: {labelfile_path}")
            files_df = pd.read_csv(
                labelfile_path, index_col="Index",
                usecols=["Index", "File", "Predicted"]
            )
            files_df["FilePath"] = files_df["File"].apply(
                lambda f: os.path.join(path, f)
            )
            files_df = files_df[files_df["FilePath"].apply(os.path.exists)]

            if "Predicted" in files_df.columns:
                labelfile_prediction = files_df["Predicted"].to_numpy().reshape(-1)
                print("labelfile: Prediction data available")
            else:
                labelfile_prediction = []
                print("labelfile: No prediction data available")

            files = files_df["FilePath"].to_numpy()

            if len(files) > 0:
                print(f"Loading images from path: {os.path.dirname(files[0])}")
            else:
                raise SystemExit("Image file list empty. No files to load")

        except Exception:
            print("Columns 'Index, File, Predicted' in labelfile not found. "
                  "Try loading labelfile in legacy format...")
            try:
                raw_files = pd.read_csv(
                    labelfile_path, index_col=0
                ).to_numpy().reshape(-1)
                print(f"Loading images from path: "
                      f"{os.path.join(path, os.path.dirname(raw_files[0]))}")
                files = np.array([
                    os.path.join(path, f) for f in raw_files
                    if os.path.exists(os.path.join(path, f))
                ])
                labelfile_prediction = [None] * len(files)
            except Exception as legacy_e:
                print(f"Legacy loading failed: {legacy_e}")
                raise SystemExit(
                    "Failed to load labelfile in any supported format."
                )
    else:
        print(f"Loading images from path: {path}")
        files = ziffer_data_files(path)

    if len(files) == 0:
        print("No images found in defined path")
        sys.exit(1)

    print(f"Startlabel:", startlabel)

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    window = LabelingWindow(files, startlabel, ticksteps, labelfile_prediction)
    window.showMaximized()
    app.exec()
