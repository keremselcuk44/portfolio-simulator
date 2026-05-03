import sys

from PyQt6.QtWidgets import QApplication

from src.db import Database
from src.portfolio import PortfolioState
from src.ui import MainWindow
from src.ui.login_dialog import LoginDialog


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Portfolio Simulator")

    db = Database()

    login = LoginDialog(db)
    if login.exec() != LoginDialog.DialogCode.Accepted or login.user_row is None:
        db.close()
        return 0

    state = PortfolioState()
    window = MainWindow(
        state,
        db=db,
        user_id=login.user_row.id,
        username=login.user_row.username,
        session_id=login.session_id,
    )
    window.show()

    return app.exec()
