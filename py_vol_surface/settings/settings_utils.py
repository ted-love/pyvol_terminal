
def get_settings_stylesheets():
    
    QPushButton = """
                              QPushButton {background-color: #464646;
                                           color: white;
                                           border: 1px solid black;
                                           padding: 5px;
                                           }
                              QPushButton:checked {background-color: #9e9e9f;
                                                   color: black;
                                                   }
                            """
    QComboBox = """
                QComboBox {
                    background-color: #464646;
                    color: white;
                }
                QComboBox::drop-down {
                    border-color: #464646;
                    background-color: #464646;
                }
                QComboBox::item {
                    background-color: #464646;
                    color: white; 
                }
                QComboBox::item:selected {
                    background-color:  #9e9e9f;
                    color: black; 
                }
                QComboBox QAbstractItemView {
                    background-color: #464646;
                    color: white; 
                }
                """
    
    QMenu = """
            QMenu::item {
                        background-color: #464646;
                        color: white
                        }
            QMenu::item:selected {
                                background-color: #9e9e9f; 
                                color: black;
                                }
            """


    QToolButton = """
            QToolButton {
                        color: white;
                        background-color: #464646;
                        }
                        
            QToolButton::selected {
                                    color: black;
                                    background-color: #9e9e9f;
                                    }

            QToolButton::hover {
                                    color: black;
                                    background-color: #9e9e9f;
                                    }

            """


    style_sheet_dict = {"QPushButton" : QPushButton,
                        "QComboBox" : QComboBox,
                        "QMenu" : QMenu,
                        "QToolButton" : QToolButton}
    

    
    
    
    return style_sheet_dict