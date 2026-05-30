# Instrucciones para Crear el Ejecutable

Para convertir esta aplicación en un archivo ejecutable (.exe en Windows), se recomienda utilizar **PyInstaller**.

## Requisitos Previos

1. Tener Python instalado.
2. Instalar las dependencias del proyecto:
   ```bash
   pip install -r requirements.txt
   ```
3. Instalar PyInstaller:
   ```bash
   pip install pyinstaller
   ```

## Pasos para generar el ejecutable

Ejecuta el siguiente comando en la terminal desde la carpeta raíz del proyecto:

```bash
pyinstaller --noconsole --onefile --name "GestionApicola" app.py
```

### Explicación de los parámetros:
- `--noconsole`: Evita que se abra una ventana de comandos (terminal) al ejecutar la aplicación.
- `--onefile`: Empaqueta todo en un único archivo ejecutable.
- `--name "GestionApicola"`: Define el nombre del archivo final.

## Notas Importantes

1. **Archivos Externos**: El ejecutable buscará la base de datos (`gestion_apicola.db`) y cualquier imagen de logo en la misma carpeta donde se encuentre el archivo .exe. Asegúrate de que estos archivos estén presentes en la carpeta final de distribución.
2. **Carpetas de Documentos**: La aplicación creará automáticamente las carpetas `Pdf`, `Presupuestos` y `Deudores` la primera vez que se ejecute si no existen.
3. **Distribución**: Una vez finalizado el proceso, el ejecutable se encontrará dentro de la carpeta `dist/`. Solo necesitas distribuir el archivo que está dentro de esa carpeta junto con la base de datos y los logos si los tienes.
