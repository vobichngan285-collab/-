"""Shared error category between persistent voice worker and its engine session."""


class VoiceSetupError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)
