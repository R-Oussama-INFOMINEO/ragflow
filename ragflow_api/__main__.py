"""
ragflow_api.__main__
~~~~~~~~~~~~~~~~~~~~

Enables the library to be invoked as a module::

    python -m ragflow_api doctor --url http://localhost:9380
    python -m ragflow_api info
"""

from ragflow_api._doctor import main

main()
