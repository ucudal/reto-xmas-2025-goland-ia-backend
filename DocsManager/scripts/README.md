# Scripts de Configuración

## Orden de Ejecución

**IMPORTANTE:** Los scripts deben ejecutarse en este orden:

1. **setup_rabbitmq.sh** - Configura RabbitMQ (exchange, queue y binding)
2. **setup_minio_events.sh** - Configura MinIO para enviar eventos a RabbitMQ

## setup_rabbitmq.sh

Script para configurar RabbitMQ con el exchange, queue y binding necesarios para recibir eventos de MinIO.

### Requisitos Previos

1. **rabbitmqadmin instalado** (el script intentará descargarlo automáticamente si no está disponible)
2. **RabbitMQ corriendo** con el plugin de management habilitado

### Uso

```bash
cd DocsManager/scripts
./setup_rabbitmq.sh
```

### Qué hace el script

1. Verifica/descarga `rabbitmqadmin` si no está instalado
2. Crea el exchange `minio-events` (tipo: direct, durable)
3. Crea la queue `document.process` (durable)
4. Crea el binding entre el exchange y la queue
5. Muestra la configuración resultante

## setup_minio_events.sh

Script para configurar eventos de MinIO hacia RabbitMQ. Cuando se crea un archivo en el bucket `goland-bucket` dentro de la carpeta especificada en `MINIO_FOLDER` (por defecto `rag-docs/`), MinIO publicará automáticamente un mensaje en la cola de RabbitMQ.

### Requisitos Previos

1. **MinIO Client (mc) instalado:**
   ```bash
   # macOS
   brew install minio/stable/mc
   
   # Linux
   wget https://dl.min.io/client/mc/release/linux-amd64/mc
   chmod +x mc
   sudo mv mc /usr/local/bin/
   ```

2. **MinIO corriendo** y accesible
3. **RabbitMQ corriendo** y accesible
4. **RabbitMQ ya configurado** (ejecutar `setup_rabbitmq.sh` primero)

### Uso

#### Opción 1: Usando variables de entorno del archivo .env

El script automáticamente carga las variables del archivo `.env` en el directorio raíz de DocsManager:

```bash
cd DocsManager
./scripts/setup_minio_events.sh
```

#### Opción 2: Usando variables de entorno directamente

```bash
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin
export MINIO_BUCKET=goland-bucket
export MINIO_FOLDER=rag-docs
export RABBITMQ_HOST=rabbitmq
export RABBITMQ_USER=guest
export RABBITMQ_PASSWORD=guest
export QUEUE_NAME=document.process

./scripts/setup_minio_events.sh
```

### Variables de Entorno

El script utiliza las siguientes variables (con valores por defecto):

| Variable | Descripción | Valor por Defecto |
|----------|-------------|-------------------|
| `MINIO_ENDPOINT` | Endpoint de MinIO (host:puerto) | `localhost:9000` |
| `MINIO_ACCESS_KEY` | Clave de acceso de MinIO | `minioadmin` |
| `MINIO_SECRET_KEY` | Clave secreta de MinIO | `minioadmin` |
| `MINIO_BUCKET` | Nombre del bucket | `goland-bucket` |
| `MINIO_FOLDER` | Carpeta dentro del bucket donde se monitorean los eventos | `rag-docs` |
| `MINIO_USE_SSL` | Usar SSL para MinIO | `false` |
| `RABBITMQ_HOST` | Host de RabbitMQ | `rabbitmq` |
| `RABBITMQ_PORT` | Puerto de RabbitMQ | `5672` |
| `RABBITMQ_USER` | Usuario de RabbitMQ | `guest` |
| `RABBITMQ_PASSWORD` | Contraseña de RabbitMQ | `guest` |
| `QUEUE_NAME` | Nombre de la cola | `document.process` |

### Qué hace el script

1. Verifica que `mc` esté instalado
2. Carga variables de entorno desde `.env` (si existe)
3. Configura un alias de MinIO
4. Verifica la conexión a MinIO
5. Crea el bucket si no existe
6. Configura la notificación AMQP hacia RabbitMQ
7. Reinicia MinIO para aplicar cambios
8. Configura eventos para archivos en la carpeta especificada en `MINIO_FOLDER` dentro del bucket
9. Muestra un resumen de la configuración

### Formato del Mensaje

Cuando MinIO detecta un nuevo archivo en la carpeta especificada en `MINIO_FOLDER` (por defecto `rag-docs/`), publica un mensaje JSON en RabbitMQ con el siguiente formato:

```json
{
  "EventName": "s3:ObjectCreated:Put",
  "Key": "rag-docs/uuid.pdf",
  "Records": [
    {
      "eventVersion": "2.0",
      "eventSource": "minio:s3",
      "awsRegion": "",
      "eventTime": "2025-01-XX...",
      "eventName": "s3:ObjectCreated:Put",
      "s3": {
        "bucket": {
          "name": "goland-bucket"
        },
        "object": {
          "key": "rag-docs/uuid.pdf",
          "size": 12345
        }
      }
    }
  ]
}
```

### Verificar la Configuración

Para verificar que los eventos están configurados:

```bash
mc event list myminio/goland-bucket
```

### Solución de Problemas

1. **Error: "mc: command not found"**
   - Instala MinIO Client siguiendo las instrucciones en "Requisitos Previos"

2. **Error: "No se pudo conectar a MinIO"**
   - Verifica que MinIO esté corriendo
   - Verifica que el endpoint y las credenciales sean correctas
   - Si MinIO está en Docker, usa `localhost` o el nombre del servicio

3. **Error: "RabbitMQ connection failed"**
   - Verifica que RabbitMQ esté corriendo
   - Verifica que el host y puerto sean correctos
   - Si RabbitMQ está en Docker, usa el nombre del servicio (`rabbitmq`) en lugar de `localhost`

4. **Los eventos no se disparan**
   - Verifica que los archivos se suban a la ruta especificada en `MINIO_FOLDER` dentro del bucket
   - Verifica que la cola `document.process` exista en RabbitMQ
   - Revisa los logs de MinIO para ver si hay errores

### Notas

- El script reinicia MinIO, lo que puede causar una breve interrupción del servicio
- Los eventos solo se disparan para archivos nuevos (PUT), no para actualizaciones
- El prefijo especificado en `MINIO_FOLDER` es obligatorio - los archivos fuera de esta carpeta no generarán eventos
- Por defecto, `MINIO_FOLDER` está configurado como `rag-docs`, pero puedes cambiarlo usando la variable de entorno

