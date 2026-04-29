"""
update_data.py — Phoenix Field Agent
Trae datos de Whitson+ y actualiza el archivo data/wells.json en GitHub.
Ejecutá este script para actualizar los datos de la app.
"""

import requests
import json
import time
import base64
import os
from datetime import datetime

# ============================================================
# CONFIGURACIÓN — editá estas variables
# ============================================================
CLIENT_NAME   = "phoenix"
CLIENT_ID     = "XEFyXC8ZxyTmoZnbDzBBKNhLRvYxvsEe"
CLIENT_SECRET = "HCtMdS_iv2mhXjEnptTgNC1MvuP2N_wQT6-Z9frpMR9Un1LEJ2WsDsYhxoStYj7s"

# GitHub — completá con tus datos
GITHUB_TOKEN  = ""          # Token de GitHub con permisos de repo (Settings > Developer settings > Personal access tokens)
GITHUB_REPO   = ""          # Ej: "leandro-quintana/phoenix-field"
GITHUB_BRANCH = "main"

# Proyecto de Whitson a usar (nombre exacto)
PROJECT_NAME  = "Main"

# Pozos a excluir (duplicados, sintéticos, etc.)
EXCLUDE_PATTERNS = ['PT_', 'DD_', '_copy', '_simul', '_mes', 'SHE.']

