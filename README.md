# Wizualizacja 3D odkształceń belki — czujniki światłowodowe

Interaktywna wizualizacja trójwymiarowych odkształceń belki mierzonej metodą rozproszenia Brillouina (BOTDR/BOTDA) przy użyciu czujników światłowodowych.

## Opis

Program wczytuje dane z plików Excel, wyodrębnia odcinek pomiarowy odpowiadający długości belki i wyświetla odkształcenia jako trójwymiarowe wykresy nałożone na model geometryczny belki. Model można swobodnie obracać myszą, a skalę wykresów odkształceń reguluje się suwakiem. Gdy plik zawiera kilka pomiarów, można przełączać między nimi w panelu bocznym.

## Przykładowy widok

```
[okno matplotlib z ciemnym tłem]
┌──────────────────────────────────┬──────────────────┐
│                                  │  Wybór pomiaru   │
│   Belka 3D (półprzeźroczysta)    │  ○ [1] pomiar 1  │
│   + wykresy odkształceń          │  ● [2] pomiar 2  │
│     czujnik 03 (różowy)          │                  │
│     czujnik 04 (zielony)         │                  │
│                                  │                  │
│  [obrót myszą]                   │                  │
└──────────────────────────────────┴──────────────────┘
   Skala [×] ──────●────────────────────  2.3×
```

## Instalacja

```bash
# Sklonuj repozytorium
git clone <url-repozytorium>
cd wizualizacja_3d

# Utwórz środowisko wirtualne
python3 -m venv .venv
source .venv/bin/activate      # Linux / macOS / WSL
# .venv\Scripts\activate       # Windows PowerShell

# Zainstaluj zależności
pip install -r requirements.txt
```

## Uruchomienie

```bash
source .venv/bin/activate
python3 wizualizacja_3d.py
```

### Windows + WSL

```bash
wsl -d Ubuntu-24.04 -- bash -c "
  cd ~/Python/git/wizualizacja_3d &&
  source .venv/bin/activate &&
  python3 wizualizacja_3d.py
"
```

## Format plików danych (Excel)

Każdy czujnik ma oddzielny plik `.xlsx` o następującej strukturze:

| Kolumna 1 | Kolumna 2 | Kolumna 3 | … |
|-----------|-----------|-----------|---|
| Długość światłowodu [m] | Pomiar referencyjny | Pomiar 1 [με] | Pomiar N [με] |

- **Kolumna 1** — pozycja wzdłuż kabla (światłowód może być dłuższy niż belka; program automatycznie pobiera **ostatni metr** danych odpowiadający odcinkowi belki)
- **Kolumna 2+** — odkształcenia w mikroepsilonach [με]; każda kolumna to oddzielny stan obciążenia lub czas pomiaru

## Konfiguracja programu

Wszystkie parametry znajdują się w sekcji `PARAMETRY` na początku pliku `wizualizacja_3d.py`.

### Długość belki

```python
BEAM_L = 1.0   # [m]
```

### Kształt przekroju poprzecznego

Przekrój definiowany jest jako lista wierzchołków `(Y, Z)` w metrach, w kolejności przeciwnej do ruchu wskazówek zegara (patrząc od `x = 0`). Środek układu `(Y=0, Z=0)`.

```python
# Prostokąt 0.20 × 0.40 m
CROSS_SECTION = [
    (-0.10, -0.20),   # lewy dół
    ( 0.10, -0.20),   # prawy dół
    ( 0.10,  0.20),   # prawy góra
    (-0.10,  0.20),   # lewy góra
]
```

Przykłady innych przekrojów (gotowe do wklejenia):

```python
# Przekrój teowy (T): stopka 0.20×0.05 m, żebro 0.05×0.25 m
CROSS_SECTION = [
    (-0.10, -0.15), ( 0.10, -0.15), ( 0.10, -0.10),
    ( 0.025,-0.10), ( 0.025, 0.15), (-0.025, 0.15),
    (-0.025,-0.10), (-0.10, -0.10),
]

# Koło R = 0.15 m (24 segmenty)
import numpy as np
r = 0.15
CROSS_SECTION = [(r*np.cos(a), r*np.sin(a))
                 for a in np.linspace(0, 2*np.pi, 25)[:-1]]
```

### Czujniki

```python
SENSORS = {
    '03': {
        'file':  '03_S10_do_S00.xlsx',  # ścieżka do pliku Excel
        'y':     -0.05,                 # pozycja Y w przekroju [m]
        'z':     -0.12,                 # pozycja Z w przekroju [m]
        'color': '#f38ba8',             # kolor (hex)
    },
    '04': {
        'file':  '04_S10_do_S01.xlsx',
        'y':      0.05,
        'z':      0.08,
        'color': '#a6e3a1',
    },
    # Dodaj kolejne czujniki analogicznie...
}
```

### Kierunek wykresu odkształceń

```python
STRAIN_DIR = 'Z'   # 'Z' = pionowo (typowy dla zginania)
                   # 'Y' = poziomo
```

### Skala

```python
SCALE_TARGET_FRAC = 0.40  # przy suwaku 1×: maks. |ε| = 40% wymiaru przekroju
SCALE_MAX_MULT    = 5.0   # górna granica suwaka
```

## Interakcja z oknem

| Akcja | Efekt |
|-------|-------|
| Przeciągnij myszą (lewy przycisk) | Obrót modelu 3D |
| Kółko myszy | Zoom |
| Suwak **Skala [×]** | Zmiana skali wykresów odkształceń |
| Przyciski **Wybór pomiaru** | Przełączanie między pomiarami (wszystkie czujniki jednocześnie) |

## Wymagania systemowe

- Python 3.10+
- WSL2 (Windows) z WSLg lub natywny Linux / macOS
- Pakiety: `pandas`, `openpyxl`, `matplotlib`, `numpy`

## Struktura projektu

```
wizualizacja_3d/
├── wizualizacja_3d.py      ← główny skrypt
├── requirements.txt        ← zależności Python
├── README.md               ← dokumentacja
├── 03_S10_do_S00.xlsx      ← dane czujnika 03
└── 04_S10_do_S01.xlsx      ← dane czujnika 04
```
