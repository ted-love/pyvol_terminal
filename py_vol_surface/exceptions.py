class CustomWarnings(Warning):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code  

    def __str__(self):
        base_msg = super().__str__()
        return f"[Code {self.code}] {base_msg}" if self.code else base_msg

class InsufficientDataWarning(CustomWarnings):
    def __init__(self, message, code=100):
        super().__init__(message, code)

class InterpolationFitWarning(CustomWarnings):
    def __init__(self, message, code=200):
        super().__init__(message, code)

class InterpolationEvalWarning(CustomWarnings):
    def __init__(self, message, code=300):
        super().__init__(message, code)