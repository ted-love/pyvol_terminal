from . import gl_plotitems

def create_GL_plotitems(price_type, surface, scatter, normalisation_engine, widget):
    surface_plotitem = gl_plotitems.glSurface(price_type,
                                              surface,
                                              normalisation_engine,
                                              parent_widget=widget,
                                              shader="shaded")
    
    scatter_plotitem = gl_plotitems.glScatter(price_type,
                                              scatter,
                                              normalisation_engine,   
                                              parent_widget=widget,
                                              size=10)
    surface_plotitem.setGLOptions('opaque')
    return surface_plotitem, scatter_plotitem
