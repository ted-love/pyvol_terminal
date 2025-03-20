import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Signal, QMutex, QMutexLocker  
from PySide6 import QtCore, QtWidgets
from py_vol_surface.axis import axis_utils
from py_vol_surface import misc_widgets
from py_vol_surface import data_objects
import time
import asyncio
from PySide6.QtCore import Qt
from py_vol_surface import workers
from py_vol_surface.plot_views import view_2D, view_3D, plot_views_utils
from py_vol_surface.plotitems_3D import gl_plotitems_utils
from py_vol_surface import settings_widgets
from py_vol_surface import instruments
from py_vol_surface import plotting_engines 
from py_vol_surface import defaults 

QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

class MainWindow(QMainWindow):
    plot_signal = Signal(str)

    def __init__(self, **config):
        super().__init__()
        
        defaults.update_config(config)
                    
        data_config=config["data_config"]
        websocket_config=config["websocket_config"]
        option_config=config["option_config"]
        future_config=config.get("future_config", None)
        self._base_interpolation_config=config["interpolation_config"]
        interest_rate_config=config["interest_rate_config"]
        dividend_rate_config=config["dividend_rate_config"]
        self.colour_styles_config=config["colour_styles_config"]
        data_processing_config=config["data_processing_config"]
        self.starting_price_type=config["starting_price_type"]
        self.plotting_config=config["plotting_config"]
                
        self.last_plot_update = time.time()
        
        self.scatter_flag=True
        self.surface_flag=True
        self.subplots_flag=True
        self.waiting_first_plot=True
        
        self.surface_xaxis_line = None
        self.surface_yaxis_line = None
        self.cross_hairs_on = False
        self.mouse_hover_on = False
        self.info_text_box = None
        self.plotting_flag = False
        self.response_buffer_flag=True

        self.current_price_types = []
        self.plot_interaction_buffer=[]
        self.all_price_types=["bid", "ask", "mid"]

        self.plot_legend_object=None
        self.count=0
        self.counter=0
        self.plot_mutex = QMutex()          
                
        self.data_container_manager, self.instrument_manager, base_domain, self.n_options = self.initData(data_config, option_config, future_config, interest_rate_config, dividend_rate_config)

        self.widget_3D_view = view_3D.CustomGLViewWidget(main_window=self,
                                                        price_type=self.starting_price_type,
                                                        instrument_manager=self.instrument_manager,
                                                        data_container_manager=self.data_container_manager,
                                                        show_spot_text=config["spot_flag"])
        self.plot_signal.connect(self.update_plot)

        self.axis_transform_engine, self.normalisation_engine = self.initEngines(self.instrument_manager, base_domain)
        self.widget_3D_view.normalisation_engine=self.normalisation_engine
        
        self.price_process_worker, self.market_data_worker = self.initWorkers(self.axis_transform_engine,
                                                                              self.normalisation_engine,
                                                                              self.data_container_manager,
                                                                              self.instrument_manager,
                                                                              data_processing_config,
                                                                              interest_rate_config,
                                                                              dividend_rate_config,
                                                                              websocket_config)
        
        self.widget_vol_smile, self.widget_vol_term, self.axis_manager, self.legend, _ = self.initPlots(self.widget_3D_view,
                                                                                                        self.data_container_manager,
                                                                                                        self.normalisation_engine, 
                                                                                                        self.colour_styles_config,
                                                                                                        )
        self.widget_3D_view.axis_manager=self.axis_manager        
        self.initUI(self.widget_3D_view, self.widget_vol_smile, self.widget_vol_term, self.legend)
        self.toggle_price_type(self.starting_price_type)    

        self.showMaximized()
        self.market_data_worker.start()

    def initData(self, data_config, option_config, future_config, interest_rate_config, dividend_rate_config):
        instrument_manager, df_options, _, _ = instruments.create_instrument_objects(data_config,
                                                                                     option_config,
                                                                                     future_config,
                                                                                     interest_rate_config["engine"],
                                                                                     dividend_rate_config["engine"],)
                                                                                                                                     
        data_container_manager, base_domain = data_objects.create_init_dataclasses(df_options, self.all_price_types)
        data_container_manager = data_objects.DataContainerManager(self.all_price_types)
        return data_container_manager, instrument_manager, base_domain, df_options["instrument_name"].unique().size
    
    def initEngines(self, instrument_manager, base_domain):
        if self.instrument_manager.options_1_underlying_flag:
            if len(self.instrument_manager.spot) == 1:
                spot_object=list(self.instrument_manager.spot.values())[0]
            elif len(self.instrument_manager.futures) == 1:
                spot_object=list(self.instrument_manager.futures.values())[0]
        else:
            spot_object=None
        axis_transform_engine = plotting_engines.MetricEngine(base_domain,
                                                              instrument_manager.options_1_underlying_flag,
                                                              spot_object)
        normalisation_engine = plotting_engines.NormalisationEngine()
        return axis_transform_engine, normalisation_engine
        
    def initWorkers(self, axis_transform_engine, normalisation_engine, data_container_manager, instrument_manager, data_processing_config,
                         interest_rate_config, dividend_rate_config, websocket_config):
        
        price_process_worker = workers.PriceProcessor(self,
                                                      axis_transform_engine,
                                                      normalisation_engine,
                                                      instrument_manager,
                                                      data_container_manager,
                                                      data_processing_config["websocket_json_format"],
                                                      interest_rate_config,
                                                      dividend_rate_config,
                                                      timer_process_data=data_processing_config["timer_process_data"])
        
        market_data_worker = workers.WebsocketWorker(**websocket_config)
        market_data_worker.update_signal.connect(self.process_market_data)
        return price_process_worker, market_data_worker
    
    def initPlots(self, GLViewWidget, data_container_manager, normalisation_engine, colour_styles_config):

        IVOL_smile_curve, IVOL_term_curve = plot_views_utils.initialise_plotdataitems(self.all_price_types, colour_styles_config["scatter"])
        n_ticks=[6, 6, 6]
        axis_manager, grid_manager = axis_utils.create_axis_items(GLViewWidget, n_ticks)

        def _create_subplot(*args, **kwargs):
            subplot = view_2D.SubPlot(*args, **kwargs)
            subplot.getViewBox().setAutoVisible(x=False, y=False)
            subplot.setBackground("k") 
            GLViewWidget.add_price_updated_callbacks(subplot.update_plot)
            return subplot
        
        widget_vol_smile = _create_subplot(self,
                                           data_container_manager,
                                           normalisation_engine,
                                           "xz",
                                           IVOL_smile_curve,
                                           GLViewWidget.right_click_signal,
                                           title="Smile",
                                           axisItems={"bottom" : axis_manager.axis_2D_items["x"][0], "left" : axis_manager.axis_2D_items["z"][1]})
        widget_vol_term = _create_subplot(self,
                                           data_container_manager,
                                           normalisation_engine,
                                           "yz",
                                           IVOL_term_curve,
                                           GLViewWidget.right_click_signal,
                                           title="Term Structure",
                                           axisItems={"bottom" : axis_manager.axis_2D_items["y"][0], "left" : axis_manager.axis_2D_items["z"][0]})

        legend=misc_widgets.Legend(colour_styles_config["scatter"], GLViewWidget)
        return widget_vol_smile, widget_vol_term, axis_manager, legend, grid_manager

    def initUI(self, widget_3D_view, widget_vol_smile, widget_vol_term, legend):
        self.setWindowTitle('Volatility Surface')
        self.widget_central = QtWidgets.QWidget()
        self.setCentralWidget(self.widget_central)
        
        self.widget_layout_v_main = QtWidgets.QVBoxLayout(self.widget_central)
        
        self.splitter_v = QtWidgets.QSplitter(Qt.Vertical)  
        self.splitter_h = QtWidgets.QSplitter(Qt.Horizontal)  
        self.splitter_sub_v = QtWidgets.QSplitter(Qt.Vertical)  
        
        self.splitter_sub_v.addWidget(widget_vol_smile)
        self.splitter_sub_v.addWidget(widget_vol_term)
        
        self.blank_surface_widget = QtWidgets.QWidget()
        self.grid_layout = QtWidgets.QGridLayout(self.blank_surface_widget)
        
        self.grid_layout.addWidget(widget_3D_view, 0, 0)
        self.grid_layout.addWidget(legend, 0, 0, alignment=QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeft)

        self.splitter_h.addWidget(self.blank_surface_widget)
        self.splitter_h.addWidget(self.splitter_sub_v)
        self.splitter_h.setStretchFactor(0, 12) 
        self.splitter_h.setStretchFactor(1, 1) 

        self.widget_layout_v_main.addWidget(self.splitter_h)
        
        self.settings_interface = settings_widgets.MainPanel(main_widget=self)
        self.settings_interface.create_settings_objects()
        
        self.splitter_v.addWidget(self.settings_interface)
        self.splitter_v.addWidget(self.splitter_h)
        self.widget_layout_v_main.insertWidget(0, self.splitter_v)
    
    def process_market_data(self, websocket_response, bulk_response=False):
        if self.response_buffer_flag:                
            if bulk_response:
                self.price_process_worker.bulk_response(websocket_response)
            else:
                self.price_process_worker.update_response_buffer(websocket_response[0])
                        
            if self.price_process_worker.check_enough_time():
                self.price_process_worker.update_price_with_buffer()    
        else:
            self.price_process_worker.update_response_buffer(websocket_response[0])
        
        if time.time() - self.last_plot_update > self.plotting_config["timer_update_plot"]:
            if len(self.current_price_types) > 0:
                self.check_normalisation_bounds()
                for price_type in self.current_price_types:
                    self.plot_signal.emit(price_type)
            self.last_plot_update = time.time()
            
    def check_normalisation_bounds(self):
        if self.data_container_manager.features.valid_values_any:
            if self.waiting_first_plot:
                for axis in ["x", "y", "z"]:
                    getattr(self.normalisation_engine, f"create_{axis}_norm")(getattr(self.data_container_manager, f"{axis}_min"),
                                                                              getattr(self.data_container_manager, f"{axis}_max"))
                    self.axis_manager.update_ticks([getattr(self.normalisation_engine, f"{axis}_LB"),
                                                    getattr(self.normalisation_engine, f"{axis}_UB")],
                                                    axis)
                self.waiting_first_plot=False
            else:
                _ = self.plot_changed_cleanup()

    def _check_norm_engine_axis_equiv(self,):  #Unused
        if self.data_container_manager.features.valid_values_any:
            axis_to_check = ["x", "y", "z"]
        else:
            axis_to_check = ["x", "y"]
            
        for axis in axis_to_check:
            LB = getattr(self.normalisation_engine, f"{axis}_LB")
            UB = getattr(self.normalisation_engine, f"{axis}_UB")
            axis_ticks_obj = self.axis_manager
            
            if LB != getattr(axis_ticks_obj, f"{axis}_min") or UB != getattr(axis_ticks_obj, f"{axis}_max"):
                self.axis_manager.update_ticks([LB, UB], axis)
    
    
    def _sanity_checker(self):  #Unused
        self.data_container_manager.calculate_data_limits()
        
        kwargs = {"x_min": self.data_container_manager.x_min, "x_max" : self.data_container_manager.x_max,
                  "y_min": self.data_container_manager.y_min, "y_max" : self.data_container_manager.y_max,}
        
        if self.data_container_manager.features.valid_values_any:
            kwargs["z_min"] = self.data_container_manager.z_min
            kwargs["z_max"] = self.data_container_manager.z_max
            
        axes_requiring_normalisation = self.normalisation_engine.check_and_update_normaliser(**kwargs)
        
        for axis in axes_requiring_normalisation:
            self.truncate_axis(axis, [getattr(self.normalisation_engine, f"{axis}_LB"), getattr(self.normalisation_engine, f"{axis}_UB")])

        self._check_norm_engine_axis_equiv()
        
    def truncate_axis(self, axis_direction, truncation_range):  #Unused
        if axis_direction=="z":
            return
        for price_type, data_container in self.data_container_manager.objects.items():
            data_container = self.data_container_manager.objects[price_type]
            mask = ((getattr(data_container.scatter, axis_direction) > truncation_range[0])
                    &(getattr(data_container.scatter, axis_direction) < truncation_range[1]))
            
            x = data_container.scatter.x[mask]
            y = data_container.scatter.y[mask]
            z = data_container.scatter.z[mask]
            
            data_container.update_dataclasses(x, y, z)
                
        self.data_container_manager.calculate_data_limits()
                    
        self.normalisation_engine.recalculate_parameters([self.data_container_manager.z_min,
                                                          self.data_container_manager.z_max,],
                                                         "z")
        
        getattr(self.normalisation_engine, f"create_truncated_{axis_direction}")(truncation_range)
        self.axis_manager.update_ticks(truncation_range, axis_direction)        
        
        for price_type, price_type_dict in self.widget_3D_view.plot_items.items():        
            for plot_type, plot_object in price_type_dict.items():
                if getattr(self, f"{plot_type}_flag"):
                    data_container = getattr(self.data_container_manager.objects[price_type], plot_type)
                    plot_object.setData(x=data_container.x, y=data_container.y, z=data_container.z)
        
        self.widget_3D_view.update_all_plots()
    
    def toggle_crosshairs(self, state):
        if state=="On":
            self.widget_3D_view.toggle_crosshairs(True)
        else:
            self.widget_3D_view.toggle_crosshairs(False)

    def switch_axis(self, axis_label, axis_direction):
        new_metric = self.axis_transform_engine.generator.label_metric_map[axis_label]
        if getattr(self.axis_transform_engine, f"{axis_direction}_metric") == new_metric:
            return
        else:
            self.axis_transform_engine.switch_axis(new_metric, axis_direction)        
            for price_type in self.current_price_types:
                data_container=self.data_container_manager.objects[price_type]
                x, y, z = self.axis_transform_engine.transform_data(data_container.raw, new_metric, axis_direction)
                data_container.update_dataclasses(x, y, z)
            
            self.data_container_manager.calculate_data_limits()
            
            self._normalisation_process(axis_label, axis_direction)
            
    def force_update_all_plots(self):
        for price_type in self.current_price_types:
            price_type_dict=self.widget_3D_view.plot_items[price_type]
            for plot_type, plot_object in price_type_dict.items():
                if getattr(self, f"{plot_type}_flag"):
                    data_container = getattr(self.data_container_manager.objects[price_type], plot_type)
                    plot_object.setData(x=data_container.x, y=data_container.y, z=data_container.z)
        
    def _normalisation_process(self, axis_label=None, axis_direction=None):
        if self.data_container_manager.features.valid_values_any:
            self.normalisation_engine.calculate_params(*self.data_container_manager.get_limits())
            for axis in ["x", "y", "z"]:
                limits = [getattr(self.normalisation_engine, f"{axis}_LB"), getattr(self.normalisation_engine, f"{axis}_UB")]              
                if axis == axis_direction:
                    self.axis_manager.switch_axis(limits, axis_label, axis)
                else:
                    self.axis_manager.update_ticks(limits, axis)
            self.force_update_all_plots()        
                    
            for widget in (self.widget_vol_smile, self.widget_vol_term):
                widget.update_plots()
 
    def add_price_levels(self, price_type):
        pass    
        
    def toggle_subplots(self, mode):
        if mode == "On" and not self.subplots_flag:
            self.splitter_sub_v.show()
            self.subplots_flag=True
        elif mode == "Off" and self.subplots_flag:
            self.splitter_sub_v.hide()
            self.subplots_flag=False
    
    def plot_changed_cleanup(self):
        if self.data_container_manager.features.valid_values_any:
            axis_req_renorm = self.normalisation_engine.check_value_bounds(*self.data_container_manager.get_limits())
            for axis in axis_req_renorm:
                getattr(self.normalisation_engine, f"create_{axis}_norm")(getattr(self.data_container_manager, f"{axis}_min"),
                                                                        getattr(self.data_container_manager, f"{axis}_max"))
                self.axis_manager.update_ticks([getattr(self.normalisation_engine, f"{axis}_LB"),
                                                getattr(self.normalisation_engine, f"{axis}_UB")], axis)
            return True
        else:
            return False

    def toggle_price_type(self, price_type):       
        if not price_type in self.current_price_types:
            self.current_price_types.append(price_type)
            data_container = data_objects.DataContainer()
            data_container.create_from_scratch(self.n_options, price_type, self.instrument_manager, self.axis_transform_engine,
                                               self._base_interpolation_config, self.colour_styles_config)
            
            self.data_container_manager.add_container(data_container)
            plot_surface_object, plot_scatter_object = gl_plotitems_utils.create_GL_plotitems(price_type, data_container.surface, data_container.scatter, self.normalisation_engine, self.widget_3D_view)

            if not self.scatter_flag:
                plot_scatter_object.hide()

            self.widget_3D_view.addPricePlots(price_type, plot_surface_object, plot_scatter_object)
            self.widget_vol_smile.add_line(price_type)
            self.widget_vol_term.add_line(price_type)
            self.legend.add_legend_item(price_type)
            
            if self.data_container_manager.features.valid_values_any:
                self._normalisation_process()
        else:
            self.current_price_types.remove(price_type)
            self.data_container_manager.remove_container(price_type)
            self.widget_3D_view.removePricePlots(price_type)                            
            self.widget_vol_smile.remove_line(price_type)
            self.widget_vol_term.remove_line(price_type)
            self.legend.remove_legend_item(price_type)
            if len(self.current_price_types) > 0 and self.data_container_manager.features.valid_values_any:
                self._normalisation_process()

    def toggle_3D_objects(self, plot_type):
        plot_type_lower = plot_type.lower()
        if not getattr(self, f"{plot_type_lower}_flag"):
            for price_type, inner_plot_objects in self.widget_3D_view.plot_items.items():
                plot_object = inner_plot_objects[plot_type_lower]
                data_container = getattr(self.data_container_manager.objects[price_type], plot_type_lower)
                plot_object.setData(data_container.x, data_container.y, data_container.z)
                plot_object.show()   
            setattr(self, f"{plot_type_lower}_flag", True)
        else:
            for inner_plot_objects in self.widget_3D_view.plot_items.values():
                plot_object=inner_plot_objects[plot_type_lower]
                plot_object.hide()
            setattr(self, f"{plot_type_lower}_flag", False)

    def _update_surface_plot(self, price_type):
        data_object=self.data_container_manager.objects[price_type].surface
        if data_object.valid_values:
            surface = self.widget_3D_view.plot_items[price_type]["surface"]
            surface.setData(x=data_object.x, y=data_object.y, z=data_object.z)
            self.waiting_first_plot=False
        
    def _update_scatter_plot(self, price_type):
        data_object = self.data_container_manager.objects[price_type].scatter
        if data_object.valid_values:            
            scatter_plot = self.widget_3D_view.plot_items[price_type]["scatter"]
            
            update_params = {'z': data_object.z}

            if scatter_plot.x.size != data_object.x.size or not all(scatter_plot.x == data_object.x):
                update_params['x'] = data_object.x
            if scatter_plot.y.size != data_object.y.size or not all(scatter_plot.y == data_object.y):
                update_params['y'] = data_object.y
            
            scatter_plot.setData(**update_params)
            self.waiting_first_plot=False
    
    def _update_text(self):
        for idx, (spot_name, spot_object) in enumerate(self.instrument_manager.spot.items()):
            if idx==0:
                combined_new_text = f"{spot_name}:  {f"{spot_object.mid:,.2f}"}"
            else:
                new_text_info = f"\n{spot_name}:  {f"{spot_object.mid:,.2f}"}"
                combined_new_text = combined_new_text + new_text_info
        self.widget_3D_view.set_spot_text(f"{combined_new_text}")

    def update_plot(self, price_type):
        if not self.widget_3D_view.interacting:
            if self.surface_flag:
                self._update_surface_plot(price_type)
            if self.scatter_flag:                
                self._update_scatter_plot(price_type)
            if len(self.instrument_manager.spot) > 0:
                self._update_text()
                
            for callback in self.widget_3D_view.price_updated_callbacks:
                callback(price_type)
        else:
            if not price_type in self.plot_interaction_buffer:
                self.plot_interaction_buffer.append(price_type)

    def plot_buffered_plots(self,):
        while self.plot_interaction_buffer:
            self.update_plot(self.plot_interaction_buffer[0])
            del self.plot_interaction_buffer[0]
            
    def update_all_plots(self):
        for price_type in self.current_price_types:
            self.update_plot(price_type)
                        
    def closeEvent(self, event):
        self.market_data_worker.stop()
        if hasattr(self, 'streamer'):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.streamer.close())
        event.accept()

    
def plot_surface(**config):
    app = QApplication(sys.argv)
    mainWin = MainWindow(**config)
    mainWin.show()
    sys.exit(app.exec())
    
