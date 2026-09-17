# Ejercicio-1---Semana-1

Tarjeta de presentación personal.

Sitio estático de presentación personal.

## Pruebas locales

Requiere Python 3:

```powershell
python -m unittest discover -s tests -p "validate_site.py" -v
```

## CI/CD

Cada pull request y cada push a `main` ejecutan las pruebas. Un push exitoso a `main` publica automáticamente el contenido en GitHub Pages mediante GitHub Actions.

En el repositorio de GitHub, configura **Settings > Pages > Source** como **GitHub Actions** la primera vez.
