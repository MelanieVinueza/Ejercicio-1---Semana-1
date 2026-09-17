# Ejercicio-1---Semana-1

Tarjeta de presentación personal.

Sitio estático de presentación personal.

## Pruebas locales

### 1. Validación estática (HTML semántico, HTML5, ARIA, enlaces seguros)

Requiere Python 3:

```powershell
python -m unittest discover -s tests -p "validate_site.py" -v
```

Incluye:

- Estructura semántica: `header`, `nav`, `main`, `footer`, un único `<h1>`, encabezados sin niveles saltados.
- HTML5: `<!DOCTYPE html>` y `lang="es"` presentes.
- ARIA: nombres accesibles en botones/enlaces, `aria-controls`/`aria-labelledby`/`aria-describedby` apuntando a ids existentes, `aria-expanded` con valores booleanos.
- Enlaces seguros: todos los enlaces externos con `https://`, sin esquemas peligrosos (`javascript:`, `data:`, `vbscript:`), `target="_blank"` con `rel="noopener"`.
- Enlaces de YouTube: solo dominios permitidos (`youtube.com`, `youtu.be`, `youtube-nocookie.com`, etc.) y siempre por HTTPS.

### 2. Validación HTML5 con el validador W3C/Nu

```powershell
pip install -r requirements.txt
html5validator index.html
```

### 3. Accesibilidad WCAG 2.1 AA y responsive

Requiere Node.js 18+:

```powershell
npm install
node tests/check_a11y_responsive.js
```

El script levanta un servidor local y ejecuta axe-core (reglas WCAG 2.1 A/AA) en viewports de **móvil (375px), tablet (768px) y escritorio (1280px)**, además de comprobar que no haya desbordamiento horizontal y que la navegación esté visible.

## CI/CD

Cada pull request y cada push a `main` ejecutan, en GitHub Actions:

1. Validación HTML5 con el validador W3C/Nu.
2. Pruebas estáticas de Python (HTML semántico, ARIA, enlaces seguros).
3. Accesibilidad WCAG 2.1 AA y responsive con axe-core + Playwright.

Si todas las pruebas pasan, un push exitoso a `main` publica automáticamente el contenido en GitHub Pages mediante las acciones oficiales (`configure-pages`, `upload-pages-artifact`, `deploy-pages`).

En el repositorio de GitHub, configura **Settings > Pages > Source** como **GitHub Actions** la primera vez.