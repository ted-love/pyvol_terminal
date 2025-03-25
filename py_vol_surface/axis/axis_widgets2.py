class GridManager:
    def __init__(self, widget=None):
        self.widget=widget
        self.grid_xy, self.grid_yz, self.grid_xz = self._create_grids()
        if not widget is None:
            self._addGrids(widget)
    
    def addWidget(self, widget):
        self.widget=widget
        self._addGrids(self.widget)
    
    def _addGrids(self, widget):
        widget.addItem(self.grid_xy)
        widget.addItem(self.grid_yz)
        widget.addItem(self.grid_xz)
        self.widget=widget
        
    def _create_grid(self, size=(1, 1, 1), spacing=(0.1, 0.1, 0.1), rotation=None, translation=None):
        grid = gl.GLGridItem()
        grid.setSize(*size)
        grid.setSpacing(*spacing)
        if rotation:
            grid.rotate(*rotation)
        
        if translation:
            grid.translate(*translation)
        return grid

    def _create_grids(self):
        self.grid_xy = self._create_grid(
            size=(1, 1, 1),
            spacing=(0.1, 0.1, 0.1),
            translation=(0.5, 0.5, 0)
        )
        
        self.grid_yz = self._create_grid(
            size=(1, 1, 1),
            spacing=(0.1, 0.1, 0.1),
            rotation=(90, 0, 1, 0),
            translation=(0, 0.5, 0.5)
        )
                        
        self.grid_xz = self._create_grid(
            size=(1, 1, 1),
            spacing=(0.1, 0.1, 0.1),
            rotation=(90, 1, 0, 0),
            translation=(0.5, 1, 0.5)
        )
        return self.grid_xy, self.grid_yz, self.grid_xz
