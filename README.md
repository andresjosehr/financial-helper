# Financial Helper

Proyecto Django con MySQL y Docker

## Requisitos

- Docker
- Docker Compose

## Configuración

1. Copiar el archivo de variables de entorno:
```bash
cp .env.example .env
```

2. Editar `.env` con tus configuraciones (opcional, los valores por defecto funcionan para desarrollo)

## Uso

### Iniciar los servicios

```bash
docker-compose up -d
```

### Ejecutar migraciones

```bash
docker-compose exec web python manage.py migrate
```

### Crear superusuario

```bash
docker-compose exec web python manage.py createsuperuser
```

### Ver logs

```bash
docker-compose logs -f web
```

### Detener los servicios

```bash
docker-compose down
```

### Detener y eliminar volúmenes (base de datos)

```bash
docker-compose down -v
```

## Acceso

- Aplicación web: http://localhost:8000
- Admin de Django: http://localhost:8000/admin
- Base de datos MySQL: localhost:3306

## Estructura del proyecto

```
.
├── config/              # Configuración del proyecto Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── Dockerfile          # Imagen Docker para Django
├── docker-compose.yml  # Orquestación de contenedores
├── requirements.txt    # Dependencias Python
├── manage.py          # CLI de Django
└── .env.example       # Plantilla de variables de entorno
```
