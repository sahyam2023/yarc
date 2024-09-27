import sys
import requests
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QTextEdit, QLabel,
    QFrame, QScrollArea, QComboBox, QDialog, QProgressBar, QSizePolicy
)
from PyQt5.QtGui import QIcon, QIntValidator
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, pyqtProperty, QObject, QTimer, QThread, pyqtSignal
from datetime import datetime, timedelta
import random
import string
import json
#import resources_rc  # Uncomment if you are using a resource file


class ResponseDialog(QDialog):
    def __init__(self, response_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Full Response Body")
        self.setGeometry(200, 200, 600, 400)

        layout = QVBoxLayout()

        self.response_text_edit = QTextEdit()
        self.response_text_edit.setReadOnly(True)
        self.response_text_edit.setText(response_text)

        layout.addWidget(self.response_text_edit)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        layout.addWidget(self.close_button)

        self.setLayout(layout)


class SmoothTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scroll_duration = 500

    def smooth_scroll(self, value):
        scroll_bar = self.verticalScrollBar()
        start_value = scroll_bar.value()
        if start_value == value:
            return

        step_count = 20
        step_size = (value - start_value) / step_count

        def perform_scroll_step():
            current_value = scroll_bar.value()
            new_value = int(current_value + step_size)
            if abs(new_value - value) < abs(step_size):
                new_value = int(value)
            scroll_bar.setValue(new_value)
            if new_value != value:
                QTimer.singleShot(self.scroll_duration // step_count, perform_scroll_step)

        perform_scroll_step()

    def setText(self, text):
        super().setText(text)
        self.smooth_scroll(self.verticalScrollBar().maximum())

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.last_mouse_pos = event.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            delta = event.pos() - self.last_mouse_pos
            scroll_bar = self.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.value() - delta.y())
            self.last_mouse_pos = event.pos()
        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        scroll_bar = self.verticalScrollBar()
        current_value = scroll_bar.value()
        scroll_step = event.angleDelta().y() / 120
        new_value = current_value - scroll_step * 10
        self.smooth_scroll(new_value)


class FadeEffect(QObject):
    def __init__(self, widget, duration=500, parent=None):
        super().__init__(parent)
        self._opacity = 1.0
        self._widget = widget
        self._duration = duration

    @pyqtProperty(float)
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, value):
        self._opacity = value
        self._widget.setStyleSheet(
            f"background-color: rgba(255, 255, 255, {self._opacity * 255});"
        )

    def apply_fade_in(self):
        animation = QPropertyAnimation(self, b"opacity")
        animation.setDuration(self._duration)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()


