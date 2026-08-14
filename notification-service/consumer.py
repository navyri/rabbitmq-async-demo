"""
Notification Service (Consumer)
--------------------------------
Listens to the 'orders_queue' and simulates sending a notification
(e.g. an email or push notification) for every order that is created.

This process runs independently from the order service. It can be
stopped, restarted, or be slower than usual, and the order service is
never blocked by it -- messages simply wait in the queue.
"""

import json
import logging
import os
import time

import pika
from dotenv import load_dotenv

# Loads variables from a local .env file if one exists (see .env.example).
# .env is never committed to the repo -- see .gitignore.
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [notification-service] %(message)s")
logger = logging.getLogger(__name__)

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

# In-memory set used only to demonstrate idempotency (processing the same
# message twice must be safe). In a real system this should be a durable
# store (Redis, a database table) so it survives a restart -- this is a
# known limitation we call out explicitly in the "limitations" slide.
_processed_order_ids: set[str] = set()


def connect_with_retry(retries: int = 5, delay_seconds: int = 3) -> pika.BlockingConnection:
    params = pika.URLParameters(RABBITMQ_URL)
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return pika.BlockingConnection(params)
        except pika.exceptions.AMQPConnectionError as exc:
            last_error = exc
            logger.warning("RabbitMQ not reachable yet (attempt %s/%s): %s", attempt, retries, exc)
            time.sleep(delay_seconds)
    raise RuntimeError("Could not connect to RabbitMQ") from last_error


def send_notification(order: dict) -> None:
    """Simulates sending an email/push notification for a new order."""
    logger.info(
        "Notification sent to %s: your order %s ($%.2f) was received.",
        order["customer_name"],
        order["order_id"],
        order["total"],
    )


def on_message(channel, method, properties, body):
    try:
        order = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Received a message that is not valid JSON, sending to DLQ")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    order_id = order.get("order_id")

    # Idempotency check: if we already processed this order_id, acknowledge
    # and skip it instead of sending a duplicate notification.
    if order_id in _processed_order_ids:
        logger.info("Order %s already processed, skipping duplicate", order_id)
        channel.basic_ack(delivery_tag=method.delivery_tag)
        return

    try:
        send_notification(order)
        _processed_order_ids.add(order_id)
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:  # noqa: BLE001 - demo-level catch-all is intentional here
        logger.error("Failed to process order %s: %s", order_id, exc)
        # requeue=False sends the message to the dead-letter queue
        # (orders_queue_dlq) instead of retrying it forever.
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    connection = connect_with_retry()
    channel = connection.channel()

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

    # Process one unacknowledged message at a time (fair dispatch).
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue="orders_queue", on_message_callback=on_message)

    logger.info("Waiting for messages on 'orders_queue'. Press CTRL+C to stop.")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
