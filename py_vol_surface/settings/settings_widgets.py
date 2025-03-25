from PySide6 import QtWidgets, QtGui
from PySide6.QtCore import Slot
from PySide6 import QtCore
from . import settings_utils


class MainSettings(QtWidgets.QWidget):
    def __init__(self, settings_manager, parent=None):
        self.settings_manager=settings_manager
        super().__init__(parent=parent)
        self._create_top_settings()
        
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

    def _create_top_settings(self):
        
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0 ,0)
        self.button_group = QtWidgets.QButtonGroup()

        self.button_group.setExclusive(True)

        self.buttons = []
        self.selection_labels = ["OMON", "Vol Table", "Surface", "Term", "Skew"]
        self.button_name_maps = {i : name for i, name in enumerate(self.selection_labels)}
        
        for i, label in enumerate(self.selection_labels):
            btn = QtWidgets.QPushButton(label)
            btn.setCheckable(True)
            btn.setStyleSheet(settings_utils.get_settings_stylesheets()["QPushButton"])
            #btn.setFont(QtGui.QFont())
            self.buttons.append(btn)
            self.layout.addWidget(btn)
            self.button_group.addButton(btn, id=i) 
            btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.button_group.buttonClicked.connect(self.settings_manager.on_button_clicked)
        self.button_group.blockSignals(True)  
        self.buttons[2].setChecked(True)     
        self.button_group.blockSignals(False)       
        

class SettingsManager:
    def __init__(self, widget_main=None, splitter_v=None, widget_surface=None, widget_vol_table=None, widget_omon_table=None, main_view_layout=None, surface_tab_widgets=None, splitter_h_surface=None,widget_layout_v_main=None):
        self.widget_main=widget_main
        self.widget_surface=widget_surface
        self.widget_vol_table=widget_vol_table
        self.main_view_layout=main_view_layout
        self.surface_tab_widgets=surface_tab_widgets
        self.viewable_widgets= surface_tab_widgets
        self.widget_omon_table=widget_omon_table
        self.splitter_v=splitter_v
        self.splitter_h_surface=splitter_h_surface
        self.widget_layout_v_main=widget_layout_v_main
        self.prev_btn_id = 2
        
        self.settings_main = MainSettings(self)
        self.settings_surface = SurfaceSettings(widget_main=self.widget_main)
        self.settings_omon_table = OMONSettings(widget_main=self.widget_main, omon_table=self.widget_omon_table, spot_qlabel=self.widget_omon_table.spot_qlabel)
        self.settings_vol_table = VolTableSettings(widget_main=self.widget_main)
        
        self.widget_layout_v_main.insertWidget(0, self.settings_main)
        self.widget_layout_v_main.insertWidget(1, self.settings_surface)
        self.widget_layout_v_main.setStretch(0, 1)
        self.widget_layout_v_main.setStretch(1, 1)
        self.widget_layout_v_main.setStretch(2, 20)
        
        self.prev_subsetting = self.settings_surface
        self.prev_view = self.splitter_h_surface

    @Slot(QtWidgets.QPushButton)
    def on_button_clicked(self, button):
        btn_id = self.settings_main.button_group.id(button)
        if btn_id == self.prev_btn_id:
            return 
        else:
            self.prev_btn_id = btn_id
        self.widget_main.switch_view(self.settings_main.button_name_maps[btn_id])
        
        match btn_id:
            case 0:
                self._switch_layout(self.widget_omon_table, self.settings_omon_table)
            case 1:
                self._switch_layout(self.widget_vol_table, self.settings_vol_table)
            case 2:
                self._switch_layout(self.splitter_h_surface, self.settings_surface)
            case 3:
                self._switch_layout(self.widget_omon_table, self.settings_omon_table)
            case 4:
                self._switch_layout(self.widget_omon_table, self.settings_omon_table)
    
    def _switch_layout(self, figure, settings):
        figure.show()
        settings.show()
        self.prev_subsetting.hide()
        self.prev_view.hide()
        self.widget_layout_v_main.replaceWidget(self.prev_view, figure)
        self.widget_layout_v_main.replaceWidget(self.prev_subsetting, settings)
        self.prev_view=figure
        self.prev_subsetting=settings
        
        
