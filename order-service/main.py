"""
Order Service (Producer)
-------------------------
A small FastAPI application that represents the "order" side of an
e-commerce system. It does NOT talk to the notification service directly.
Instead, it publishes an "order.created" event to RabbitMQ and returns
immediately -- this is the asynchronous part of the demo.

Run standalone:
    uvicorn main:app --reload --port 8000
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import pika
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# Loads variables from a local .env file if one exists (see .env.example).
# .env is never committed to the repo -- see .gitignore.
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [order-service] %(message)s")
logger = logging.getLogger(__name__)

# --- Configuration (12-factor style: everything from environment variables) ---
# CloudAMQP provides a single AMQPS connection string that already includes
# the host, TLS port, credentials and vhost. pika.URLParameters parses it.
#
# IMPORTANT: there is no hardcoded fallback on purpose. The service refuses
# to start without a real connection string, so a credential can never be
# accidentally committed to source control again.
RABBITMQ_URL = os.getenv("RABBITMQ_URL")
if not RABBITMQ_URL:
    raise RuntimeError(
        "RABBITMQ_URL is not set. Copy .env.example to .env and paste your "
        "CloudAMQP connection string, or export it directly: "
        "export RABBITMQ_URL='amqps://user:pass@host/vhost'"
    )

EXCHANGE_NAME = os.getenv("EXCHANGE_NAME", "orders_exchange")
ROUTING_KEY = os.getenv("ROUTING_KEY", "order.created")

app = FastAPI(title="Order Service", version="1.0.0")


class OrderRequest(BaseModel):
    customer_name: str = Field(..., examples=["Maria Gomez"])
    items: list[str] = Field(..., examples=[["Wireless Mouse", "USB-C Cable"]])
    total: float = Field(..., gt=0, examples=[49.98])


def get_connection(retries: int = 5, delay_seconds: int = 3) -> pika.BlockingConnection:
    """
    Connect to RabbitMQ with a small retry loop.

    Why this exists: the broker is remote (CloudAMQP), so the very first
    request after a cold start could hit a slow DNS lookup or a brief
    network hiccup. Without a retry loop that first order would be lost.
    This is one of the concrete technical decisions in the analysis slide.
    """
    params = pika.URLParameters(RABBITMQ_URL)
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return pika.BlockingConnection(params)
        except pika.exceptions.AMQPConnectionError as exc:
            last_error = exc
            logger.warning("RabbitMQ not reachable yet (attempt %s/%s): %s", attempt, retries, exc)
            time.sleep(delay_seconds)
    raise RuntimeError(f"Could not connect to RabbitMQ after {retries} attempts") from last_error


def publish_order_created(order: dict) -> None:
    connection = get_connection()
    try:
        channel = connection.channel()

        # Durable exchange + queue + dead-letter queue for failed messages.
        # This mirrors the theory slide (Producer / Exchange / Queue / Binding / Consumer)
        # with a real, runnable configuration.
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="direct", durable=True)
        channel.exchange_declare(exchange="orders_dlx", exchange_type="fanout", durable=True)

        channel.queue_declare(
            queue="orders_queue",
            durable=True,
            arguments={"x-dead-letter-exchange": "orders_dlx"},
        )
        channel.queue_bind(exchange=EXCHANGE_NAME, queue="orders_queue", routing_key=ROUTING_KEY)

        channel.queue_declare(queue="orders_queue_dlq", durable=True)
        channel.queue_bind(exchange="orders_dlx", queue="orders_queue_dlq", routing_key="")

        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=ROUTING_KEY,
            body=json.dumps(order),
            properties=pika.BasicProperties(
                delivery_mode=2,  # persistent message, survives a broker restart
                content_type="application/json",
                message_id=order["order_id"],
            ),
        )
        logger.info("Published order %s to exchange '%s'", order["order_id"], EXCHANGE_NAME)
    finally:
        connection.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/orders", status_code=201)
def create_order(payload: OrderRequest):
    order = {
        "order_id": str(uuid.uuid4()),
        "customer_name": payload.customer_name,
        "items": payload.items,
        "total": payload.total,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        publish_order_created(order)
    except RuntimeError as exc:
        # If the broker is really unreachable, fail loudly instead of
        # pretending the order was queued.
        logger.error("Failed to publish order %s: %s", order["order_id"], exc)
        raise HTTPException(status_code=503, detail="Messaging system unavailable, try again later") from exc

    # Note: the HTTP response returns immediately after publishing.
    # The order service does NOT wait for the notification to be sent --
    # that is the asynchronous behavior this whole demo is about.
    return {"order_id": order["order_id"], "status": "queued"}
