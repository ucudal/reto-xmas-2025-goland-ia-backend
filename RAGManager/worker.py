#!/usr/bin/env python3
"""
Worker entry point for document processing.

This script starts the RabbitMQ consumer that processes document upload messages.
"""

from app.workers.document_worker import start_worker

if __name__ == "__main__":
    start_worker()

