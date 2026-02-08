from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext
import pybind11

ext_modules = [
    Pybind11Extension(
        "hmm_regime",
        sources=[
            "bindings/hmm_bindings.cpp",
            "src/hmm.cpp",
        ],
        include_dirs=[
            pybind11.get_include(),
            "src",
        ],
        cxx_std=17,
        extra_compile_args=["-O3", "-march=native"],
    ),
]

setup(
    name="hmm_regime",
    version="0.1.0",
    author="Your Name",
    description="Hidden Markov Model for financial regime detection with Student-t emissions",
    long_description=open("README.md").read() if __file__ else "",
    long_description_content_type="text/markdown",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
    python_requires=">=3.7",
    install_requires=[
        "numpy>=1.19.0",
    ],
)
