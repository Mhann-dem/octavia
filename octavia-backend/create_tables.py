"""Utility to create DB tables for local development."""
from app.db import engine, Base
from app import models


def create_all():
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    create_all()
    print("Created tables")
