#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wizualizacja 3D odkształceń belki z czujników światłowodowych
==============================================================

Wymagania:
    pip install pandas openpyxl matplotlib numpy

Uruchomienie:
    python wizualizacja_3d.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RadioButtons
from mpl_toolkits.mplot3d import Axes3D          # noqa: F401
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


# ═══════════════════════════════════════════════════════════════════════════════
#  PARAMETRY — dostosuj do swojego układu pomiarowego
# ═══════════════════════════════════════════════════════════════════════════════

# Długość belki [m]
BEAM_L = 1.0

# ---------------------------------------------------------------------------
# Przekrój poprzeczny: lista wierzchołków (Y, Z) [m], podawanych
# w kolejności przeciwnej do ruchu wskazówek zegara patrząc od x=0.
#
# Układ współrzędnych przekroju:
#   środek = (Y=0, Z=0)
#   Y+ = prawa strona,   Z+ = góra
#
# Przykłady gotowych do użycia (odkomentuj wybrany):
#
# ── Prostokąt 0.20 × 0.40 m ──────────────────────────────────────────────
CROSS_SECTION = [
    (-0.10, -0.20),
    ( 0.10, -0.20),
    ( 0.10,  0.20),
    (-0.10,  0.20),
]
#
# ── Przekrój teowy (T) ────────────────────────────────────────────────────
# Stopka: 0.20 × 0.05 m,  żebro: 0.05 × 0.25 m
# CROSS_SECTION = [
#     (-0.10, -0.15),  # stopka – lewy dół
#     ( 0.10, -0.15),  # stopka – prawy dół
#     ( 0.10, -0.10),  # stopka – prawy góra
#     ( 0.025,-0.10),  # żebro  – prawy dół
#     ( 0.025, 0.15),  # żebro  – prawy góra
#     (-0.025, 0.15),  # żebro  – lewy góra
#     (-0.025,-0.10),  # żebro  – lewy dół
#     (-0.10, -0.10),  # stopka – lewy góra
# ]
#
# ── Koło (aproksymacja, 24 segmenty) ─────────────────────────────────────
# r = 0.15
# CROSS_SECTION = [(r*np.cos(a), r*np.sin(a))
#                  for a in np.linspace(0, 2*np.pi, 25)[:-1]]
# ---------------------------------------------------------------------------

# Czujniki światłowodowe
# Dla każdego czujnika podaj:
#   file   – ścieżka do pliku Excel
#   y, z   – pozycja w przekroju [m]
#   color  – kolor (hex lub nazwa matplotlib)
SENSORS = {
    '03': {
        'file':  '03_S10_do_S00.xlsx',
        'y':     -0.05,
        'z':     -0.12,
        'color': '#f38ba8',
    },
    '04': {
        'file':  '04_S10_do_S01.xlsx',
        'y':      0.05,
        'z':      0.08,
        'color': '#a6e3a1',
    },
}

# Kierunek wykresu odkształceń w przestrzeni 3D
#   'Z' = pionowo (typowy dla zginania)  /  'Y' = poziomo
STRAIN_DIR = 'Z'

# Skala automatyczna: maks. |ε| → SCALE_TARGET_FRAC × wymiaru przekroju
SCALE_TARGET_FRAC = 0.40

# Suwak skali — zakres mnożnika
SCALE_MAX_MULT  = 5.0
SCALE_INIT_MULT = 1.0

# Liczba punktów interpolacji wzdłuż belki
N_PTS = 300

# ═══════════════════════════════════════════════════════════════════════════════


# ── Wczytywanie danych ────────────────────────────────────────────────────────

