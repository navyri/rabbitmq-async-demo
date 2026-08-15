<p align='center'> 
  <img src="https://capsule-render.vercel.app/api?type=waving&height=200&color=FF6600&text=RabbitMQ%20Async%20Demo&fontColor=FFFFFF&desc=Asynchronous%20Communication%20Between%20Microservices&fontAlignY=30&descAlignY=54"/> 
</p>

<p align="center">
  <a href="https://youtu.be/UeRYxGLPWK0" target="_blank" rel="noopener noreferrer">
    <img
      src="https://64.media.tumblr.com/e29ae5ec2a39de294d8722ecf312b5d3/7b273f38c55d349b-43/s2048x3072/89ad0a543624dcd3dec51c74ab221c6a7d1ec435.pnj"
      alt="Anime image - Watch the presentation video"
      height="350"
    />
  </a>
</p>

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# Asynchronous Communication Between Microservices with RabbitMQ

Minimal, runnable example of **event-driven, asynchronous communication** between two independent microservices, built as material for a university presentation on RabbitMQ.

> **Security note:** this project connects to a cloud-hosted RabbitMQ broker (CloudAMQP). The connection string is a secret and is loaded from a local `.env` file that is **never committed** (see the [Environment variables](#environment-variables) section below). If an earlier version of this repo ever had a real connection string typed directly into the code, rotate that credential from the CloudAMQP dashboard before making the repo public.

This repository contains:

- A producer service (`order-service`) built with FastAPI that exposes `POST /orders` and publishes order-created events.
- A consumer service (`notification-service`), an independent Python worker that listens to those events and simulates sending notifications.
- The configuration of a RabbitMQ broker hosted on CloudAMQP, with an exchange, a main queue, and a dead-letter queue for failed messages.

## Overall repository structure

```bash
rabbitmq-async-demo/
├── README.md
├── order.json
├── .gitignore
├── order-service/
│   ├── .env.example
│   ├── requirements.txt
│   └── main.py
└── notification-service/
    ├── .env.example
    ├── requirements.txt
    └── consumer.py
```

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# First component: order-service (producer)

In this component the producer service was implemented, an API built with FastAPI that receives orders from a client, publishes an `order.created` event to RabbitMQ, and responds immediately without waiting for the message to be processed.

The following tasks were carried out:

- Exposing the `POST /orders` endpoint.
- Publishing the event to the `orders_exchange` exchange with the `order.created` routing key.
- Configuring persistent messages (`delivery_mode=2`) so orders are not lost if the broker restarts.
- Handling connection errors, returning `503 Service Unavailable` if the broker is unavailable at the time of publishing.

## Main files of the first component

- `order-service/main.py`
- `order-service/requirements.txt`
- `order-service/.env.example`

## Usage example for the first component

**macOS / Linux**

```bash
cd order-service
cp .env.example .env   # then edit .env with your real CloudAMQP URL
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Windows (PowerShell)**

```powershell
cd order-service
Copy-Item .env.example .env   # then edit .env with your real CloudAMQP URL
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# Second component: notification-service (consumer)

In this component the consumer service was implemented, an independent worker that listens to the RabbitMQ queue and simulates sending a notification (for example, an email) for every order it receives.

The following tasks were carried out:

- Consuming messages from `orders_queue`, with `prefetch_count=1` to distribute the load evenly if more instances are added.
- Idempotency validation by `order_id`, avoiding duplicate notifications on redelivery.
- Handling malformed messages: if the JSON is invalid, the message is sent to the dead-letter queue instead of stopping the worker.
- Structured logging with timestamps for every notification processed.

## Main files of the second component

- `notification-service/consumer.py`
- `notification-service/requirements.txt`
- `notification-service/.env.example`

## Usage example for the second component

**macOS / Linux**

```bash
cd notification-service
cp .env.example .env   # then edit .env with your real CloudAMQP URL
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python consumer.py
```

**Windows (PowerShell)**

```powershell
cd notification-service
Copy-Item .env.example .env   # then edit .env with your real CloudAMQP URL
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python consumer.py
```

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# Third component: message broker (RabbitMQ / CloudAMQP)

In the third component, the broker that connects the two services without them talking to each other directly was configured. The demo uses a RabbitMQ instance hosted on CloudAMQP, which both services connect to over AMQPS (TLS).

```
Client --HTTP POST /orders--> [order-service] --publishes--> [orders_exchange]
                                                                    |
                                                       routing key: order.created
                                                                    v
                                                            [orders_queue] --> [notification-service]
                                                                    |
                                                        (on failure) v
                                                            [orders_dlx] --> [orders_queue_dlq]
```

The following tasks were carried out:

- Creation of the `orders_exchange` exchange (type `direct`), durable.
- Creation of the `orders_queue` queue, durable, bound with the `order.created` routing key.
- Dead-letter configuration: any rejected message (`nack`, `requeue=False`) is routed through the `orders_dlx` fanout exchange into the `orders_queue_dlq` queue, instead of being lost or retried indefinitely.

## Environment variables

All configuration is injected through environment variables, nothing is hardcoded in the source code, and no real credential is ever committed.

| Variable | Used by | Required | Purpose |
|---|---|---|---|
| `RABBITMQ_URL` | both services | Yes, no default value | Full AMQPS URI from the CloudAMQP dashboard (`amqps://user:password@host/vhost`) |
| `EXCHANGE_NAME` | both services | No (`orders_exchange`) | Exchange name |
| `ROUTING_KEY` | both services | No (`order.created`) | Routing key / binding key |

Each service loads these variables from a local `.env` file (via `python-dotenv`) if one exists, or from variables already exported in the shell. **If `RABBITMQ_URL` is not set, the service raises an error immediately instead of starting**, so a missing credential is never silently ignored.

**macOS / Linux**

```bash
cd order-service
cp .env.example .env
# now open .env and paste the real CloudAMQP connection string
```

**Windows (PowerShell)**

```powershell
cd order-service
Copy-Item .env.example .env
# now open .env and paste the real CloudAMQP connection string
```

Repeat the same inside `notification-service/`. `.env` is listed in `.gitignore`, so `git status` should never show it as a new file.

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# How to run the whole project

Python 3.11+ and a CloudAMQP instance are required. The broker is hosted on CloudAMQP, so **no local RabbitMQ installation is needed**.

Pick the block that matches your OS. Both do exactly the same three things, in three separate terminals: start the consumer, start the API, then send a test order.

### macOS / Linux

```bash
# Terminal 1 - notification-service (consumer)
cd notification-service
cp .env.example .env   # then edit .env with your real CloudAMQP URL
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python consumer.py
```

```bash
# Terminal 2 - order-service (producer/API)
cd order-service
cp .env.example .env   # then edit .env with your real CloudAMQP URL
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

```bash
# Terminal 3 - send a test order
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_name": "Mariana Es", "items": ["Wireless Mouse", "USB-C Cable"], "total": 49.98}'
```

### Windows (PowerShell)

PowerShell is the default terminal on Windows 10/11 (Start → "Terminal"). If activating the virtual environment fails with a message about running scripts being disabled, run this once per terminal session first: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`. If `python` isn't recognized, try `py -3` instead (the Python Launcher for Windows).

```powershell
# Terminal 1 - notification-service (consumer)
cd notification-service
Copy-Item .env.example .env   # then edit .env with your real CloudAMQP URL
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python consumer.py
```

```powershell
# Terminal 2 - order-service (producer/API)
cd order-service
Copy-Item .env.example .env   # then edit .env with your real CloudAMQP URL
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

```powershell
# Terminal 3 - send a test order
curl.exe -X POST "http://localhost:8000/orders" -H "Content-Type: application/json" --data-binary "@order.json"
```
> Use `curl.exe`, not plain `curl` — in PowerShell, `curl` is an alias for `Invoke-WebRequest`, which doesn't accept the same flags and will error out on `-X`/`-d`.

Using **Command Prompt (cmd.exe)** instead? Activate with `.venv\Scripts\activate.bat` and use `copy` instead of `Copy-Item` — everything else above is identical.

**Expected input** (`POST /orders` body):

```json
{
  "customer_name": "Maria Gomez",
  "items": ["Wireless Mouse", "USB-C Cable"],
  "total": 49.98
}
```

**Expected output** (HTTP response, returned immediately):

```json
{ "order_id": "b3f1...", "status": "queued" }
```

**Expected side effect** (in the `notification-service` logs, a moment later):

```
[notification-service] Notification sent to Maria Gomez: your order b3f1... ($49.98) was received.
```

You can also open your instance's RabbitMQ management UI from the CloudAMQP dashboard (`https://customer.cloudamqp.com` → your instance) to see the exchange, the queue, and the message rates in real time.

To stop the services, press `CTRL+C` in each terminal. The queues and messages remain in CloudAMQP.

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# Error handling

| Error | Cause | How it's handled |
|---|---|---|
| `RABBITMQ_URL is not set` on startup | `.env` wasn't created, or the variable wasn't exported | The service refuses to start and prints exactly what to do, instead of failing later with a confusing connection error |
| `Connection refused` / timeout | The broker takes a moment to respond over the internet | `pika.URLParameters` plus a retry loop with backoff in both services' code |
| Duplicate notification for the same order | A message is redelivered (e.g. the consumer crashed before acking) | Idempotency check using `order_id` before sending the notification |
| Malformed message body | A producer bug sends invalid JSON | The consumer catches the parsing error and routes the message to the dead-letter queue instead of crashing |
| Broker unreachable when publishing | The CloudAMQP instance is down or the network fails | `order-service` returns `503 Service Unavailable` instead of silently losing the order |
| `python -m venv .venv` hangs and ends in `KeyboardInterrupt` on Windows | A known issue with `ensurepip` when creating the virtual environment on certain Python versions (for example Python 3.14) on Windows; the subprocess that installs `pip` stops responding | Delete the `.venv` folder and recreate the environment: `Remove-Item -Recurse -Force .venv` and then `python -m venv .venv` again |

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# Technical decisions

- **`direct` exchange with an explicit routing key** instead of publishing straight to a queue — this keeps the producer decoupled from queue names and makes it possible to add more consumers/queues later without changing `order-service`.
- **Durable exchange, durable queue, persistent messages** (`delivery_mode=2`) so orders are not lost if the broker restarts.
- **Dead-letter exchange/queue** so failed messages are inspectable instead of silently dropped or retried forever.
- **`prefetch_count=1`** on the consumer so messages are distributed fairly if more consumer instances are added later (horizontal scaling).
- **No hardcoded credentials, ever** — `RABBITMQ_URL` has no default value in code; it is only ever read from `.env` (local, gitignored) or the environment.

# Best practices applied

- Idempotent message processing.
- Explicit error handling and dead-lettering instead of silent failures.
- Configuration via environment variables, loaded from a gitignored `.env` file — never hardcoded, never committed.
- Each service has its own `requirements.txt` and can be deployed independently (independent deployability, a core microservices principle).
- Structured logging with timestamps on both services.

# Known limitations

- The idempotency check is stored in memory, so it resets if the notification service restarts; a production system would persist processed IDs in Redis or a database.
- Notifications are simulated with a log line, not a real email/SMS provider integration.
- There is a single consumer instance; no load test was performed to measure throughput under heavy traffic.

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# Technologies used

- Python
- FastAPI
- Uvicorn
- RabbitMQ
- CloudAMQP

# Notes

- The repository includes the development corresponding to both services and the broker configuration.
- The real `.env` file is never committed; only `.env.example` is included for each service.
- Screenshots and execution evidence (terminal output, `curl`, consumer logs, and the RabbitMQ management UI) should be added before submission.
- To run the project correctly, an active CloudAMQP instance is required, with its connection string configured in `.env`.

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>
