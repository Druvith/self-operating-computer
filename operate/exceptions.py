class ModelNotRecognizedException(Exception):
    """Exception raised for unrecognized models.

    Attributes:
        model -- the unrecognized model
        message -- explanation of the error
    """

    def __init__(self, model, message="Model not recognized"):
        self.model = model
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message} : {self.model} "


class APIError(Exception):
    """Exception raised for API errors."""

    def __init__(self, message="API error"):
        self.message = message
        super().__init__(self.message)


class ModelResponseError(Exception):
    """Exception raised for invalid model responses."""

    def __init__(self, message="Invalid model response"):
        self.message = message
        super().__init__(self.message)


class ExecutionError(Exception):
    """Exception raised for errors during operation execution."""

    def __init__(self, message="Execution error"):
        self.message = message
        super().__init__(self.message)

class OCRError(Exception):
    """Exception raised for OCR errors."""

    def __init__(self, message="OCR error"):
        self.message = message
        super().__init__(self.message)