class OMONSettings(QtWidgets.QWidget):
    def __init__(self, widget_main=None, omon_table=None, spot_qlabel=None, parent=None):
        super().__init__(parent)
        self.widget_main=widget_main
        self.omon_table=omon_table
        self.spot_qlabel=spot_qlabel
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0 ,0)
        self.strike_center()
        self.total_num_strikes()
        self.setStyleSheet(""" 
                           background-color: black;
                           """)
        
        self.layout.addWidget(self.spot_qlabel)
        self.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
    
    def create_live_spot_label(self):
        
        self.spot_qlabel = QtWidgets.QLabel("")
        self.spot_qlabel.setStyleSheet("""
                                        QLabel {
                                                background-color: black;
                                                color: #fb8b1e;
                                        }
                                        """)
        self.spot_qlabel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.layout.addWidget(self.spot_qlabel)
        
    def total_num_strikes(self):
        title = QtWidgets.QLabel("Strikes")
        
        title.setStyleSheet("""
                            QLabel {
                                    background-color: black;
                                    color: #fb8b1e;
                            }
                            """)
        
        self.n_strikes_line = QtWidgets.QLineEdit()
        self.n_strikes_line.setText(str(5))
        self.n_strikes_line.setStyleSheet("""
                                            QLineEdit {
                                                background-color: #fb8b1e;
                                                color: black;
                                                
                                            }
                                            QLineEdit:focus {
                                                background-color: #fb8b1e;
                                                border: 2px solid black;
                                            }
                                            QLineEdit::selection {
                                                
                                                background-color:  lightblue;
                                                color: #ffffff;                                  
                                                }
                                            """)
        self.n_strikes_line.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.n_strikes_line.editingFinished.connect(self.n_strike_edit)
        self.layout.addWidget(title)
        self.layout.addWidget(self.n_strikes_line)
        
    def n_strike_edit(self):
        text = self.n_strikes_line.text()
        text = float(text)
        if int(text) == text:
            n_strikes = int(text)
            self.omon_table.bulk_change_strike_num(n_strikes)
            self.n_strikes_line.clearFocus()

    def strike_center(self):
        title = QtWidgets.QLabel("Center")
        title.setStyleSheet("""
                            QLabel {
                                    background-color: black;
                                    color: #fb8b1e;
                            }
                            """)
        self.strike_center_line = QtWidgets.QLineEdit()
        self.strike_center_line.setText(str(self.omon_table.strike_center))
        self.strike_center_line.setStyleSheet("""
                                                QLineEdit {
                                                    background-color: #fb8b1e;
                                                    color: black;
                                                    
                                                }
                                                QLineEdit:focus {
                                                    background-color: #fb8b1e;
                                                    border: 2px solid black;
                                                }
                                                QLineEdit::selection {
                                                    
                                                    background-color:  lightblue;
                                                    color: #ffffff;                                  
                                                    }
                                                """)
        self.strike_center_line.setSizePolicy(QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.strike_center_line.editingFinished.connect(self.strike_center_edit)
        self.layout.addWidget(title)
        self.layout.addWidget(self.strike_center_line)
        
    def strike_center_edit(self):
        text = self.strike_center_line.text()
        self.omon_table.change_center(text)
        self.strike_center_line.clearFocus()

class VolTableSettings(QtWidgets.QWidget):
    def __init__(self, widget_main=None, vol_table=None, parent=None):
        super().__init__(parent)
        self.widget_main=widget_main
        self.vol_table=vol_table
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0 ,0)
        self.create_moneyness_combobox(["Strike", "Delta", "Moneyness", "Log-Moneyness", "Standardised-Moneyness"], widget_main.switch_axis)

    def create_col_filter(self):
        self.line_edit = QtWidgets.QLineEdit()
        self.line_edit.setText("10")  # Set default value
        # Stylesheet for highlight when focused
        self.line_edit.setStyleSheet("""
                                    QLineEdit {
                                        background-color: white;
                                        color: black;
                                    }
                                    QLineEdit:focus {
                                        background-color: #ffffcc;  
                                        border: 2px solid #3366ff;
                                    }
                                """)

        self.line_edit.editingFinished.connect(self.handle_line_edit)
        self.layout.addWidget(self.line_edit)
    
    def create_moneyness_combobox(self, options, action_handler):
        combobox = QtWidgets.QComboBox()
        combobox.setStyleSheet(settings_utils.get_settings_stylesheets()["QComboBox"])

        combobox.blockSignals(True)
        combobox.addItems(options)
        combobox.blockSignals(False)
        combobox.currentTextChanged.connect(lambda text: action_handler(text))
        self.layout.addWidget(combobox)

    def handle_line_edit(self):

        text = self.line_edit.text()
        try:
            value = int(text)
        except ValueError:
            self.line_edit.setText("10")
            value = 10

        if self.widget_main:
            self.widget_main.handle_line_edit_value(value)
        else:
            print(f"Line edit value: {value}")

