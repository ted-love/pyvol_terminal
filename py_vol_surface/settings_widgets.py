from PySide6 import QtWidgets

class MainPanel(QtWidgets.QWidget):
    def __init__(self, main_widget=None, parent=None):
        self.main_widget=main_widget
        super().__init__(parent)
        
    def create_settings_objects(self):
        self.setStyleSheet("background-color: white;")
        self.layout = QtWidgets.QHBoxLayout(self)
        
        self.create_change_dimensions_menu()
        
        self.create_toggle_buttons("Toggle Sub-Plots", self.main_widget.toggle_subplots, ["On", "Off"])
        self.create_toggle_buttons("Toggle Crosshairs", self.main_widget.toggle_crosshairs, ["On", "Off"])
        self.create_toggle_buttons("Toggle Price Types", self.main_widget.toggle_price_type, ["bid", "ask", "mid"])
        self.create_toggle_buttons("Toggle 3D Assets", self.main_widget.toggle_3D_objects, ["Surface", "Scatter"])
        
    def create_change_dimensions_menu(self):
        tool_button = QtWidgets.QToolButton(self)
        tool_button.setText("Change Dimensions")
        tool_button.setStyleSheet("QToolButton { color: black; }")

        tool_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        main_menu = QtWidgets.QMenu(self)
        main_menu.setStyleSheet("""
                                QMenu::item { background-color: white; color: black; }
                                QMenu::item:selected { background-color: #3399FF; color: black; }
                                """
                               )

        def _add_submenu(title, options, axis):
            submenu = QtWidgets.QMenu(title, main_menu)
            main_menu.addMenu(submenu)

            for option in options:
                action = submenu.addAction(option)
                action.triggered.connect(lambda checked=False, o=option, a=axis: self.main_widget.switch_axis(o, a) if not self.main_widget.waiting_first_plot else None)
        
        _add_submenu("Money", ["Strike", "Delta", "Moneyness", "Log-Moneyness", "Standardised-Moneyness"], "x")
        _add_submenu("Expiry", ["Expiry", "Years"], "y")
        _add_submenu("Volatility", ["Implied Volatility", "Implied Volatility (%)", "Total Volatility"], "z")

        tool_button.setMenu(main_menu)
        tool_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)

        column_layout = QtWidgets.QVBoxLayout()
        column_layout.addWidget(tool_button)
        self.layout.addLayout(column_layout)
    
    def create_toggle_buttons(self, title, trigger_functions, option_list, *args):
        tool_button = QtWidgets.QToolButton(self)
        tool_button.setText(title)
        tool_button.setStyleSheet("""
                                  QToolButton {
                                               color: black;
                                              }
                                  """)
        tool_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet("""
                            QMenu::item {
                                        background-color: white; 
                                        color: black
                                        }
                            QMenu::item:selected {
                                                background-color: #3399FF; 
                                                color: black;
                                                }
                           """)
        for idx, option in enumerate(option_list):
            action = menu.addAction(option)
            action_args = [arg[idx] for arg in args] if args else []
            action.triggered.connect(lambda checked=False, p=option, a=action_args: trigger_functions(p, *a) if not self.main_widget.waiting_first_plot else None)

        tool_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        tool_button.setMenu(menu)

        column_layout = QtWidgets.QVBoxLayout()
        column_layout.addWidget(tool_button)
        self.layout.addLayout(column_layout)
        self.adjustSize()

