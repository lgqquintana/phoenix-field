# Phoenix Field Agent

Agente de análisis de campo para Phoenix Global Resources — Vaca Muerta.

## Estructura

```
phoenix-field-agent/
├── index.html          ← La app web
├── update_data.py      ← Script para actualizar datos desde Whitson+
├── Datos_estaticos.xlsx ← (copiá tu archivo acá)
└── data/
    └── wells.json      ← Generado automáticamente por update_data.py
```

## Setup inicial (una sola vez)

### 1. Crear repositorio en GitHub

1. Andá a github.com → New repository
2. Nombre: `phoenix-field` (o el que quieras)
3. Visibility: **Private** (recomendado — los datos son sensibles)
4. Inicializalo con README

### 2. Subir estos archivos

Desde VS Code o la terminal:
```bash
git clone https://github.com/TU_USUARIO/phoenix-field.git
cd phoenix-field
# Copiá todos los archivos de esta carpeta acá
git add .
git commit -m "Initial setup"
git push
```

### 3. Configurar GitHub Pages

1. En tu repo → Settings → Pages
2. Source: Deploy from a branch
3. Branch: main / root
4. Save

Tu app va a estar en: `https://TU_USUARIO.github.io/phoenix-field/`

### 4. Crear GitHub Token

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token
3. Permisos: marcar `repo` (acceso completo)
4. Copiar el token

### 5. Configurar update_data.py

Abrí `update_data.py` y completá:
```python
GITHUB_TOKEN = "ghp_tu_token_acá"
GITHUB_REPO  = "tu_usuario/phoenix-field"
```

### 6. Copiar Datos_estaticos.xlsx

Copiá tu archivo Excel con datos estáticos en la carpeta raíz del proyecto.

---

## Uso diario

Para actualizar los datos del campo:

```bash
cd phoenix-field
python update_data.py
```

El script:
1. Se autentica con Whitson+
2. Trae todos los pozos del proyecto Main
3. Descarga producción de cada pozo
4. Cruza con el Excel de datos estáticos
5. Sube el JSON a GitHub automáticamente
6. La app se actualiza en ~2 minutos

---

## Uso de la app

1. Abrí la URL de GitHub Pages en el browser
2. La primera vez te pide tu **API key de Anthropic** (conseguila en console.anthropic.com)
3. La key se guarda en tu browser, no en ningún servidor
4. Hacé click en "Actualizar datos" para cargar los últimos datos

### Pestañas

- **Overview** — Producción total por área, GOR del campo, comparación por nivel
- **Declinación** — Curvas de todos los pozos, filtrable por área y nivel
- **Niveles** — Comparación C-2 / C-3 / C-3.5 / C-4
- **Pozo** — Detalle individual: producción, GOR, WOR en el tiempo

### Chat con el agente

El agente tiene contexto completo del campo. Podés preguntarle:
- "¿Cómo está el campo hoy?"
- "¿Qué pozos tienen WOR anómalo?"
- "Comparame el PAD-9 vs PAD-12"
- "Haceme un reporte ejecutivo mensual"
- "¿Qué está pasando con el 2043?"
- "¿Vale la pena continuar perforando en C-4?"

---

## Actualización de datos estáticos

Si agregás nuevos pozos al Excel, reemplazá `Datos_estaticos.xlsx` y volvé a correr `update_data.py`.

---

## Seguridad

- El repositorio debería ser **privado**
- La API key de Claude se guarda en el **localStorage de tu browser** únicamente
- Las credenciales de Whitson están en el script Python (no en la app web)
- Nunca subas el GitHub Token al repositorio

---

## Soporte

Problemas comunes:

**"Sin datos" en la app**
→ Corriste `update_data.py`? Esperaste 2 minutos para que GitHub Pages se actualice?

**Error de API key**
→ Hacé click en "API Key" en la app y verificá que empiece con `sk-ant-`

**Error en update_data.py**
→ Verificá que `GITHUB_TOKEN` y `GITHUB_REPO` estén correctamente configurados
