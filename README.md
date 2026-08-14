<p align='center'> 
  <img src="https://capsule-render.vercel.app/api?type=waving&height=200&color=FF6600&text=RabbitMQ%20Async%20Demo&fontColor=FFFFFF&desc=Comunicacion%20Asincrona%20entre%20Microservicios&fontAlignY=30&descAlignY=54"/> 
</p>

<p align="center">
  <a href="https://youtu.be/UeRYxGLPWK0" target="_blank" rel="noopener noreferrer">
    <img
      src="https://64.media.tumblr.com/e29ae5ec2a39de294d8722ecf312b5d3/7b273f38c55d349b-43/s2048x3072/89ad0a543624dcd3dec51c74ab221c6a7d1ec435.pnj"
      alt="Anime image - Ver video de la presentacion"
      height="350"
    />
  </a>
</p>

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# Comunicacion Asincrona entre Microservicios con RabbitMQ

Ejemplo minimo y ejecutable de **comunicacion asincrona basada en eventos** entre dos microservicios independientes, desarrollado como material para una presentacion universitaria sobre RabbitMQ.

> **Nota de seguridad:** este proyecto se conecta a un broker RabbitMQ alojado en la nube (CloudAMQP). La cadena de conexion es un secreto y se carga desde un archivo `.env` local que **nunca se versiona** (ver la seccion de [Variables de entorno](#variables-de-entorno)). Si una version anterior de este repositorio llego a tener una cadena de conexion real escrita directamente en el codigo, esa credencial debe rotarse desde el panel de CloudAMQP antes de hacer publico el repositorio.

Este repositorio contiene:

- Un servicio productor (`order-service`) construido con FastAPI que expone `POST /orders` y publica eventos de ordenes creadas.
- Un servicio consumidor (`notification-service`), un worker independiente en Python que escucha esos eventos y simula el envio de notificaciones.
- La configuracion de un broker RabbitMQ alojado en CloudAMQP, con exchange, cola principal y una cola de mensajes fallidos (dead-letter).

## Estructura general del repositorio

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

# Primer componente: order-service (productor)

En este componente se implemento el servicio productor, una API construida con FastAPI que recibe ordenes de un cliente, publica un evento `order.created` en RabbitMQ y responde de inmediato sin esperar a que el mensaje sea procesado.

Se realizaron las siguientes tareas:

- Exposicion del endpoint `POST /orders`.
- Publicacion del evento en el exchange `orders_exchange` con la routing key `order.created`.
- Configuracion de mensajes persistentes (`delivery_mode=2`) para no perder ordenes ante un reinicio del broker.
- Manejo de errores de conexion, retornando `503 Service Unavailable` si el broker no esta disponible al momento de publicar.

## Archivos principales del primer componente

- `order-service/main.py`
- `order-service/requirements.txt`
- `order-service/.env.example`

## Ejemplo de uso del primer componente

**macOS / Linux**

```bash
cd order-service
cp .env.example .env   # luego editar .env con la URL real de CloudAMQP
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Windows (PowerShell)**

```powershell
cd order-service
Copy-Item .env.example .env   # luego editar .env con la URL real de CloudAMQP
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# Segundo componente: notification-service (consumidor)

En este componente se implemento el servicio consumidor, un worker independiente que escucha la cola de RabbitMQ y simula el envio de una notificacion (por ejemplo, un correo) por cada orden recibida.

Se realizaron las siguientes tareas:

- Consumo de mensajes desde `orders_queue`, con `prefetch_count=1` para distribuir la carga de forma equitativa si se agregan mas instancias.
- Validacion de idempotencia por `order_id`, evitando notificaciones duplicadas ante una redelivery.
- Manejo de mensajes malformados: si el JSON no es valido, el mensaje se envia a la cola de dead-letter en lugar de detener el worker.
- Registro de logs estructurados con marca de tiempo para cada notificacion procesada.

## Archivos principales del segundo componente

- `notification-service/consumer.py`
- `notification-service/requirements.txt`
- `notification-service/.env.example`

## Ejemplo de uso del segundo componente

**macOS / Linux**

```bash
cd notification-service
cp .env.example .env   # luego editar .env con la URL real de CloudAMQP
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python consumer.py
```

**Windows (PowerShell)**

```powershell
cd notification-service
Copy-Item .env.example .env   # luego editar .env con la URL real de CloudAMQP
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python consumer.py
```

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# Tercer componente: broker de mensajeria (RabbitMQ / CloudAMQP)

En el tercer componente se configuro el broker que conecta a los dos servicios sin que estos se comuniquen directamente entre si. La demo usa una instancia de RabbitMQ alojada en CloudAMQP, a la que ambos servicios se conectan por AMQPS (TLS).

```
Cliente --HTTP POST /orders--> [order-service] --publica--> [orders_exchange]
                                                                    |
                                                       routing key: order.created
                                                                    v
                                                            [orders_queue] --> [notification-service]
                                                                    |
                                                       (ante fallo) v
                                                            [orders_dlx] --> [orders_queue_dlq]
```

Se realizaron las siguientes tareas:

- Creacion del exchange `orders_exchange` (tipo `direct`), durable.
- Creacion de la cola `orders_queue`, durable, enlazada con la routing key `order.created`.
- Configuracion de dead-lettering: todo mensaje rechazado (`nack`, `requeue=False`) se enruta a traves del exchange fanout `orders_dlx` hacia la cola `orders_queue_dlq`, en vez de perderse o reintentarse indefinidamente.

## Variables de entorno

Toda la configuracion se inyecta por variables de entorno, nada esta escrito directamente en el codigo, y ninguna credencial real se versiona.

| Variable | Usada por | Obligatoria | Proposito |
|---|---|---|---|
| `RABBITMQ_URL` | ambos servicios | Si, sin valor por defecto | URI AMQPS completa del panel de CloudAMQP (`amqps://usuario:clave@host/vhost`) |
| `EXCHANGE_NAME` | ambos servicios | No (`orders_exchange`) | Nombre del exchange |
| `ROUTING_KEY` | ambos servicios | No (`order.created`) | Routing key / binding key |

Cada servicio carga estas variables desde un archivo `.env` local (via `python-dotenv`) si existe, o desde variables ya exportadas en la shell. **Si `RABBITMQ_URL` no esta definida, el servicio lanza un error de inmediato en lugar de arrancar**, para que una credencial faltante nunca pase desapercibida.

**macOS / Linux**

```bash
cd order-service
cp .env.example .env
# ahora abrir .env y pegar la cadena de conexion real de CloudAMQP
```

**Windows (PowerShell)**

```powershell
cd order-service
Copy-Item .env.example .env
# ahora abrir .env y pegar la cadena de conexion real de CloudAMQP
```

Repetir lo mismo dentro de `notification-service/`. `.env` esta listado en `.gitignore`, por lo que `git status` nunca deberia mostrarlo como archivo nuevo.

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# Como ejecutar el proyecto completo

Se necesitan Python 3.11+ y una instancia de CloudAMQP. El broker esta alojado en CloudAMQP, por lo que **no se requiere una instalacion local de RabbitMQ**.

Elegir el bloque segun el sistema operativo. Ambos hacen exactamente lo mismo en tres terminales separadas: iniciar el consumidor, iniciar la API, y luego enviar una orden de prueba.

### macOS / Linux

```bash
# Terminal 1 - notification-service (consumidor)
cd notification-service
cp .env.example .env   # luego editar .env con la URL real de CloudAMQP
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python consumer.py
```

```bash
# Terminal 2 - order-service (productor/API)
cd order-service
cp .env.example .env   # luego editar .env con la URL real de CloudAMQP
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

```bash
# Terminal 3 - orden de prueba
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_name": "Maria Gomez", "items": ["Wireless Mouse", "USB-C Cable"], "total": 49.98}'
```

### Windows (PowerShell)

PowerShell es la terminal por defecto en Windows 10/11 (Inicio → "Terminal"). Si al activar el entorno virtual aparece un error sobre la ejecucion de scripts deshabilitada, ejecutar una vez por sesion de terminal: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`. Si `python` no es reconocido, probar con `py -3` (el Python Launcher para Windows).

```powershell
# Terminal 1 - notification-service (consumidor)
cd notification-service
Copy-Item .env.example .env   # luego editar .env con la URL real de CloudAMQP
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python consumer.py
```

```powershell
# Terminal 2 - order-service (productor/API)
cd order-service
Copy-Item .env.example .env   # luego editar .env con la URL real de CloudAMQP
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

```powershell
# Terminal 3 - orden de prueba
curl.exe -X POST "http://localhost:8000/orders" -H "Content-Type: application/json" --data-binary "@order.json"
```
> Usar `curl.exe`, no `curl` a secas — en PowerShell, `curl` es un alias de `Invoke-WebRequest`, que no acepta los mismos flags y falla con `-X`/`-d`.

Usando **Command Prompt (cmd.exe)** en lugar de PowerShell? Activar el entorno con `.venv\Scripts\activate.bat` y usar `copy` en vez de `Copy-Item` — el resto es identico a lo anterior.

**Entrada esperada** (`POST /orders`):

```json
{
  "customer_name": "Maria Gomez",
  "items": ["Wireless Mouse", "USB-C Cable"],
  "total": 49.98
}
```

**Salida esperada** (respuesta HTTP inmediata):

```json
{ "order_id": "b3f1...", "status": "queued" }
```

**Efecto secundario esperado** (logs de `notification-service` momentos despues):

```
[notification-service] Notification sent to Maria Gomez: your order b3f1... ($49.98) was received.
```

Tambien se puede abrir la UI de administracion de RabbitMQ de la instancia desde el panel de CloudAMQP (`https://customer.cloudamqp.com` → tu instancia) para ver el exchange, la cola y las tasas de mensajes en tiempo real.

Para detener los servicios, presionar `CTRL+C` en cada terminal. Las colas y los mensajes permanecen en CloudAMQP.

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# Manejo de errores

| Error | Causa | Como se maneja |
|---|---|---|
| `RABBITMQ_URL is not set` al iniciar | No se creo el `.env`, o la variable no fue exportada | El servicio se niega a iniciar e imprime que hacer, en lugar de fallar despues con un error de conexion confuso |
| `Connection refused` / timeout | El broker tarda un momento en responder por internet | `pika.URLParameters` mas un bucle de reintento con backoff en el codigo de ambos servicios |
| Notificacion duplicada para la misma orden | Un mensaje es redelivered (por ejemplo, el consumidor se cayo antes de hacer ack) | Verificacion de idempotencia usando `order_id` antes de enviar la notificacion |
| Cuerpo de mensaje malformado | Un bug del productor envia un JSON invalido | El consumidor captura el error de parseo y enruta el mensaje a la cola de dead-letter en vez de fallar |
| Broker inalcanzable al publicar | La instancia de CloudAMQP esta caida o falla la red | `order-service` retorna `503 Service Unavailable` en lugar de perder la orden silenciosamente |
| `python -m venv .venv` se queda colgado y termina en `KeyboardInterrupt` en Windows | Problema conocido de `ensurepip` al crear el entorno virtual sobre ciertas versiones de Python (por ejemplo Python 3.14) en Windows; el subproceso que instala `pip` no responde | Borrar la carpeta `.venv` y volver a crear el entorno: `Remove-Item -Recurse -Force .venv` y luego `python -m venv .venv` de nuevo |

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# Decisiones tecnicas

- Exchange `direct` con routing key explicita en lugar de publicar directamente a una cola, lo que desacopla al productor de los nombres de cola y permite agregar mas consumidores/colas despues sin tocar `order-service`.
- Exchange durable, cola durable y mensajes persistentes (`delivery_mode=2`) para no perder ordenes ante un reinicio del broker.
- Exchange y cola de dead-letter para que los mensajes fallidos sean inspeccionables en vez de perderse o reintentarse indefinidamente.
- `prefetch_count=1` en el consumidor para distribuir la carga de forma equitativa si se agregan mas instancias (escalado horizontal).
- Sin credenciales hardcodeadas, nunca: `RABBITMQ_URL` no tiene valor por defecto en el codigo, solo se lee desde `.env` (local, gitignored) o desde el entorno.

# Buenas practicas aplicadas

- Procesamiento de mensajes idempotente.
- Manejo explicito de errores y dead-lettering en lugar de fallos silenciosos.
- Configuracion por variables de entorno, cargadas desde un `.env` gitignored, nunca hardcodeada ni commiteada.
- Cada servicio tiene su propio `requirements.txt` y puede desplegarse de forma independiente (despliegue independiente, principio central de microservicios).
- Logging estructurado con marca de tiempo en ambos servicios.

# Limitaciones conocidas

- La verificacion de idempotencia se guarda en memoria, por lo que se reinicia si el servicio de notificaciones se reinicia; un sistema en produccion persistiria los IDs procesados en Redis o una base de datos.
- Las notificaciones se simulan con una linea de log, sin integracion real con un proveedor de correo/SMS.
- Hay una unica instancia de consumidor; no se realizo prueba de carga para medir el throughput bajo trafico alto.

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>

# Tecnologias utilizadas

- Python
- FastAPI
- Uvicorn
- RabbitMQ
- CloudAMQP

# Notas

- El repositorio incluye el desarrollo correspondiente a los dos servicios y a la configuracion del broker.
- El archivo `.env` real no se versiona; solo se incluye `.env.example` en cada servicio.
- Las capturas de pantalla y evidencia de ejecucion (terminales, `curl`, logs del consumidor y la UI de administracion de RabbitMQ) deben agregarse antes de la entrega.
- Para ejecutar correctamente el proyecto es necesario contar con una instancia de CloudAMQP activa y su cadena de conexion configurada en `.env`.

<p align='center'>
  <img src="https://capsule-render.vercel.app/api?type=rect&height=5&color=FF6600&reversal=false&fontAlignY=40&fontColor=FFFFFF&fontSize=60"/>
</p>
