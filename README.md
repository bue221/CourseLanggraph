# Estudio de conceptos de langgraph

Este proyecto utiliza un ambiente virtual de Conda con dependencias instaladas a través de pip.

## Requisitos Previos

- Conda instalado en tu sistema
- Python 3.12 o superior

## Configuración del Ambiente

1. Crear el ambiente virtual con Conda:

```bash
conda create -n supervisor python=3.12
```

2. Activar el ambiente:

```bash
conda activate supervisor
```

3. Instalar las dependencias usando pip:

```bash
pip install -r requirements.txt
```

## Uso

Para ejecutar el proyecto:

```bash
python src/main.py
```

## Desactivar el Ambiente

Cuando hayas terminado, puedes desactivar el ambiente con:

```bash
conda deactivate
```

## Solución de Problemas

Si encuentras algún problema con las dependencias, puedes intentar:

1. Actualizar pip:

```bash
pip install --upgrade pip
```

2. Reinstalar las dependencias:

```bash
pip install -r requirements.txt --force-reinstall
```

## Contribución

1. Asegúrate de que el ambiente esté activado
2. Instala las dependencias de desarrollo:

```bash
pip install -r requirements-dev.txt
```

3. Ejecuta las pruebas:

```bash
pytest
```
