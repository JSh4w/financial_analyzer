"""Singleton Pattern to initliase Modal authentication"""
import modal 
from typing import List, Dict, Any 


class ModalSetup:
    """Creates modal app"""
    def __init__(self):
        self.app = modal.App("financial-analyzer")
        self._image = None 
        self.input_queue = None 
        self.output_queue = None 
    
    @property
    def image(self,*installs):

    @image.deleter
    def image(self):
        del self._image

    @image.setter 
    def image(self,py_ver : str ="3.11",*installs):
        pkgs = installs or[
            "torch>=2.0.0",
            "transformers>=4.30.0",
            "scipy>=1.10.0"
            ]
        self._image = (
            modal.Image.debian_slim(python_version=py_ver)
            .pipinstall(
                pkgs
            )
        )




if __name__ == "__main__":
    modal_cls = ModalSetup()