# GOLAND BACKEND - RETO DICIEMBRE 2025

## 🥅 Objetivo
> _Proporcionar un asistente conversacional que responda consultas nutricionales y
culinarias contextualizadas sobre el producto_  


---

## 🌿 Nomenclatura de Ramas

Para mantener un flujo de trabajo organizado y fácil de entender, el proyecto utiliza una convención clara para nombrar las ramas del repositorio. Dicha convención es la siguiente: feature/taskName

**feature/taskName**

## 🔧 Ramas de nuevas funcionalidades

Para las ramas de endpoints específicamente se usara la siguiente convención:

**CRUD_METHOD/funcionalidad**


## 🐛 Ramas de Bugs

Para las ramas de endpoints específicamente se usara la siguiente convención:

**bug/taskName**

---

## 🧹 Code Quality - Ruff

Este proyecto utiliza [Ruff](https://github.com/astral-sh/ruff) como linter y formateador de código Python. Ruff es extremadamente rápido (escrito en Rust) y reemplaza herramientas como Flake8, Black, isort, y muchas otras.

### Instalación

Ruff ya está configurado en el proyecto. Si necesitas instalarlo manualmente:

```bash
pip install ruff
```

O si usas las dependencias de desarrollo del proyecto:

```bash
pip install -e ".[dev]"
```

### Uso

**Linting (verificar código):**
```bash
python -m ruff check .
```

**Linting con auto-fix:**
```bash
python -m ruff check . --fix
```

**Formatear código:**
```bash
python -m ruff format .
```

**Verificar un archivo específico:**
```bash
python -m ruff check app/main.py
python -m ruff format app/main.py
```

### Configuración

La configuración de Ruff está en `pyproject.toml` bajo la sección `[tool.ruff]`. Las reglas habilitadas incluyen:

- **E, W**: Errores y advertencias de pycodestyle
- **F**: Pyflakes (detectar errores de importación y variables no utilizadas)
- **I**: isort (ordenar imports)
- **N**: pep8-naming (convenciones de nombres)
- **UP**: pyupgrade (actualizar sintaxis a versiones modernas de Python)
- **B**: flake8-bugbear (detectar errores comunes)
- **C4**: flake8-comprehensions (mejorar comprehensions)
- **SIM**: flake8-simplify (simplificar código)

### Integración con IDEs

**VS Code:**
Instala la extensión oficial "Ruff" desde el marketplace de VS Code para tener linting y formateo automático.

**Pre-commit hooks (opcional):**
Si quieres ejecutar Ruff antes de cada commit, puedes configurarlo como un pre-commit hook.

### Más información

- [Documentación oficial de Ruff](https://docs.astral.sh/ruff/)
- [Repositorio en GitHub](https://github.com/astral-sh/ruff)