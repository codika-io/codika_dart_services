class DartAnalyzerError(Exception):
    """Exception raised when there is an error analyzing Dart code."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)