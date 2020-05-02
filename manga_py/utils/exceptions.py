__all__ = [
    'CantWriteFileException',
    'BackgroundImageExtractException',
]


class CantWriteFileException(Warning):
    def __init__(self, path: str):
        self.path = path


class BackgroundImageExtractException(Warning):
    def __init__(self, style: str):
        self.style = style
