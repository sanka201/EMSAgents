from abc import ABC, abstractmethod

class Optimizationstrategy(ABC):
    
    def __init__(self) -> None:
        super().__init__()
        
    @abstractmethod
    def optimize(self,model):
        pass