# Worker Thread for Network Request
class Worker(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    response_received = pyqtSignal(object)  # Signal to emit the response

    def __init__(self, url, payload):
        super().__init__()
        self.url = url
        self.payload = payload

    def run(self):
        try:
            response = requests.post(self.url, json=self.payload, timeout=40)
            self.response_received.emit(response)  # Emit signal with the response
        except requests.RequestException as e:
            self.error.emit(f"An error occurred: {str(e)}")
        finally:
            self.finished.emit()

class ChallanSender(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.set_auto_dates()
        self.update_random_ids()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self.center)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.center)

    def center(self):
        screen_geometry = QApplication.desktop().availableGeometry()
        widget_geometry = self.geometry()
        x = (screen_geometry.width() - widget_geometry.width()) / 2
        y = (screen_geometry.height() - widget_geometry.height()) / 2
        self.move(int(x), int(y))

    def init_ui(self):
        self.setWindowTitle("Challan Checker")
        self.setWindowIcon(QIcon(":/logo.png"))  # If using a resource file
        self.resize(800, 695)
        self.center()

        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        self.header_label = QLabel("Challan Checker for Himachal Pradesh")
        self.header_label.setStyleSheet(
            """
            font-size: 24px;
            font-weight: bold;
            color: #007bff;
            padding: 10px;
            border-bottom: 2px solid #007bff;
            background-color: #f0f8ff;
            text-align: center;
            width: 100%;
        """
        )
        self.main_layout.addWidget(self.header_label)

        self.container_widget = QWidget()
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.container_widget)
        self.main_layout.addWidget(self.scroll_area)

        self.setStyleSheet(
            """
            QWidget {
                background-color: #f0f0f0;
                font-size: 14px;
            }
            QLabel {
                color: #333;
                font-weight: bold;
                width: 150px;
                text-align: right;
                margin-right: 10px;
            }
            QLabel#url-label {
                font-size: 16px;
                color: #007bff;
                background-color: #f0f8ff;
                padding: 5px;
                border: 1px solid #007bff;
                border-radius: 5px;
            }
            QLineEdit, QTextEdit {
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #aaa;
                font-size: 14px;
                background-color: #f9f9f9;
                min-width: 300px;
            }
            QTextEdit {
                min-height: 100px;
                max-height: 300px;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                border-radius: 5px;
                padding: 10px;
                border: none;
                font-size: 14px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QFrame {
                border-radius: 5px;
                padding: 10px;
                margin: 10px 0;
                border: 1px solid #ddd;
            }
            #url-frame {
                background-color: #e6f7ff;
                border-bottom: 4px solid #66cdaa;
            }
            #details-frame {
                background-color: #fff5e6;
                border-bottom: 4px solid #ff9900;
            }
            #response-frame {
                background-color: #e6ffe6;
                border-bottom: 4px solid #00cc66;
            }
            #progress-frame {
                background-color: #f0f0f0;
            }
            QComboBox {
                padding: 5px 10px;
                border-radius: 5px;
                border: 1px solid #aaa;
                background-color: #f9f9f9;
                font-size: 16px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left-width: 1px;
                border-left-color: #ddd;
                border-left-style: solid;
            }
            QComboBox::down-arrow {
                image: url(:/down-arrow.png);
            }
            QComboBox QAbstractItemView {
                border: 1px solid #ddd;
                background-color: #ffffff;
                selection-background-color: #007bff;
                selection-color: white;
                font-size: 20px;
                font-weight: bold;
            }
            QComboBox::item {
                padding: 5px 10px;
            }
            QComboBox::item:selected {
                background-color: #007bff;
                color: white;
            }
            QLabel#copyright {
                color: #007bff;
                font-size: 12px;
                font-family: 'Arial', sans-serif;
                font-style: italic;
                text-align: right;
                margin-right: 10px;
                margin-bottom: 10px;
                background-color: #f0f0f0;
                padding: 5px;
                border-radius: 5px;
                border: 1px solid #007bff;
            }
            QScrollBar:vertical {
                border: 1px solid #ddd;
                background: #f1f1f1;
                width: 16px;
            }
            QScrollBar::handle:vertical {
                background: #007bff;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #0056b3;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                border: 1px solid #ddd;
                background: #f1f1f1;
                height: 10px;
            }
            QScrollBar::add-line:vertical {
                border-bottom: 1px solid #ddd;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QScrollBar::sub-line:vertical {
                border-top: 1px solid #ddd;
                border-bottom-left-radius: 5px;
                border-bottom-right-radius: 5px;
            }
        """
        )

        # URL Type Selection
        self.url_type_frame = QFrame()
        self.url_type_frame.setObjectName("url-frame")
        self.url_type_layout = QHBoxLayout()
        self.url_type_frame.setLayout(self.url_type_layout)
        self.url_type_label = QLabel("Select URL Type:")
        self.url_type_label.setObjectName("url-label")
        self.url_type_combo = QComboBox()
        self.url_type_combo.addItems(["Live Challan URL", "Testing Challan URL"])
        self.url_type_combo.currentIndexChanged.connect(self.update_url)
        self.url_type_layout.addWidget(self.url_type_label)
        self.url_type_layout.addWidget(self.url_type_combo)
        self.container_layout.addWidget(self.url_type_frame)

        # User Details Frame
        self.details_frame = QFrame()
        self.details_frame.setObjectName("details-frame")
        self.details_layout = QVBoxLayout()
        self.details_frame.setLayout(self.details_layout)

        self.user_id_input = QLineEdit()
        self.district_id_input = QLineEdit()
        self.location_input = QLineEdit()
        self.district_input = QLineEdit()
        self.off_code_input = QLineEdit()
        int_validator = QIntValidator(0, 9999, self)

        self.user_id_input.setValidator(int_validator)
        self.district_id_input.setValidator(int_validator)
        self.off_code_input.setValidator(int_validator)

        fields = [
            ("User ID:", self.user_id_input),
            ("District ID:", self.district_id_input),
            ("Location:", self.location_input),
            ("District:", self.district_input),
            ("RTO circle Number:", self.off_code_input),
        ]
        for label_text, field in fields:
            field_layout = QHBoxLayout()
            label = QLabel(label_text)
            field_layout.addWidget(label)
            field_layout.addWidget(field)
            field_layout.setStretch(1, 1)
            field_layout.setContentsMargins(0, 0, 0, 0)
            self.details_layout.addLayout(field_layout)

        self.container_layout.addWidget(self.details_frame)

        # Response Frame
        self.response_frame = QFrame()
        self.response_frame.setObjectName("response-frame")
        self.response_layout = QVBoxLayout()
        self.response_frame.setLayout(self.response_layout)

        self.request_details = SmoothTextEdit()
        self.request_details.setReadOnly(True)
        self.response_body = SmoothTextEdit()
        self.response_body.setReadOnly(True)

        self.response_layout.addWidget(QLabel("Request Details:"))
        self.response_layout.addWidget(self.request_details)
        self.response_layout.addWidget(QLabel("Response Body:"))
        self.response_layout.addWidget(self.response_body)

        self.container_layout.addWidget(self.response_frame)

        # Progress Bar
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("progress-frame")
        self.progress_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.progress_layout = QVBoxLayout()
        self.progress_frame.setLayout(self.progress_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

        self.progress_layout.addWidget(self.progress_bar)
        self.progress_frame.hide()

        self.container_layout.addWidget(self.progress_frame)

        # Send Button
        self.send_button = QPushButton("Send Challan")
        self.send_button.clicked.connect(self.send_challan)
        self.main_layout.addWidget(self.send_button)

        # Copyright Notice
        self.copyright_label = QLabel("@with love by sahyam")
        self.copyright_label.setObjectName("copyright")
        self.main_layout.addWidget(self.copyright_label)

        # Apply fade effects
        self.apply_fade_in_effect(self.url_type_frame)
        self.apply_fade_in_effect(self.details_frame)
        self.apply_fade_in_effect(self.response_frame)

        # Example frame transition animation
        self.animate_frame_transition(
            self.details_frame,
            QRect(self.details_frame.geometry()),
            QRect(0, 100, self.details_frame.width(), self.details_frame.height()),
        )
        self.capitalize_first_letter()
        self.location_input.textChanged.connect(self.capitalize_first_letter)
        self.district_input.textChanged.connect(self.capitalize_first_letter)

    def capitalize_first_letter(self):
        for field in [self.location_input, self.district_input]:
            text = field.text()
            if text:
                capitalized_text = text[0].upper() + text[1:]
                if text != capitalized_text:
                    field.setText(capitalized_text)

    def apply_fade_in_effect(self, widget):
        effect = FadeEffect(widget)
        effect.apply_fade_in()

    def animate_frame_transition(self, frame, start_rect, end_rect):
        animation = QPropertyAnimation(frame, b"geometry")
        animation.setDuration(500)
        animation.setStartValue(start_rect)
        animation.setEndValue(end_rect)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()

    def set_auto_dates(self):
        now = datetime.now()
        base_date = now - timedelta(days=2)
        self.violation_time = base_date.strftime("%Y-%m-%d 10:14:45.0")
        self.action_time = base_date.strftime("%Y-%m-%d 10:44:00.0")

    def update_random_ids(self):
        self.transaction_number = (
            f"REAMN{''.join(random.choices(string.digits, k=12))}A{''.join(random.choices(string.digits, k=4))}"
        )
        self.registration_number = f"DL4CQ{''.join(random.choices(string.digits, k=5))}"
        self.equipment_id = f"GTFGF{''.join(random.choices(string.digits, k=5))}"

    def update_url(self):
        index = self.url_type_combo.currentIndex()
        if index == 0:
            self.url = "https://itmschallan.parivahan.gov.in/pushws/api/echallan/pushdata"
            self.offence_id = "4391"
        else:
            self.url = "https://staging.parivahan.gov.in/pushws/api/echallan/pushdata"
            self.offence_id = "9759"

    def scroll_to_widget(self, widget):
        scroll_bar = self.scroll_area.verticalScrollBar()
        widget_rect = widget.rect()
        widget_global_rect = widget.mapToGlobal(widget_rect.topLeft())
        scroll_area_rect = self.scroll_area.viewport().rect()
        scroll_area_global_rect = self.scroll_area.viewport().mapToGlobal(
            scroll_area_rect.topLeft()
        )
        target_position = (
            widget_global_rect.y()
            - scroll_area_global_rect.y()
            + scroll_bar.value()
        )
        target_position = max(0, min(scroll_bar.maximum(), target_position))

        animation_duration = 500
        step_count = 20
        step_size = (target_position - scroll_bar.value()) / step_count

        def scroll_step():
            current_value = scroll_bar.value()
            new_value = int(current_value + step_size)
            if abs(new_value - target_position) < abs(step_size):
                new_value = int(target_position)
            scroll_bar.setValue(new_value)
            if new_value != target_position:
                QTimer.singleShot(animation_duration // step_count, scroll_step)

        scroll_step()

    def send_challan(self):
        self.send_button.setEnabled(False)
        self.update_random_ids()
        self.update_url()

        self.progress_bar.setValue(0)
        self.progress_bar.show()

        payload = {
            "cctvNoticeData": [
                {
                    "offenceId": self.offence_id,
                    "dpCd": "TP",
                    "latitude": 1.0,
                    "transactionNo": self.transaction_number,
                    "userId": self.user_id_input.text(),
                    "regnNo": self.registration_number,
                    "voilationSource": "OSV",
                    "voilationSourceCatg": "Over Speed Violation",
                    "stateCd": "HP",
                    "districtId": self.district_id_input.text(),
                    "location": self.location_input.text(),
                    "district": self.district_input.text(),
                    "offCd": self.off_code_input.text(),
                    "equipmentId": self.equipment_id,
                    "vendorName": "I2V",
                    "vehicleSpeed": 50,
                    "speedLimit": 40,
                    "vehicleWeight": 0,
                    "voilationTime": self.violation_time,
                    "actionTime": self.action_time,
                    "longitude": 1.0,
                    "image1": "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",
                }
            ]
        }

        # Create and start the worker thread
        self.worker = Worker(self.url, payload)
        self.worker.finished.connect(self.on_request_finished)
        self.worker.error.connect(self.on_request_error)
        self.worker.response_received.connect(self.on_response_received)
        self.worker.start()

    def on_response_received(self, response):
        response_text = response.text

        # Update progress bar
        self.progress_bar.setValue(100)

        # Hide progress bar after request
        self.progress_bar.hide()

        # Determine color based on status code category
        if 200 <= response.status_code < 300:
            status_color = "green"
            status_background_color = "#d4edda"
            status_code_text = f"{response.status_code} - Success"
        elif 300 <= response.status_code < 400:
            status_color = "orange"
            status_background_color = "#fff3cd"
            status_code_text = f"{response.status_code} - Redirection"
        elif 400 <= response.status_code < 500:
            status_color = "darkred"
            status_background_color = "#f8d7da"
            status_code_text = f"{response.status_code} - Client Error"
        else:
            status_color = "darkred"
            status_background_color = "#f5c6cb"
            status_code_text = f"{response.status_code} - Server Error"

        status_code_html = f"""
        <div style="
            padding: 15px; 
            margin-bottom: 20px; 
            border: 3px solid {status_color}; 
            background-color: {status_background_color}; 
            border-radius: 8px;
            font-size: 20px;
            font-weight: bold;
            text-align: center;
            color: {status_color};
            ">
            Response Status: {status_code_text}
        </div>
        """

        request_details_html = f"""
        <div style="
            padding: 10px; 
            margin-top: 10px; 
            font-size: 16px;
            line-height: 1.5;
            color: #333;
            ">
            <strong>Request URL:</strong> {self.url}<br>
            <strong>Response Time:</strong> {response.elapsed.total_seconds()} seconds
        </div>
        """

        self.request_details.setHtml(
            f"""
            {status_code_html}
            {request_details_html}
        """
        )

        QTimer.singleShot(0, lambda: self.scroll_to_widget(self.request_details))

        try:
            formatted_response = json.dumps(response.json(), indent=4)
        except (ValueError, json.JSONDecodeError):
            formatted_response = response_text

        if len(formatted_response) > 50:
            self.response_dialog = ResponseDialog(formatted_response)
            self.response_dialog.exec_()
        else:
            self.response_body.setText(formatted_response)
    
    def on_request_finished(self):
        self.send_button.setEnabled(True)  # Re-enable button

    def on_request_error(self, error_message):
        self.send_button.setEnabled(True)  # Re-enable button
        self.response_body.setText(error_message)  # Display error


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChallanSender()
    window.show()
    sys.exit(app.exec_())
