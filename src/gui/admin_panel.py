"""
MODUŁ 6: PANEL ADMINISTRACYJNY
GUI for managing accounts
"""

import sys
import asyncio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QTextEdit, QLabel, QSplitter,
    QGroupBox, QListWidgetItem, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from src.main import KwasnyLogManager


class WorkerThread(QThread):
    """Worker thread for async operations"""
    finished = pyqtSignal(object)
    progress = pyqtSignal(str)
    
    def __init__(self, manager, account_id=None):
        super().__init__()
        self.manager = manager
        self.account_id = account_id
    
    def run(self):
        """Run the async operation"""
        try:
            if self.account_id:
                # Process single account
                result = asyncio.run(self.manager.process_single_account(self.account_id))
            else:
                # Process all accounts
                result = asyncio.run(self.manager.process_all_accounts(parallel=False))
            
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({'error': str(e)})


class AdminPanel(QMainWindow):
    """
    Main admin panel GUI
    Structure:
    - Left: Account list
    - Right: Account details
    - Top: Control buttons
    """
    
    def __init__(self):
        super().__init__()
        
        # Initialize manager
        self.manager = KwasnyLogManager()
        self.current_account_id = None
        self.worker = None
        
        self.init_ui()
        self.load_accounts()
    
    def init_ui(self):
        """Initialize UI components"""
        self.setWindowTitle("KWASNY LOG MANAGER - Panel Administracyjny")
        self.setGeometry(100, 100, 1400, 900)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Top control panel
        control_group = self.create_control_panel()
        main_layout.addWidget(control_group)
        
        # Splitter for left and right panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Account list
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel: Account details
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set splitter sizes (1:2 ratio)
        splitter.setSizes([400, 800])
        
        main_layout.addWidget(splitter)
        
        # Status bar
        self.statusBar().showMessage("Gotowy")
        
        # Apply stylesheet
        self.apply_stylesheet()
    
    def create_control_panel(self):
        """Create top control panel"""
        group = QGroupBox("Kontrola")
        layout = QHBoxLayout()
        
        # Buttons
        self.btn_initialize = QPushButton("🔄 Inicjalizuj System")
        self.btn_initialize.clicked.connect(self.initialize_system)
        
        self.btn_process_all = QPushButton("▶️ Start Wszystkich")
        self.btn_process_all.clicked.connect(self.process_all_accounts)
        
        self.btn_stop = QPushButton("⏸️ Stop")
        self.btn_stop.setEnabled(False)
        
        self.btn_refresh = QPushButton("🔄 Odśwież")
        self.btn_refresh.clicked.connect(self.load_accounts)
        
        # Statistics labels
        self.lbl_total_accounts = QLabel("Kont: 0")
        self.lbl_total_profit = QLabel("Zysk: $0.00")
        
        # Add to layout
        layout.addWidget(self.btn_initialize)
        layout.addWidget(self.btn_process_all)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_refresh)
        layout.addStretch()
        layout.addWidget(self.lbl_total_accounts)
        layout.addWidget(self.lbl_total_profit)
        
        group.setLayout(layout)
        return group
    
    def create_left_panel(self):
        """Create left panel with account list"""
        group = QGroupBox("Lista Kont")
        layout = QVBoxLayout()
        
        # Account list
        self.account_list = QListWidget()
        self.account_list.itemClicked.connect(self.on_account_selected)
        layout.addWidget(self.account_list)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        btn_process = QPushButton("▶️ Przetwórz")
        btn_process.clicked.connect(self.process_selected_account)
        
        btn_details = QPushButton("📊 Szczegóły")
        btn_details.clicked.connect(self.show_account_details)
        
        btn_layout.addWidget(btn_process)
        btn_layout.addWidget(btn_details)
        
        layout.addLayout(btn_layout)
        
        group.setLayout(layout)
        return group
    
    def create_right_panel(self):
        """Create right panel with account details"""
        group = QGroupBox("Szczegóły Konta")
        layout = QVBoxLayout()
        
        # Details text area
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.details_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        group.setLayout(layout)
        return group
    
    def apply_stylesheet(self):
        """Apply custom stylesheet"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QGroupBox {
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 5px 15px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QListWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
            }
            QListWidget::item:selected {
                background-color: #0d47a1;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                border: 1px solid #555555;
                font-family: 'Courier New';
            }
            QLabel {
                color: #ffffff;
                font-weight: bold;
                padding: 5px;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 3px;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #0d47a1;
            }
        """)
    
    def load_accounts(self):
        """Load accounts into the list"""
        self.account_list.clear()
        accounts = self.manager.database.get_all_accounts(active_only=False)
        
        for account in accounts:
            # Create list item
            status_icon = "✅" if account['active'] else "❌"
            text = f"{status_icon} {account['email']}"
            
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, account['id'])
            
            # Color coding based on status
            if account['email_status'] == 'POCZTA_DZIAŁA':
                item.setForeground(QColor("#00ff00"))
            elif account['email_status'] in ['BŁĘDNE_HASŁO', 'KONTO_NIEISTNIEJE']:
                item.setForeground(QColor("#ff0000"))
            else:
                item.setForeground(QColor("#ffff00"))
            
            self.account_list.addItem(item)
        
        # Update statistics
        self.update_statistics()
        
        self.statusBar().showMessage(f"Załadowano {len(accounts)} kont")
    
    def update_statistics(self):
        """Update global statistics display"""
        accounts = self.manager.database.get_all_accounts(active_only=True)
        self.lbl_total_accounts.setText(f"Kont: {len(accounts)}")
        
        global_stats = self.manager.financial_calculator.get_global_statistics()
        self.lbl_total_profit.setText(f"Zysk: ${global_stats['total_profit']:.2f}")
    
    def on_account_selected(self, item):
        """Handle account selection"""
        self.current_account_id = item.data(Qt.ItemDataRole.UserRole)
        self.show_account_details()
    
    def show_account_details(self):
        """Display details for selected account"""
        if not self.current_account_id:
            return
        
        # Get account details
        account = self.manager.database.get_account(self.current_account_id)
        if not account:
            return
        
        # Build details text
        details = []
        details.append("="*60)
        details.append(f"KONTO: {account['email']}")
        details.append("="*60)
        details.append("")
        
        # Status
        details.append(f"Status Email: {account['email_status']}")
        details.append(f"Status Facebook: {account['facebook_status']}")
        details.append(f"Aktywne: {'Tak' if account['active'] else 'Nie'}")
        details.append(f"Ostatnia kontrola: {account['last_check'] or 'Nigdy'}")
        details.append("")
        
        # Financial summary
        details.append(self.manager.financial_calculator.format_account_summary(self.current_account_id))
        details.append("")
        
        # Recent logs
        details.append("="*60)
        details.append("OSTATNIA AKTYWNOŚĆ")
        details.append("="*60)
        logs = self.manager.database.get_account_logs(self.current_account_id, limit=10)
        for log in logs:
            details.append(f"[{log['timestamp']}]")
            details.append(f"  Akcja: {log['action']}")
            details.append(f"  Status: {log['status']}")
            if log['details']:
                details.append(f"  Szczegóły: {log['details']}")
            if log['duration']:
                details.append(f"  Czas: {log['duration']:.2f}s")
            details.append("")
        
        self.details_text.setPlainText("\n".join(details))
    
    def initialize_system(self):
        """Initialize system with config files"""
        try:
            self.manager.initialize_system()
            self.load_accounts()
            QMessageBox.information(self, "Sukces", "System zainicjalizowany!")
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Błąd inicjalizacji: {e}")
    
    def process_selected_account(self):
        """Process selected account"""
        if not self.current_account_id:
            QMessageBox.warning(self, "Uwaga", "Wybierz konto z listy")
            return
        
        self.details_text.append("\n🔄 Rozpoczynam przetwarzanie...\n")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        
        # Start worker thread
        self.worker = WorkerThread(self.manager, self.current_account_id)
        self.worker.finished.connect(self.on_process_finished)
        self.worker.start()
        
        self.btn_process_all.setEnabled(False)
        self.statusBar().showMessage("Przetwarzanie...")
    
    def process_all_accounts(self):
        """Process all accounts"""
        self.details_text.append("\n🔄 Rozpoczynam przetwarzanie wszystkich kont...\n")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        # Start worker thread
        self.worker = WorkerThread(self.manager, None)
        self.worker.finished.connect(self.on_process_finished)
        self.worker.start()
        
        self.btn_process_all.setEnabled(False)
        self.statusBar().showMessage("Przetwarzanie wszystkich kont...")
    
    def on_process_finished(self, result):
        """Handle process completion"""
        self.progress_bar.setVisible(False)
        self.btn_process_all.setEnabled(True)
        
        if isinstance(result, dict) and 'error' in result:
            self.details_text.append(f"\n❌ Błąd: {result['error']}\n")
            self.statusBar().showMessage("Błąd!")
        else:
            self.details_text.append("\n✅ Przetwarzanie zakończone!\n")
            self.statusBar().showMessage("Gotowy")
            self.load_accounts()
            if self.current_account_id:
                self.show_account_details()


def main():
    """Main entry point for GUI"""
    app = QApplication(sys.argv)
    panel = AdminPanel()
    panel.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