def load_sensor(filepath: str) -> tuple:
    """
    Wczytuje wszystkie kolumny pomiarów z pliku Excel.

    Pierwsza kolumna to długość światłowodu [m].
    Każda kolejna kolumna to osobny pomiar (odkształcenia [με]).
    Zwracane są dane z ostatniego metra włókna (odcinek belki).

    Zwraca
    -------
    x       : np.ndarray, shape (N_PTS,)  — pozycja [0 … BEAM_L]
    names   : list[str]                   — nazwy kolumn pomiarów
    strains : list[np.ndarray]            — odkształcenia [με] dla każdego pomiaru
    """
    df = pd.read_excel(filepath)
    length_raw = df.iloc[:, 0].to_numpy(dtype=float)

    names:   list = []
    strains: list = []

    for col in df.columns[1:]:
        s_raw = df[col].to_numpy(dtype=float)
        ok = np.isfinite(length_raw) & np.isfinite(s_raw)
        lv, sv = length_raw[ok], s_raw[ok]

        order = np.argsort(lv)
        lv, sv = lv[order], sv[order]

        end_pos = lv[-1]
        mask = lv >= (end_pos - BEAM_L)
        x_raw, s_seg = lv[mask], sv[mask]

        x_norm = x_raw - x_raw[0]
        x_grid = np.linspace(0.0, BEAM_L, N_PTS)
        s_grid = np.interp(x_grid, x_norm / x_norm[-1] * BEAM_L, s_seg)

        names.append(str(col))
        strains.append(s_grid)

    x_out = np.linspace(0.0, BEAM_L, N_PTS)
    return x_out, names, strains


# ── Geometria belki ───────────────────────────────────────────────────────────

def extrude(verts_yz: list, x0: float, x1: float) -> list:
    """
    Wyciąga wielokąt przekroju wzdłuż osi X.
    Zwraca listę ścian (każda = lista punktów 3D) dla Poly3DCollection.
    """
    n = len(verts_yz)
    faces = []

    # Przekroje czołowe
    cap_a = [(x0, y, z) for y, z in verts_yz]
    cap_b = [(x1, y, z) for y, z in verts_yz]
    faces.append(cap_a)
    faces.append(cap_b[::-1])

    # Ściany boczne
    for i in range(n):
        j = (i + 1) % n
        ya, za = verts_yz[i]
        yb, zb = verts_yz[j]
        faces.append([
            (x0, ya, za),
            (x1, ya, za),
            (x1, yb, zb),
            (x0, yb, zb),
        ])

    return faces


def section_bounds(verts_yz: list) -> tuple:
    """Zwraca (y_min, y_max, z_min, z_max) dla wierzchołków przekroju."""
    ys = [v[0] for v in verts_yz]
    zs = [v[1] for v in verts_yz]
    return min(ys), max(ys), min(zs), max(zs)


# ── Rysowanie ─────────────────────────────────────────────────────────────────

def draw_beam(ax: Axes3D, verts_yz: list) -> None:
    """Półprzeźroczysta bryła belki z wyraźnymi przekrojami czołowymi."""
    faces = extrude(verts_yz, 0.0, BEAM_L)
    ax.add_collection3d(Poly3DCollection(
        faces, alpha=0.10,
        facecolor='#89b4fa', edgecolor='#7287fd', linewidth=0.5,
    ))
    # Przekroje czołowe – bardziej widoczne
    for xp in (0.0, BEAM_L):
        cap = [(xp, y, z) for y, z in verts_yz]
        ax.add_collection3d(Poly3DCollection(
            [cap], alpha=0.35,
            facecolor='#89b4fa', edgecolor='white', linewidth=1.5,
        ))


def draw_sensor_markers(ax: Axes3D, sensors: dict) -> None:
    """Znaczniki czujników w obu przekrojach czołowych + etykiety."""
    for sid, cfg in sensors.items():
        for xp in (0.0, BEAM_L):
            ax.scatter([xp], [cfg['y']], [cfg['z']],
                       color=cfg['color'], s=60, zorder=10, depthshade=False)
        ax.text(0.0, cfg['y'], cfg['z'], f'  {sid}',
                color=cfg['color'], fontsize=11, fontweight='bold', zorder=11)


