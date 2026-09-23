"""Service layer package.

Import concrete services from their canonical modules. Keeping package import
side-effect free prevents cycles across services, pipeline, and metabolisation.
"""
