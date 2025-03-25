from PySide6 import QtWidgets, QtCore, QtGui
from datetime import datetime   
import numpy as np
import copy
from . import tables_utils
import time


class VolTable(QtWidgets.QTableWidget):
    def __init__(self, data_container_manager, tick_label_engine=None, parent=None):
        self.data_container_manager=data_container_manager
        self.tick_label_engine=tick_label_engine
        self.column_items=[]
        self.row_items=[]
        
        self.init_xy_data(data_container_manager)

        super().__init__(self.rows, self.columns, parent)
        self.setHorizontalHeaderLabels(self.column_vals)
        self.setVerticalHeaderLabels(self.row_vals)
        self.update_table()

    def init_xy_data(self, data_container_manager):
        self.domain_mid = data_container_manager.objects["mid"].domain
        
        self.row_vals = self.domain_mid.y_vect
        self.column_vals = self.domain_mid.x_vect
        self.rows = self.row_vals.size
        self.columns = self.column_vals.size
        
        self.column_vals=[self.tick_label_engine.x_func(new_val) for new_val in self.column_vals]
        self.row_vals=[self.tick_label_engine.y_func(new_val) for new_val in self.row_vals]

    def update_table(self):
        self.blockSignals(True)
        self.setUpdatesEnabled(False)        
        for idx in range(self.domain_mid.z_mat.shape[0]):
            for jdx in range(self.domain_mid.z_mat.shape[1]):
                new_val_str = self.tick_label_engine.z_func(self.domain_mid.z_mat[idx,jdx])
                item = QtWidgets.QTableWidgetItem(new_val_str)
                self.setItem(idx, jdx, item)
        
        self.blockSignals(False)
        self.setUpdatesEnabled(True)
    
    def _update_table_labels(self):
        self.row_vals = self.domain_mid.y_vect
        self.column_vals = self.domain_mid.x_vect
        self.rows = self.row_vals.size
        self.columns = self.column_vals.size
        
        self.setColumnCount(self.columns)
        self.setRowCount(self.rows)
        
        new_cols=[self.tick_label_engine.x_func(new_val) for new_val in self.column_vals]
        self.setHorizontalHeaderLabels(new_cols)
        
        new_rows=[self.tick_label_engine.y_func(new_val) for new_val in self.row_vals]
        self.setVerticalHeaderLabels(new_rows)