# Correcciones de Landing Zone
LZ_CORRECTIONS = {
    'PET.Nq.MMo-2221(h)': 'C-4.0',
}
# ============================================================


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def get_token():
    log("Autenticando con Whitson...")
    r = requests.post(
        "https://whitson.eu.auth0.com/oauth/token",
        json={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "audience": f"https://{CLIENT_NAME}.whitson.com/",
            "grant_type": "client_credentials"
        }
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    log("Token OK")
    return token


def api_get(token, path, params=None):
    base = f"https://{CLIENT_NAME}.whitson.com/api-external/v1"
    r = requests.get(
        f"{base}{path}",
        headers={"Authorization": f"Bearer {token}", "content-type": "application/json"},
        params=params
    )
    r.raise_for_status()
    return r.json()


def load_static_data():
    """Carga datos estáticos del Excel si existe."""
    static = {}
    try:
        import pandas as pd
        if os.path.exists("Datos_estaticos.xlsx"):
            df = pd.read_excel("Datos_estaticos.xlsx")
            for _, row in df.iterrows():
                name = row.get('NAME', '')
                if name:
                    static[name] = {
                        'lz': str(row.get('Landing Zone', '')),
                        'pad': str(row.get('PAD', '')),
                        'subarea': str(row.get('subarea', '')),
                        'stim': str(row.get('Stimulation Design', '')),
                        'lw': float(row.get('Long_estimulada_m', 0) or 0),
                        'stages': int(row.get('Stage Ejecuted', 0) or 0),
                        'sand_mlb': round(float(row.get('Total_Sand_lbs', 0) or 0) / 1e6, 2),
                        'prop_int': round(float(row.get('Prop_Int_lb/ft', 0) or 0), 0),
                        'fluid_int': round(float(row.get('Fluid_Int_bbl/ft', 0) or 0), 1),
                        'tvd': round(float(row.get('TVD_LP_m', 0) or 0), 1),
                        'toc': round(float(row.get('avg_TOC [%]', 0) or 0) * 100, 2),
                        'phit': round(float(row.get('avg_PHIT [%]', 0) or 0) * 100, 2),
                    }
            log(f"Datos estáticos cargados: {len(static)} pozos")
    except ImportError:
        log("pandas no disponible, saltando datos estáticos")
    except Exception as e:
        log(f"Error cargando estáticos: {e}")
    return static


def fetch_wells(token, project_id):
    log(f"Trayendo pozos del proyecto {project_id}...")
    return api_get(token, "/wells", params={"project_id": project_id})


def fetch_production(token, well_id):
    try:
        data = api_get(token, f"/wells/{well_id}/production_data")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def build_monthly(prod):
    """Agrupa producción diaria en promedios mensuales."""
    monthly = {}
    for d in prod:
        date = d.get('date', '')
        if not date:
            continue
        ym = str(date)[:7]
        if ym not in monthly:
            monthly[ym] = {'qo': [], 'qg': [], 'qw': []}
        monthly[ym]['qo'].append(d.get('qo_sc') or 0)
        monthly[ym]['qg'].append(d.get('qg_sc') or 0)
        monthly[ym]['qw'].append(d.get('qw_sc') or 0)

    result = []
    for ym in sorted(monthly.keys()):
        v = monthly[ym]
        n = len(v['qo'])
        result.append({
            'ym': ym,
            'qo': round(sum(v['qo']) / n, 1),
            'qg': round(sum(v['qg']) / n, 1),
            'qw': round(sum(v['qw']) / n, 1),
        })
    return result


def compute_stats(monthly):
    if not monthly:
        return 0, 0, 0, 0, 0, 0
    qo_all = [m['qo'] for m in monthly]
    qg_all = [m['qg'] for m in monthly]
    last30 = monthly[-1:]  # último mes
    qo_last = last30[0]['qo'] if last30 else 0
    qg_last = last30[0]['qg'] if last30 else 0
    qw_last = last30[0]['qw'] if last30 else 0
    return (
        round(max(qo_all), 1),
        round(qo_last, 1),
        round(qg_last, 1),
        round(qw_last, 1),
        round(qg_last / qo_last * 1000, 0) if qo_last > 0 else 0,
        round(qw_last / qo_last, 2) if qo_last > 0 else 0
    )


def push_to_github(data):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        log("GitHub no configurado. Guardando solo localmente.")
        return False

    content = json.dumps(data, ensure_ascii=False)
    encoded = base64.b64encode(content.encode()).decode()
    path = "data/wells.json"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    # Obtener SHA actual si existe
    sha = None
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        sha = r.json().get("sha")

    payload = {
        "message": f"Update wells data — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "content": encoded,
        "branch": GITHUB_BRANCH
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=headers, json=payload)
    if r.status_code in (200, 201):
        log(f"Datos subidos a GitHub: {GITHUB_REPO}/{path}")
        return True
    else:
        log(f"Error GitHub: {r.status_code} — {r.text[:200]}")
        return False


def main():
    print("=" * 55)
    print("  Phoenix Field Agent — Actualizador de datos")
    print("=" * 55)

    token = get_token()
    static = load_static_data()

    # Campos y proyectos
    fields = api_get(token, "/fields")
    log(f"Campos: {[f['name'] for f in fields]}")

    field_id = fields[0]["id"]
    projects = api_get(token, f"/fields/{field_id}/projects")

    project = next((p for p in projects if p["name"] == PROJECT_NAME), None)
    if not project:
        log(f"Proyecto '{PROJECT_NAME}' no encontrado. Disponibles: {[p['name'] for p in projects]}")
        return

    log(f"Proyecto: {project['name']} (id={project['id']})")
    wells_raw = fetch_wells(token, project["id"])
    log(f"Pozos encontrados: {len(wells_raw)}")

    wells_out = []
    for i, w in enumerate(wells_raw):
        name = w.get('name', f"id_{w['id']}")

        # Excluir sintéticos
        if any(p in name for p in EXCLUDE_PATTERNS):
            continue

        log(f"  [{i+1}/{len(wells_raw)}] {name}")
        prod = fetch_production(token, w['id'])
        monthly = build_monthly(prod)
        qo_max, qo_actual, qg_actual, qw_actual, gor, wor = compute_stats(monthly)

        fechas = sorted([m['ym'] for m in monthly])
        static_info = static.get(name, {})

        # Aplicar correcciones de LZ
        lz = LZ_CORRECTIONS.get(name, static_info.get('lz', ''))

        wells_out.append({
            "name": name,
            "subarea": static_info.get('subarea', ''),
            "lz": lz,
            "pad": static_info.get('pad', ''),
            "stim": static_info.get('stim', ''),
            "lw": static_info.get('lw', w.get('l_w', 0)),
            "stages": static_info.get('stages', 0),
            "sand_mlb": static_info.get('sand_mlb', 0),
            "prop_int": static_info.get('prop_int', 0),
            "fecha_inicio": fechas[0] if fechas else '',
            "fecha_ultimo": fechas[-1] if fechas else '',
            "Qo_max": qo_max,
            "Qo_actual": qo_actual,
            "Qg_actual": qg_actual,
            "Qw_actual": qw_actual,
            "GOR_actual": gor,
            "WOR_actual": wor,
            "monthly": monthly
        })

        time.sleep(0.1)

    log(f"\nPozos procesados: {len(wells_out)}")
    with_prod = [w for w in wells_out if w['monthly']]
    log(f"Con producción: {len(with_prod)}")

    # Guardar localmente
    os.makedirs("data", exist_ok=True)
    with open("data/wells.json", "w", encoding="utf-8") as f:
        json.dump(wells_out, f, ensure_ascii=False)
    log("Guardado: data/wells.json")

    # Subir a GitHub
    pushed = push_to_github(wells_out)

    print("\n" + "=" * 55)
    print(f"  Listo. {len(wells_out)} pozos actualizados.")
    if pushed:
        print(f"  App disponible en: https://{GITHUB_REPO.split('/')[0]}.github.io/{GITHUB_REPO.split('/')[1]}/")
    else:
        print("  Para ver la app localmente: abrí index.html en tu browser")
        print("  (necesitás un servidor local: python -m http.server 8080)")
    print("=" * 55)


if __name__ == "__main__":
    main()
