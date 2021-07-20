from setuptools import setup, Extension
#from distutils.core import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension(
        "pegasustools.pgq.cypqubit", ["src/pegasustools/pgq/cypqubit.pyx"],
        extra_compile_args=["-std=c++17"]
    ),
    Extension(
        "pegasustools.pgq.util", ["src/pegasustools/pgq/util.pyx"],
        extra_compile_args=["-std=c++17"]
    ),
    Extension(
        "pegasustools.util.qac", ["src/pegasustools/util/qac.pyx"],
        extra_compile_args=["-std=c++17"]
    ),
    Extension(
        "pegasustools.util.stats", ["src/pegasustools/util/stats.pyx"],
        extra_compile_args=["-std=c++17"]
    ),
    Extension(
        "pegasustools.util.graph", ["src/pegasustools/util/graph.pyx"],
        extra_compile_args=["-std=c++17"]
    )
]

setup(
    name="pegasustools-hmb",
    version="0.0.1",
    author="Humberto Munoz Bauza",
    package_dir={"": "src"},
    packages=["pegasustools"],
    install_requires=[
        "cython",
        "dimod",
        "numpy",
        "pandas",
        "networkx",
        "dwave_networkx",
        "dwave_system"
    ],
    entry_points={
        'console_scripts': [
            'pgt-cell = pegasustools.apps.cell_anneal:main',
            'pgt-gen = pegasustools.apps.instance_gen:main',
            'pgt-qac-chain = pegasustools.apps.qac_chain:main',
            'pgt-qac-top = pegasustools.apps.qac_top:main'
        ]
    },
    ext_modules=cythonize(extensions, annotate=True),
)