def draw_strains(ax: Axes3D, sensor_data: dict, sensors: dict,
                 meas_idx: int, scale: float) -> list:
    """
    Rysuje profile odkształceń (linia bazowa + linia odkształceń + wstęga)
    dla wybranego pomiaru i wszystkich czujników.

    Zwraca listę Line3D do legendy.
    """
    handles = []
    for sid, cfg in sensors.items():
        x, _names, strains = sensor_data[sid]
        idx   = min(meas_idx, len(strains) - 1)
        s     = strains[idx]
        sy, sz, color = cfg['y'], cfg['z'], cfg['color']
        disp  = s * scale

        # Linia bazowa (oś czujnika) – przerywana
        ax.plot([0.0, BEAM_L], [sy, sy], [sz, sz],
                color=color, linewidth=0.8, linestyle='--', alpha=0.45)

        if STRAIN_DIR == 'Z':
            lz = sz + disp
            line, = ax.plot(x, np.full(N_PTS, sy), lz,
                            color=color, linewidth=2.2, alpha=0.95,
                            label=f'Czujnik {sid}')
            X_s = np.vstack([x, x])
            Y_s = np.full((2, N_PTS), sy)
            Z_s = np.vstack([np.full(N_PTS, sz), lz])
        else:  # 'Y'
            ly = sy + disp
            line, = ax.plot(x, ly, np.full(N_PTS, sz),
                            color=color, linewidth=2.2, alpha=0.95,
                            label=f'Czujnik {sid}')
            X_s = np.vstack([x, x])
            Y_s = np.vstack([np.full(N_PTS, sy), ly])
            Z_s = np.full((2, N_PTS), sz)

        ax.plot_surface(X_s, Y_s, Z_s,
                        color=color, alpha=0.18,
                        linewidth=0, antialiased=False)
        handles.append(line)

    return handles


def set_axes_style(ax: Axes3D, verts_yz: list) -> None:
    y_min, y_max, z_min, z_max = section_bounds(verts_yz)
    span_y = y_max - y_min
    span_z = z_max - z_min
    pad_y  = span_y * 1.5
    pad_z  = span_z * 0.8

    ax.set_xlabel('X [m]  —  długość belki', color='white', labelpad=10)
    ax.set_ylabel('Y [m]  —  szerokość',     color='white', labelpad=8)
    ax.set_zlabel('Z [m]  —  wysokość',      color='white', labelpad=8)

    ax.set_xlim(0.0, BEAM_L)
    ax.set_ylim(y_min - pad_y / 2, y_max + pad_y / 2)
    ax.set_zlim(z_min - pad_z / 2, z_max + pad_z / 2)

    ax.tick_params(colors='white', labelsize=8)
    for pane in (ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane):
        pane.fill = False
        pane.set_edgecolor('#313244')
    ax.grid(True, color='#313244', linewidth=0.4)


# ── Aplikacja ─────────────────────────────────────────────────────────────────

