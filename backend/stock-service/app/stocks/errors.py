class ConnectionFailedError(Exception):
    """Custom Exception raised when a connection attempt fail.
    Use when intending to trigger a retry loop""" 
    def __init__(self, message, code=None):
        self.message = message
        self.code = code
        super().__init__(message)