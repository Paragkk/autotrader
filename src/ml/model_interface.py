"""
ML Model Interface Stub
"""

from abc import ABC, abstractmethod


class MLModel(ABC):
    @abstractmethod
    def predict(self, data: object) -> object:
        pass