def main() -> None:
    # Wczytaj dane ze wszystkich czujników
    sensor_data = {sid: load_sensor(cfg['file']) for sid, cfg in SENSORS.items()}

    # Nazwy pomiarów z pierwszego czujnika (zakładamy tę samą kolejność)
    first_sid   = next(iter(sensor_data))
    _, meas_names, _ = sensor_data[first_sid]
    n_meas      = len(meas_names)

    # Etykiety w RadioButtons: skrócone do 22 znaków
    def shorten(s: str, maxlen: int = 22) -> str:
        return s if len(s) <= maxlen else s[:maxlen - 1] + '…'

    radio_labels = [f'[{i+1}]  {shorten(n)}' for i, n in enumerate(meas_names)]

    # Skala automatyczna
    all_strains = [s for _, _, sts in sensor_data.values() for s in sts]
    max_strain  = max(np.max(np.abs(s)) for s in all_strains) if all_strains else 1.0
    y_min, y_max, z_min, z_max = section_bounds(CROSS_SECTION)
    dim_ref     = (z_max - z_min) if STRAIN_DIR == 'Z' else (y_max - y_min)
    scale_base  = (dim_ref * SCALE_TARGET_FRAC) / max_strain if max_strain > 0 else 1e-5

    # Stan aplikacji
    state = {'meas_idx': 0, 'scale_mult': SCALE_INIT_MULT}

    # ── Budowa okna ───────────────────────────────────────────────────────────
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(15, 8))
    fig.patch.set_facecolor('#1e1e2e')
    try:
        fig.canvas.manager.set_window_title(
            'Wizualizacja 3D — odkształcenia belki (czujniki światłowodowe)'
        )
    except Exception:
        pass

    # Oś 3D — lewa część okna
    ax: Axes3D = fig.add_axes([0.02, 0.12, 0.70, 0.85], projection='3d')
    ax.set_facecolor('#1e1e2e')

    # Panel wyboru pomiaru — RadioButtons (prawy panel)
    row_h      = 0.055
    panel_h    = min(row_h * n_meas + 0.10, 0.75)
    panel_y    = 0.50 - panel_h / 2
    ax_radio   = fig.add_axes([0.74, panel_y, 0.24, panel_h])
    ax_radio.set_facecolor('#313244')
    radio = RadioButtons(ax_radio, radio_labels, activecolor='#f38ba8')
    ax_radio.set_title('Wybór pomiaru', color='#cdd6f4',
                       fontsize=9, pad=6, fontweight='bold')
    for lbl in radio.labels:
        lbl.set_color('#cdd6f4')
        lbl.set_fontsize(8)

    # Suwak skali — dół okna
    ax_sl  = fig.add_axes([0.08, 0.040, 0.58, 0.025])
    slider = Slider(ax_sl, 'Skala  [×]', 0.0, SCALE_MAX_MULT,
                    valinit=SCALE_INIT_MULT,
                    color='#f38ba8', track_color='#313244')
    slider.label.set_color('white')
    slider.valtext.set_color('white')

    # Informacja o skali bezwzględnej
    scale_txt = fig.text(0.68, 0.045, '', color='#a6adc8',
                         fontsize=8, ha='left', va='center')

    # ── Rysowanie sceny ───────────────────────────────────────────────────────
    def draw_scene() -> None:
        elev, azim = ax.elev, ax.azim

        ax.cla()
        ax.set_facecolor('#1e1e2e')

        scale = scale_base * state['scale_mult']
        idx   = state['meas_idx']

        draw_beam(ax, CROSS_SECTION)
        draw_sensor_markers(ax, SENSORS)
        handles = draw_strains(ax, sensor_data, SENSORS, idx, scale)
        set_axes_style(ax, CROSS_SECTION)

        ax.legend(handles=handles, loc='upper left',
                  facecolor='#313244', edgecolor='#89b4fa',
                  labelcolor='white', fontsize=10)

        meas_label = meas_names[idx] if idx < len(meas_names) else '?'
        ax.set_title(
            f'Odkształcenia włókniste  ·  belka L = {BEAM_L:.2f} m  ·  '
            f'{meas_label}\n'
            f'skala = {scale:.3e} m/με',
            color='white', fontsize=9, pad=10,
        )
        scale_txt.set_text(f'{scale:.3e} m/με   ({scale * 1000:.5f} mm/με)')

        ax.view_init(elev=elev, azim=azim)
        fig.canvas.draw_idle()

    # ── Callbacki ─────────────────────────────────────────────────────────────
    def on_slider(val: float) -> None:
        state['scale_mult'] = val
        draw_scene()

    def on_radio(label: str) -> None:
        state['meas_idx'] = radio_labels.index(label)
        draw_scene()

    slider.on_changed(on_slider)
    radio.on_clicked(on_radio)

    draw_scene()
    plt.show()


if __name__ == '__main__':
    main()