class SurfaceSettings(QtWidgets.QWidget):
    def __init__(self, widget_main=None, parent=None):
        self.widget_main=widget_main
        super().__init__(parent)
        self.create_settings_objects()
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        
    def create_settings_objects(self):
        self.setStyleSheet("background-color: white;")
                
        self.layout = QtWidgets.QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0 ,0)
        
        self.prev_button=1         
        
        self.create_change_dimensions_menu()
        self.create_toggle_buttons("Toggle Sub-Plots", self.widget_main.toggle_subplots, ["On", "Off"])
        self.create_toggle_buttons("Toggle Crosshairs", self.widget_main.toggle_crosshairs, ["On", "Off"])
        self.create_toggle_buttons("Toggle Price Types", self.widget_main.toggle_price_type, ["bid", "ask", "mid"])
        self.create_toggle_buttons("Toggle 3D Assets", self.widget_main.toggle_3D_objects, ["Surface", "Scatter"])
        
    def create_change_dimensions_menu(self):
        tool_button = QtWidgets.QToolButton(self)
        tool_button.setText("Change Dimensions")
        tool_button.setStyleSheet(settings_utils.get_settings_stylesheets()["QToolButton"])

        tool_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        main_menu = QtWidgets.QMenu(self)
        main_menu.setStyleSheet(settings_utils.get_settings_stylesheets()["QMenu"])

        def _add_submenu(title, options, axis):
            submenu = QtWidgets.QMenu(title, main_menu)
            main_menu.addMenu(submenu)

            for option in options:
                action = submenu.addAction(option)
                action.triggered.connect(lambda checked=False, o=option, a=axis: self.widget_main.switch_axis(o, a) if not self.widget_main.waiting_first_plot else None)
        
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
        tool_button.setStyleSheet(settings_utils.get_settings_stylesheets()["QToolButton"])
        tool_button.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        menu = QtWidgets.QMenu(self)
        menu.setStyleSheet(settings_utils.get_settings_stylesheets()["QMenu"])
        for idx, option in enumerate(option_list):
            action = menu.addAction(option)
            action_args = [arg[idx] for arg in args] if args else []
            action.triggered.connect(lambda checked=False, p=option, a=action_args: trigger_functions(p, *a) if not self.widget_main.waiting_first_plot else None)

        tool_button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        tool_button.setMenu(menu)

        column_layout = QtWidgets.QVBoxLayout()
        column_layout.addWidget(tool_button)
        self.layout.addLayout(column_layout)
        self.adjustSize()




