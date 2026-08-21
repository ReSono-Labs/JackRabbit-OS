"""Domain-memory package.

Import concrete classes from their owning modules. Keeping this initializer
side-effect free prevents the reviewer/contracts boundary from recursively
loading the pipeline during runtime startup.
"""