class OptionMonitorTable(QtWidgets.QWidget):
    def __init__(self, instrument_manager, parent=None):
        super().__init__(parent)
        self.instrument_manager=instrument_manager
        self.KT_instrument_obj_map = {}
        self.instrument_obj_textitem_maps = {}        
        self.data_cols = ['Instrument Name', 'Bid', 'Ask', 'Mid', "IVOL"]
        self.n_data_cols = len(self.data_cols)

        self.default_strikes = 5
        self.n_strikes_per_expiry = {}
        self.expiry_strike_map = {}
        self.idx_text_item = {}
        self.expiry_combobox_map = {}
        self.max_strikes_per_expiry = {expiry : len(strike_arr) for expiry, strike_arr in self.instrument_manager.options_maps.expiry_strike_map.items()}
        
        if len(self.instrument_manager.spot) > 0:
            self.spot_name = list(self.instrument_manager.spot.keys())[0]
            
            self.spot_object = list(self.instrument_manager.spot.values())[0]
            
            self.spot_qlabel = QtWidgets.QLabel(f"{self.spot_name}: {self.spot_object.mid}")
            self.spot_qlabel.setStyleSheet("""
                                            QLabel {
                                                    background-color: black;
                                                    color: #fb8b1e;
                                            }
                                            """)
            self.spot_qlabel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        all_strikes = list(self.instrument_manager.options_maps.strike_expiry_map.keys())
        self.strike_center = 0.5 * (np.amin(all_strikes) + np.amax(all_strikes))
        
        self.n_strikes_per_expiry = {expiry : self.default_strikes if n_strikes >= self.default_strikes else n_strikes for expiry, n_strikes in self.max_strikes_per_expiry.items()}
        self.row_start_idx_per_expiry = {}
        
        cum_row_idx = 0
        for idx, (expiry, n_strikes) in enumerate(self.n_strikes_per_expiry.items()):
            if idx == 0:
                self.row_start_idx_per_expiry[expiry] = 0
            else:
                self.row_start_idx_per_expiry[expiry] = cum_row_idx
            
            cum_row_idx += 1 + n_strikes
            
        self.n_rows_option_table = 1 + cum_row_idx
        self.n_cols_option_table = 1 + 2 * len(self.data_cols)
                
        self.v_layout = QtWidgets.QVBoxLayout(self)
        
        self.metric_columns = [metric.lower() for metric in self.data_cols[1:]]
        self._subsample_instrument_manager()
        self.setup_parent_table(self.data_cols)
        self.create_child_table_rows()

        self.option_table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.option_table.horizontalHeader().setSectionResizeMode(len(self.data_cols)+1, QtWidgets.QHeaderView.Stretch)
    
    def update_spot_text(self):
        self.spot_qlabel.setText(f"{self.spot_name}:  {f"{self.spot_object.mid:,.2f}"}")
    
    def _get_closest_n_strikes(self, strike_arr, n_strikes_filter):
        differences = np.abs(self.strike_center - strike_arr)
        closest_indices = np.argsort(differences)[:n_strikes_filter]
        strike_arr = strike_arr[closest_indices]
        strike_arr.sort()
        return strike_arr

    def _create_strike_put_call_object_dict(self, expiry, strike_arr):
        strike_put_call_object_dict = {}
        
        for strike in strike_arr:
            instrument_list = self.instrument_manager.options_maps.expiry_strike_instrument_map[expiry][strike]
            
            if len(instrument_list) == 1:
                raise KeyError(f"No put-call pair for {instrument_list[0]}")
            
            instrument_name = instrument_list[0]
            
            option_object = self.instrument_manager.options[instrument_name]
            self.instrument_manager_subsampled.options[instrument_name] = option_object
            if option_object.flag_int == 1:
                put_name = self.instrument_manager.options_maps.put_call_map[instrument_name]
                put_object = self.instrument_manager.options[put_name]
                
                self.instrument_manager_subsampled.options[put_name] = put_object
                strike_put_call_object_dict[strike] = {"call" : option_object,
                                                            "put": put_object}
            else:
                call_name = self.instrument_manager.options_maps.put_call_map[instrument_name]
                call_object = self.instrument_manager.options[call_name]
                self.instrument_manager_subsampled.options[call_name] = call_object

                strike_put_call_object_dict[strike] = {"call" : call_object,
                                                            "put": option_object}
        return strike_put_call_object_dict 
    
    def _subsample_instrument_manager(self):
        self.instrument_manager_subsampled = copy.deepcopy(self.instrument_manager)
        self.instrument_manager_subsampled.options = {}
        
        self.expiry_strike_put_call_object = {}
        
        for expiry, strike_arr in self.instrument_manager.options_maps.expiry_strike_map.items():
            strike_arr = self._get_closest_n_strikes(strike_arr, self.n_strikes_per_expiry[expiry])
            self.expiry_strike_map[expiry] = strike_arr 
            strike_put_call_object_dict = self._create_strike_put_call_object_dict(expiry, strike_arr)

            self.expiry_strike_put_call_object[expiry] = strike_put_call_object_dict
                        
        self.instrument_manager_subsampled.update_option_attr_maps()
    
    def _create_header_title(self, category):
        label = QtWidgets.QLabel(category)
        label.setStyleSheet(tables_utils.get_style_sheets()["QLabel"])
        font = QtGui.QFont("Neue Haas Grotesk", 14)
        font.setBold(True)
        label.setFont(font)
        return label

    def _create_header_tables(self):
        self.header_layout = QtWidgets.QHBoxLayout()

        h_c = self._create_header_title("Calls")
        h_s = self._create_header_title("Strike")
        h_p = self._create_header_title("Puts")

        h_s.setStyleSheet(tables_utils.get_style_sheets()["QLabel"])
        h_p.setStyleSheet(tables_utils.get_style_sheets()["QLabel"])

        for label in [h_c, h_s, h_p]:
            label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
            label.setAlignment(QtCore.Qt.AlignCenter)
            
        self.header_layout.addWidget(h_c)
        self.header_layout.addWidget(h_s)
        self.header_layout.addWidget(h_p)
        return self.header_layout
    
    def setup_parent_table(self, data_cols):
        self.header_layout=self._create_header_tables()
        self.option_table = QtWidgets.QTableWidget()
        self.option_table.setShowGrid(False)
        self.option_table.verticalHeader().setVisible(False)
        self.option_table.horizontalHeader().setVisible(True)
        self.option_table.setItemDelegate(tables_utils.CustomDelegate())
        
        self.option_table.setStyleSheet("""
                                        QTableView {border-style: none;
                                                    background-color: black;
                                                    padding: 0px;
                                                    margin: 0px; 
                                                    border-left: 2px solid #414141;
                                                    border-right: 2px solid #414141;
                                                    }
                                        QTableWidget::item:selected {background-color: #414141;
                                                                    }
                                        
                                        QTableWidgetItem {
                                            border-radius: 0px; 
                                            border: 1px solid black;
                                        }
                                        
                                        
                                        """
                                        )   
        self.option_table.horizontalHeader().setSectionsClickable(True)
        self.option_table.setAutoFillBackground(False)
        
        self.option_table.setRowCount(self.n_rows_option_table)
        self.option_table.setColumnCount(self.n_cols_option_table)
        
        column_names = data_cols  + [""] + data_cols

        for idx, col in enumerate(column_names):
            col_item = tables_utils.TableColumnItem(col)
            if idx == 0 or idx == len(data_cols) + 1:
                col_item.setTextAlignment(QtCore.Qt.AlignLeft)
                font = QtGui.QFont("Neue Haas Grotesk", 14)
                col_item.setFont(font)
                
            self.option_table.setHorizontalHeaderItem(idx, col_item)
        
        header = self.option_table.horizontalHeader()
        header.sectionResized.connect(self.update_header_stretch)
        
        self.v_layout.addLayout(self.header_layout)
        self.v_layout.addWidget(self.option_table)
        self.update_header_stretch()      
    

    def update_header_stretch(self, *args):
        sum_calls = sum(self.option_table.columnWidth(i) for i in range(self.n_data_cols))
        #strikes_width = self.option_table.columnWidth(5)
        sum_puts = sum(self.option_table.columnWidth(i) for i in range(self.n_data_cols+1, int(2*self.n_data_cols + 1)))

        self.header_layout.setStretch(0, sum_calls)
        #self.header_layout.setStretch(1, strikes_width)
        self.header_layout.setStretch(2, sum_puts)
        
    def update_table(self):
        self.blockSignals(True)
        self.setUpdatesEnabled(False)        
        for instrument_name, option_object in self.instrument_manager_subsampled.options.items():
            if instrument_name in self.instrument_obj_textitem_maps:
                text_item_dict = self.instrument_obj_textitem_maps[instrument_name]
                for metric, text_item in text_item_dict.items(): 
                    val = getattr(option_object, metric)
                    if metric == "ivol":
                        val = val[2]
                        if val != val and not option_object.OTM:
                            if option_object.flag_int == 1:
                                put_instrument_name = self.instrument_manager_subsampled.options_maps.put_call_map[instrument_name]
                                val = self.instrument_manager_subsampled.options[put_instrument_name].ivol[2]
                                text_item.setText(f"{(np.round(val, 2))}*")
                                continue
                                
                    text_item.setText(str(np.round(val, 2)))
            else:
                print(f"\n{instrument_name} not in self.instrument_obj_textitem_maps")
                

        self.blockSignals(False)
        self.setUpdatesEnabled(True)        

    def _create_text_item_expiry(self, expiry):
        text_item = tables_utils.OptionExpiryCellItem(datetime.fromtimestamp(expiry).strftime("%d-%b-%y"))
        font_call = text_item.font()
        font_call.setPointSize(12)
        text_item.setFont(font_call)
        return text_item
    
    def change_center(self, center):
        center = float(center)
        self.strike_center = center
        
        
        self.create_child_table_rows()
        
    def _create_text_item_instrument_name(self, expiry, strike, option_type):
        option_object = self.expiry_strike_put_call_object[expiry][strike][option_type]
        text_item = tables_utils.OptionNameCellItem(str(option_object.instrument_name))
        return text_item, option_object
    
    def _create_text_item_metric(self, metric, option_object):
        metric_value = getattr(option_object, metric)
        if metric == "ivol":
            metric_value = metric_value[2]
        if metric_value != metric_value:
            metric_value=str(metric_value)
        else:
            metric_value=str(np.round(metric_value,2 ))
        text_item = tables_utils.OptionMetricCellItem(metric_value)
        return text_item
    
    def _create_expiry_row_text_items(self, option_table, expiry, idx_expiry, n_strikes):
        text_item_call = self._create_text_item_expiry(expiry)
        text_item_put = self._create_text_item_expiry(expiry)
                
        option_table.setItem(idx_expiry, 0, text_item_call)
        option_table.setItem(idx_expiry, self.n_data_cols + 1, text_item_put)
        
        for k, _ in enumerate(self.metric_columns):
            blank_text_item1 = tables_utils.BlankCellItem()
            blank_text_item2 = tables_utils.BlankCellItem()
            option_table.setItem(idx_expiry, 1 + k , blank_text_item1)
            option_table.setItem(idx_expiry, 1 + self.n_data_cols + 1 + k , blank_text_item2)

    def _create_strike_row_text_items(self, option_table, expiry, strike, idx_expiry, idx_strike):
        
        name_text_item_call, call_object = self._create_text_item_instrument_name(expiry, strike, "call")
        name_text_item_put, put_object = self._create_text_item_instrument_name(expiry, strike, "put")

        text_item_strike = tables_utils.OptionMetricCellItem(str(strike))
        text_item_strike.setTextAlignment(QtCore.Qt.AlignCenter)
        text_item_strike.setForeground(QtGui.QBrush("white"))
        
        option_table.setItem(idx_expiry + idx_strike, 0, name_text_item_call)
        option_table.setItem(idx_expiry + idx_strike, self.n_data_cols, text_item_strike)
        option_table.setItem(idx_expiry + idx_strike, self.n_data_cols + 1, name_text_item_put)
        
        return call_object, put_object

    def _create_metric_row_text_item(self, option_table, call_object, put_object, metric, idx_expiry, idx_strike, jdx_metric):
        text_item_call = self._create_text_item_metric(metric, call_object)
        text_item_put = self._create_text_item_metric(metric, put_object)
        
        option_table.setItem(idx_expiry + idx_strike, jdx_metric, text_item_call)
        option_table.setItem(idx_expiry + idx_strike, jdx_metric + self.n_data_cols + 1, text_item_put)
        
        return text_item_call, text_item_put
    
    def create_child_table_rows(self):
        self.idx_text_item = []

        for expiry, strikes_arr in self.expiry_strike_map.items():
            idx_expiry = self.row_start_idx_per_expiry[expiry]
            
            select_strikes_combobox = self.create_combobox(idx_expiry, len(strikes_arr), self.max_strikes_per_expiry[expiry], expiry)
            self.option_table.setCellWidget(idx_expiry, self.n_data_cols, select_strikes_combobox)

            self._create_expiry_row_text_items(self.option_table, expiry, idx_expiry, len(strikes_arr))
            
            for idx_strike, strike in enumerate(strikes_arr, start=1):                
                call_object, put_object = self._create_strike_row_text_items(self.option_table, expiry, strike, idx_expiry, idx_strike)
                call_metric_dict = {}
                put_metric_dict = {}
                
                for jdx_metric, metric in enumerate(self.metric_columns, start=1):
                    text_item_call, text_item_put = self._create_metric_row_text_item(self.option_table, call_object, put_object, metric, idx_expiry, idx_strike, jdx_metric)
                    call_metric_dict[metric] = text_item_call
                    put_metric_dict[metric] = text_item_put

                self.instrument_obj_textitem_maps[call_object.instrument_name] = call_metric_dict
                self.instrument_obj_textitem_maps[put_object.instrument_name] = put_metric_dict

    def update_child_table_rows(self, expiry_update):
        for expiry, strikes_arr in self.expiry_strike_map.items():
            if expiry == expiry_update:
                idx_expiry = self.row_start_idx_per_expiry[expiry]
                self._create_expiry_row_text_items(self.option_table, expiry, idx_expiry, len(strikes_arr))
                for idx_strike, strike in enumerate(strikes_arr, start=1):                
                    call_object, put_object = self._create_strike_row_text_items(self.option_table, expiry, strike, idx_expiry, idx_strike)
                    call_metric_dict = {}
                    put_metric_dict = {}
                    
                    for jdx_metric, metric in enumerate(self.metric_columns, start=1):
                        text_item_call, text_item_put = self._create_metric_row_text_item(self.option_table, call_object, put_object, metric, idx_expiry, idx_strike, jdx_metric)
                        call_metric_dict[metric] = text_item_call
                        put_metric_dict[metric] = text_item_put

                    self.instrument_obj_textitem_maps[call_object.instrument_name] = call_metric_dict
                    self.instrument_obj_textitem_maps[put_object.instrument_name] = put_metric_dict
                    
    def create_combobox(self, idx, default_n_strikes, max_n_strikes, expiry):
        combobox = tables_utils.StrikeOptionsComboBox(strikes=max_n_strikes,
                                                      default_n_strike=default_n_strikes,
                                                      expiry=expiry,
                                                      table_idx=idx)
        for s in range(1, max_n_strikes+1):
            combobox.addItem(str(s))
        
        combobox.setCurrentText(str(default_n_strikes))
        self.expiry_combobox_map[expiry] = combobox
        
        combobox.currentTextChanged.connect(lambda selected_text: self.change_strikes(selected_text, combobox))
        return combobox
    
    def add_strikes(self, new_n_strikes, expiry, combobox):
        total_strikes_4_expiry = self.instrument_manager.options_maps.expiry_strike_map[expiry]
        self.n_strikes_per_expiry[expiry] = new_n_strikes
        
        instruments_to_remove = self.instrument_manager_subsampled.options_maps.expiry_instrument_map[expiry]
        for instrument_name in instruments_to_remove:
            del self.instrument_manager_subsampled.options[instrument_name]

        strike_arr = self._get_closest_n_strikes(total_strikes_4_expiry, new_n_strikes)
        self.expiry_strike_map[expiry] = strike_arr 
        strike_put_call_object_dict = self._create_strike_put_call_object_dict(expiry, strike_arr)

        self.expiry_strike_put_call_object[expiry] = strike_put_call_object_dict
        n_strike_increase = new_n_strikes - combobox.current_n_strikes
        
        if n_strike_increase > 0:
            for i in range(n_strike_increase):
                self.option_table.insertRow(combobox.table_idx+1)

        for exp in self.row_start_idx_per_expiry:
            if exp > expiry:
                self.row_start_idx_per_expiry[exp] += n_strike_increase
                self.expiry_combobox_map[exp].table_idx += n_strike_increase
        
        self.instrument_manager_subsampled.update_option_attr_maps()
        self.update_child_table_rows(expiry)
    
    def remove_strikes(self, new_n_strikes, expiry, combobox):
        n_strike_decrease = combobox.current_n_strikes - new_n_strikes
        current_strikes = list(self.expiry_strike_put_call_object[expiry])
        current_strikes = np.sort(current_strikes)
        
        sorted_idx = np.argsort((current_strikes - self.strike_center))
        
        idx_to_keep = sorted_idx[:new_n_strikes]
        idx_to_remove = sorted_idx[new_n_strikes:]

        strikes_to_keep = current_strikes[idx_to_keep]
        strikes_to_remove = current_strikes[idx_to_remove]
        self.expiry_strike_map[expiry] = strikes_to_keep
        
        for strike in strikes_to_remove:
            for instrument_name in self.instrument_manager.options_maps.expiry_strike_instrument_map[expiry][strike]:
                del self.instrument_manager_subsampled.options[instrument_name]

            del self.expiry_strike_put_call_object[expiry][strike]
        self.instrument_manager_subsampled.update_option_attr_maps()
        idx_to_remove.sort()
        idx_to_remove = idx_to_remove[::-1]
        for idx in idx_to_remove:
            self.option_table.removeRow(combobox.table_idx + 1 + idx)
        
        for exp in self.row_start_idx_per_expiry:
            if exp > expiry:
                self.row_start_idx_per_expiry[exp] -= n_strike_decrease
                self.expiry_combobox_map[exp].table_idx -= n_strike_decrease

    def change_strikes(self, new_n_strikes, combobox):
        new_n_strikes = int(float(new_n_strikes))
        self.option_table.blockSignals(True)
        self.option_table.setUpdatesEnabled(False)
        if new_n_strikes == combobox.current_n_strikes:
            return
        else:
            expiry = combobox.expiry
            if new_n_strikes > combobox.current_n_strikes:
                self.add_strikes(new_n_strikes, expiry, combobox)
            else:
                self.remove_strikes(new_n_strikes, expiry, combobox)
        
            combobox.current_n_strikes = new_n_strikes
        
        self.option_table.blockSignals(False)
        self.option_table.setUpdatesEnabled(True)
        
    def bulk_change_strike_num(self, new_strike):
        for expiry, combobox in self.expiry_combobox_map.items():
            if new_strike <= self.max_strikes_per_expiry[expiry]:
                combobox.currentTextChanged.emit(str(new_strike))  
                
                
                
                
                
            
        