# Adaptive Cover rako Edition 1.6.1

[Polski](#polski) | [English](#english)

Adaptive Cover rako Edition is a custom Home Assistant integration for automatic control of
roller shutters, awnings and tilting blinds. It combines solar geometry,
indoor and outdoor temperature, weather measurements, schedules, open-window
policies and bounded behavioral learning. Every runtime decision is explainable
and available in diagnostics schema v4.

> This is an independently maintained fork of
> [basbruss/adaptive-cover](https://github.com/basbruss/adaptive-cover). It
> preserves the MIT license and attribution required for the original project;
> project maintenance, releases, documentation and issue handling are provided
> by [@rako79](https://github.com/rako79).

> The integration directly controls physical `cover` entities. Test a new
> configuration with **Dry run** enabled before allowing automatic movement.

---

# Polski

## Najważniejsze możliwości

- Obsługa rolet pionowych, markiz poziomych i żaluzji z uchyłem.
- Obliczanie pozycji na podstawie azymutu i wysokości słońca oraz geometrii
  okna lub osłony.
- Tryb podstawowy oraz tryb klimatyczny uwzględniający temperaturę,
  nasłonecznienie, pogodę i obecność.
- Bezpośrednia ochrona przed deszczem, silnym wiatrem, zimnem i słońcem.
- Nocne przewietrzanie z twardą godziną zakończenia.
- Podtrzymanie ochrony termicznej tylko po rzeczywistym nasłonecznieniu danego
  okna.
- Cztery polityki zachowania po otwarciu okna lub drzwi balkonowych.
- Automatyczne wykrywanie ręcznego sterowania i czasowe wstrzymanie automatyki.
- Trwały `BehavioralLearner`, który uczy niewielkich preferencji użytkownika.
- Ochrona silnika: minimalna zmiana pozycji, minimalny odstęp, cooldown oraz
  limity ruchów na godzinę i dobę.
- Weryfikacja osiągnięcia celu, bezpieczne retry i tolerancja niedokładnych
  pozycji krańcowych, np. `97%` jako osiągnięte `100%`.
- Eksport i import ustawień oraz rozbudowana diagnostyka v4.
- Polskie i angielskie tłumaczenia encji, opcji i usług.

## Wymagania

- Home Assistant `2026.7.0` lub nowszy z gałęzi `2026.x`.
- Python `3.14.2` lub nowszy z gałęzi `3.14` po stronie Home Assistant.
- Fizyczna encja `cover` obsługująca ustawianie pozycji albo pozycji uchyłu.
- Poprawnie skonfigurowana lokalizacja i strefa czasowa Home Assistant.

## Instalacja

### HACS

1. Dodaj `https://github.com/rako79/adaptive-cover` jako niestandardowe
   repozytorium integracji w HACS.
2. Wyszukaj i zainstaluj **Adaptive Cover rako Edition**.
3. Uruchom ponownie Home Assistant.
4. Przejdź do **Ustawienia -> Urządzenia i usługi -> Dodaj integrację** i
   wybierz **Adaptive Cover rako Edition**.

> Ten fork zachowuje domenę `adaptive_cover` dla zgodności z istniejącymi
> wpisami konfiguracji. Nie instaluj go równolegle z innym wariantem Adaptive
> Cover; HACS powinien zarządzać jedną kopią tej integracji.

### Ręcznie

1. Skopiuj katalog `custom_components/adaptive_cover` do katalogu
   `/config/custom_components/adaptive_cover` w Home Assistant.
2. Upewnij się, że nie istnieje druga kopia, np.
   `/config/custom_components/adaptive_cover copy`.
3. Uruchom ponownie Home Assistant i dodaj integrację z interfejsu.

Po aktualizacji plików zawsze wykonaj pełny restart Home Assistant. Samo
odświeżenie przeglądarki nie przeładowuje kodu Pythona.

## Konfiguracja

Każdy wpis konfiguracji reprezentuje jedną grupę osłon o wspólnej geometrii i
logice. Jedna fizyczna roleta nie może należeć do kilku wpisów Adaptive Cover.
Duplikaty są odrzucane podczas konfiguracji, importu i uruchamiania.

### Typy osłon

| Typ | Zastosowanie | Najważniejsze dane |
| --- | --- | --- |
| Roleta pionowa | Roleta poruszająca się góra/dół | wysokość okna, wymagany obszar cienia, głębokość okna i parapetu |
| Markiza pozioma | Markiza wysuwana nad oknem lub tarasem | długość markizy i kąt montażu |
| Żaluzja z uchyłem | Lamele sterowane kątem | rozstaw, głębokość i zakres obrotu lameli |

### Geometria słońca

- `set_azimuth` określa kierunek, w który skierowane jest okno.
- `fov_left` i `fov_right` definiują pole widzenia okna.
- `min_elevation` i `max_elevation` mogą ograniczyć aktywny zakres wysokości
  słońca.
- Opcjonalna martwa strefa wyklucza fragment pola widzenia, np. zasłonięty przez
  sąsiedni budynek.
- Interpolacja pozwala zdefiniować własne pozycje dla zakresów azymutu.
- Obliczenia są zabezpieczone przed `NaN`, dzieleniem przez zero i skrajną
  geometrią.

### Tryby działania

**Tryb podstawowy** używa pozycji słońca, geometrii osłony, zakresu czasu oraz
pozycji domyślnej i nocnej.

**Tryb klimatyczny** rozszerza obliczenia o:

- temperaturę wewnętrzną i zewnętrzną,
- progi komfortu `temp_low` i `temp_high`,
- pogodę i prognozę temperatury,
- obecność,
- pomiar lux lub irradiancji z histerezą,
- ochronę przed zimnem, deszczem i wiatrem,
- nocne przewietrzanie,
- ochronę przed świtem,
- Strict Sun Block,
- podtrzymanie ochrony termicznej.

## Kolejność decyzji

Reguły mają jawne priorytety. Wyższa reguła nie może zostać zmieniona przez
niższą decyzję komfortową.

| Priorytet | Reguła | Zachowanie |
| ---: | --- | --- |
| 110 | Wyłączone sterowanie | oblicza cel, ale nie wykonuje ruchu |
| 105 | Otwarte okno | stosuje wybraną politykę bezpieczeństwa |
| 100 | Deszcz / silny wiatr | ustawia skonfigurowaną pozycję awaryjną |
| 98 | Minimalna / maksymalna pozycja | nakłada fizyczne ograniczenia pozycji |
| 95 | Ochrona przed zimnem | zamyka osłonę nocą poniżej progu temperatury |
| 90 | Ochrona przed świtem | ogranicza wczesne światło w wybranych miesiącach |
| 85 | Strict Sun Block | blokuje bezpośrednie silne słońce w oknie |
| 80 | Nocne przewietrzanie | uchyla roletę do skonfigurowanej pozycji |
| 70 | Koniec harmonogramu / przewietrzania | przywraca skonfigurowaną pozycję nocną |
| 60 | Thermal Hold | czasowo utrzymuje ochronę po bezpośrednim słońcu |
| 50 | Tryb nocny | używa pozycji po zachodzie |
| 40 | Okno w cieniu | wraca do pozycji domyślnej |
| 10 | Automatyka komfortowa | używa wyniku geometrii i klimatu |

Diagnostyka zawiera `decision_trace`, który pokazuje reguły aktywne, wybraną
regułę oraz reguły nadpisane wyższym priorytetem.

## Funkcje klimatyczne

### Słabe promieniowanie

W trybie klimatycznym bieżący sygnał lux lub irradiancji ma pierwszeństwo przed
samą prognozą. Jeżeli `low_light=true` i `thermal_stress=0`, integracja ustawia
pozycję domyślną, nawet gdy prognoza temperatury oznaczyła dzień jako letni.
Dodatni stres termiczny nadal utrzymuje ochronę, na przykład gdy powietrze
zewnętrzne jest gorętsze od wnętrza.

Jeżeli skonfigurowany czujnik temperatury pomieszczenia jest niedostępny,
integracja nie zastępuje go temperaturą zewnętrzną. Ochrona termiczna pozostaje
nieaktywna do odzyskania wiarygodnego pomiaru wewnętrznego, a diagnostyka
pokazuje `temperature_source=inside_unavailable`.

### Nocne przewietrzanie

Nocne przewietrzanie działa od zachodu słońca do `night_purge_end_time`, jeżeli
temperatura wewnętrzna jest wyższa od progu komfortu, a na zewnątrz jest
chłodniej niż w pomieszczeniu. Po osiągnięciu godziny końcowej integracja ustawia
skonfigurowaną pozycję nocną. Restart lub przeładowanie wykonane po terminie, ale
przed rozpoczęciem harmonogramu dziennego, powoduje natychmiastowe nadrobienie
pominiętego zamknięcia.

Ochrona przed zimnem, deszczem i wiatrem ma wyższy priorytet niż przewietrzanie.
Ochrona przed zimnem ma histerezę `1°C`: po aktywacji poniżej progu pozostaje
włączona do czasu, aż temperatura zewnętrzna osiągnie próg powiększony o `1°C`.
Duży skok czujnika temperatury zewnętrznej, przekraczający `3°C`, musi utrzymać
się przez pięć minut. Krótszy skok jest odrzucany przed oceną ochrony zimna i
nocnego przewietrzania. Diagnostyka pokazuje wartość surową, zaakceptowaną,
kandydata oraz liczbę odrzuconych odczytów.

Start przewietrzania wymaga temperatury pokojowej powyżej `temp_low + 0,5°C`
i powietrza zewnętrznego chłodniejszego o ponad `1°C`. Rozpoczęte przewietrzanie
trwa do spadku temperatury pokojowej do `temp_low` lub różnicy temperatur
do `0,2°C`. Kontaktron nie jest wymagany do uruchomienia tej funkcji;
skonfigurowane polityki otwartego okna nadal obowiązują.

### Podtrzymanie ochrony termicznej

`thermal_hold_after_sun` działa tylko wtedy, gdy konkretne okno było wcześniej
rzeczywiście wystawione na bezpośrednie słońce. Ochrona zostaje zwolniona:

- po upływie `thermal_hold_duration`,
- gdy na zewnątrz jest chłodniej od wnętrza co najmniej o
  `thermal_hold_release_delta`,
- gdy nie występuje stres termiczny.

### Deszcz i wiatr

- Fizyczny czujnik deszczu ma pierwszeństwo przed opisem prognozy pogody.
- Prędkość wiatru jest przeliczana do `km/h` z `m/s`, `mph` lub węzłów.
- Można ustawić osobne pozycje awaryjne dla deszczu i wiatru.
- Opcja `rain_night_only` ogranicza reakcję na deszcz do pory nocnej.
- Deszcz i wiatr omijają harmonogram, ręczne przejęcie, cooldown oraz limity
  ruchów. Polityka otwartego okna nadal ma najwyższy priorytet.

Strict Sun Block wymaga aktualnego numerycznego odczytu irradiancji lub lux
większego od progu włączenia. Stan `unknown`, `unavailable` albo brak odczytu nie
jest traktowany jako silne słońce. Podczas uruchamiania Home Assistant integracja
korzysta z `async_at_started`, czeka na stabilizację encji i dopiero potem może
wysłać pierwsze polecenie. Ten sam mechanizm działa przy przeładowaniu integracji.

## Otwarte okno lub drzwi

Obsługiwane polityki `window_open_action`:

| Polityka | Działanie |
| --- | --- |
| `pause` | wstrzymuje automatyczne ruchy |
| `move_to_position` | ustawia `window_open_position` |
| `block_closing_only` | pozwala otwierać, ale blokuje dalsze zamykanie |
| `return_after_close` | wstrzymuje automatykę i wraca do celu po zamknięciu okna |

## Ręczne sterowanie

Integracja odróżnia własne polecenia od ruchów użytkownika. Po wykryciu ręcznej
zmiany dana roleta pozostaje poza automatyką przez wybrany czas. Dostępne czasy
to: brak, 15, 30, 60, 120, 240 minut albo do zachodu słońca.
Raporty pozycji odebrane przez dwie minuty po wysłaniu polecenia są przypisywane
do ruchu automatyki. Po osiągnięciu celu powtórzony raport jest porównywany z
ostatnią fizycznie zadaną pozycją, a nie z kolejną kalkulacją.

`manual_ignore_intermediate` pozwala ignorować przejściowe stany `opening` i
`closing`. Przycisk resetu ręcznego sterowania przywraca aktualny bezpieczny cel
i czeka maksymalnie 120 sekund na zakończenie ruchu.

Termin przejęcia jest zapisywany jako stała chwila. Wariant „do zachodu słońca”
nie skraca się podczas kolejnych odświeżeń i po zachodzie wskazuje następny
zachód.

## BehavioralLearner

Uczenie jest zapisywane osobno dla każdego wpisu konfiguracji w Home Assistant
Store. Po potwierdzonej ręcznej zmianie aktualizuje:

- korektę pozycji ograniczoną do `-25...+25` punktów procentowych,
- korektę temperatury komfortu ograniczoną do `-3...+3°C`,
- licznik ręcznych korekt.

Uczenie działa wyłącznie podczas aktywnego harmonogramu i tylko dla decyzji
komfortowych. Nie może zmienić pozycji bezpieczeństwa wynikających z deszczu,
wiatru, zimna ani Strict Sun Block.
Przycisk **Reset Behavioral Learning** usuwa wszystkie wyuczone korekty wpisu.
Znacznik ostatniego bezpośredniego słońca jest zapisywany oddzielnie i przetrwa
restart Home Assistant, dzięki czemu Thermal Hold nie traci kontekstu.
Aktualizacja mechanizmu rozpoznawania ruchu i harmonogramu jednorazowo zeruje
starsze korekty, które mogły powstać z raportów pośrednich napędu lub ruchów
spoza czasu automatyki. Znacznik słońca nie jest przy tym usuwany.

## Harmonogram i źródła czasu

Godzina rozpoczęcia ma kolejność: encja startu, godzina dnia roboczego/wolnego
przy skonfigurowanej encji Workday, a następnie uniwersalne `start_time`.
Niedostępna encja Workday nie jest uznawana za dzień wolny.

Godzina zakończenia ma kolejność: encja końca, jawne `end_time`, a dopiero potem
zachód słońca z `close_sunset_offset`. Encja przesunięcia zachodu jest zawsze
dostępna, także po zmianie źródła czasu. Jej wartość wpływa na harmonogram tylko
przy zamknięciu solarnym. Zmiana terminu na wcześniejszy oraz termin pominięty
podczas restartu są obsługiwane przy najbliższym odświeżeniu.

## Ochrona silnika i retry

| Opcja | Domyślnie | Znaczenie |
| --- | ---: | --- |
| `delta_position` | `1%` | minimalna różnica pozycji wymagana do ruchu |
| `delta_time` | `2 min` | minimalny odstęp między automatycznymi zmianami |
| `global_cooldown` | `5 min` | przerwa po dowolnym poleceniu dla tej samej rolety |
| `max_moves_per_hour` | `8` | godzinowy limit poleceń; `0` wyłącza limit |
| `max_moves_per_day` | `40` | dobowy limit poleceń; `0` wyłącza limit |

Polecenia mają numer generacji. Opóźnione retry sprawdza ponownie aktualny cel,
stan sterowania, ręczne przejęcie, politykę okna i limity. Stare zadanie nie może
wykonać ruchu po zmianie warunków. Zadania retry działają w tle, nie blokują
startu Home Assistant i są anulowane podczas wyładowania integracji.

Warunki są ponownie oceniane co minutę, również bez zmian czujników. Wygaśnięcie
blokady lub ręcznego przejęcia pozwala wznowić automatykę z aktualnym celem.
Weryfikacja napędu następuje po `45 s` lub od razu po potwierdzającym zdarzeniu;
samo ponowienie nadal respektuje limity. Identyczne polecenia podczas oczekiwania
na cel są łączone. Historia poleceń zapisuje przyczynę, wyzwalacz, odczyty,
pozycję początkową, cel i rodzaj polecenia (`initial`, `retry`, `dry_run`).
Eksport diagnostyki nie wysyła poleceń ani nie przejmuje oczekujących zdarzeń.

## Najważniejsze wartości domyślne

| Opcja | Wartość |
| --- | ---: |
| Pozycja domyślna | `60%` |
| Pozycja po zachodzie | `0%` |
| Komfort niski / wysoki | `21°C / 25°C` |
| Próg zimna | `16°C` |
| Próg silnego wiatru | `40 km/h` |
| Nocne przewietrzanie | włączone |
| Koniec nocnego przewietrzania | `07:00` |
| Pozycja przewietrzania | `15%` |
| Thermal Hold | wyłączony |
| Pozycja Thermal Hold | `30%` |
| Czas Thermal Hold | `120 min` |
| Zwolnienie Thermal Hold | `1°C` |
| Ręczne przejęcie | `15 min` |

## Encje

Każdy wpis tworzy:

- sensor wyliczonej pozycji,
- sensory początku i końca nasłonecznienia,
- sensor metody sterowania: `winter`, `intermediate` lub `summer`,
- sensor statusu algorytmu,
- sensor tekstowego uzasadnienia decyzji,
- sensor harmonogramu: `active`, `disabled` lub `outside_schedule`,
- binary sensor bezpośredniego słońca,
- binary sensor ręcznego przejęcia,
- przełącznik automatyki,
- przełącznik wykrywania ręcznego sterowania,
- przełącznik Dry Run,
- wybór czasu ręcznego przejęcia,
- przycisk resetu ręcznego sterowania,
- przycisk resetu BehavioralLearner,
- liczbę przesunięcia zamknięcia względem zachodu,
- encję czasu otwarcia; przy sensorze Workday osobno dla dni roboczych i wolnych.

W trybie klimatycznym pojawiają się również przełączniki trybu klimatycznego,
źródła temperatury, lux, irradiancji i Strict Sun Block, zależnie od konfiguracji.

## Usługi

### Eksport ustawień

```yaml
action: adaptive_cover.export_config
data:
  filename: adaptive_cover_settings.json
  include_date: true
```

Domyślnie powstaje plik, np.
`12.07.2026_adaptive_cover_settings.json`, w katalogu `/config`.

### Import ustawień

```yaml
action: adaptive_cover.import_config
data:
  filename: 12.07.2026_adaptive_cover_settings.json
```

Import jest transakcyjnie walidowany i zachowuje zgodność ze starszym formatem.
Aktualizuje istniejące wpisy dopasowane po `entry_id` lub tytule. Nie tworzy
automatycznie brakujących wpisów konfiguracji.

### Eksport diagnostyki

```yaml
action: adaptive_cover.export_diagnostics
data:
  filename: adaptive_cover_diagnostics.json
  include_date: true
  refresh: true
```

Odświeżenie jest domyślnie włączone, działa read-only, nie wysyła poleceń ruchu
i ma limit 30 sekund.

## Diagnostyka v4

Eksport oraz standardowa diagnostyka Home Assistant używają tego samego
schematu. Zawierają:

- wersję integracji, Home Assistant i Pythona,
- strefę czasową i ścieżkę załadowanego komponentu,
- wersję, stan, źródło i walidację `ConfigEntry`,
- aktualną decyzję i maksymalnie 50 ostatnich decyzji,
- ślad priorytetów `decision_trace`,
- aktualne pozycje, błąd pozycji, tolerancję i `target_satisfied`,
- ostatnie polecenia, ich czas, błędy usług i historię ruchów,
- stan i terminy zadań retry,
- zdrowie koordynatora i czas odświeżeń,
- harmonogram, cache prognozy, `low_light`, tryb sezonowy, stan nocnego
  przewietrzania i progi ochrony zimna,
- stany i świeżość wszystkich powiązanych encji,
- stan odczytu i zapisu BehavioralLearner.

Historie są ograniczone do 50 wpisów i rozpoczynają się od nowa po restarcie.
Przed publicznym udostępnieniem diagnostyki sprawdź ścieżki, identyfikatory
encji i kontekst stanów.

## Rozwiązywanie problemów

1. Sprawdź sensor uzasadnienia decyzji i `target_position`.
2. Sprawdź `control_toggle`, `manual_override`, `window_open` oraz `dry_run`.
3. Porównaj `current_position`, `position_error`, `effective_tolerance` i
   `target_satisfied`.
4. Sprawdź `last_skip_reason`, `last_service_error` i `verify_tasks`.
5. Upewnij się, że działa tylko katalog
   `/config/custom_components/adaptive_cover`.
6. Wyeksportuj diagnostykę z `refresh: true` i dołącz aktualne logi HA.

`position_delta_too_small` zwykle nie oznacza błędu. Informuje, że różnica jest
mniejsza od skonfigurowanego progu i kolejne polecenie nie jest potrzebne.

## Rozwój i testy

```powershell
.\.venv\Scripts\ruff.exe check --no-cache custom_components\adaptive_cover tests
.\.venv\Scripts\ruff.exe format --check custom_components\adaptive_cover tests
.\.venv\Scripts\python.exe tests\run_pytest.py -q
.\.venv\Scripts\python.exe -m compileall -q custom_components\adaptive_cover tests
```

Blueprinty w `custom_components/adaptive_cover/blueprints` są rozwiązaniem
legacy przeznaczonym wyłącznie dla dodatkowych osłon. Nie należy nimi ponownie
sterować roletami przypisanymi bezpośrednio do integracji.

## Architektura 1.6

Każde odświeżenie przechodzi przez jeden przepływ:

`zdarzenie/timer -> snapshot wejść -> kandydaci -> arbiter -> limity i polityki runtime -> movement.py -> usługa cover`

- `coordinator.py` składa zależności, a `coordinator_pipeline.py` prowadzi
  krótkie fazy pojedynczego cyklu aktualizacji.
- `coordinator_events.py` przechowuje przyczyny odświeżeń oraz zarządza
  zdarzeniami i timerami.
- `coordinator_data.py` pobiera wartości HA raz i buduje snapshot wejść.
- `geometry.py` oblicza geometrię, a `climate.py` tworzy kandydatów bez
  bezpośredniego odczytywania `hass.states`.
- `decision.py` jest wspólnym arbitrem priorytetów, śladu decyzji i fizycznych
  ograniczeń pozycji.
- `coordinator_execution.py` stosuje polityki wykonawcze.
- `movement.py` jest jedyną bramką wywołań usług domeny `cover`, weryfikacji i
  retry.
- `manual_control.py`, `learning.py`, `schedule.py`, `models.py` i `options.py`
  utrzymują niezależne polityki domenowe.

Nowsze zdarzenie otrzymuje rosnącą generację. Jeżeli pojawi się podczas
sterowania grupą rolet, pozostałe stare cele są pomijane, a kolejny cykl
oblicza aktualną decyzję. Timer końca nocnego wietrzenia nie ustawia pozycji
bezpośrednio.

---

# English

## Key features

- Supports vertical roller shutters, horizontal awnings and tilting blinds.
- Calculates position from solar azimuth, elevation and cover geometry.
- Basic mode and climate mode with temperature, irradiance, weather and
  occupancy inputs.
- Direct protection against rain, strong wind, cold conditions and sunlight.
- Night purge with a hard local end time.
- Thermal protection hold only after actual direct sun on the specific window.
- Four open-window policies.
- Automatic manual-override detection and timed return to automation.
- Persistent bounded `BehavioralLearner` preferences.
- Motor protection through minimum position delta, minimum interval, cooldown,
  hourly limits and daily limits.
- Target verification, safe retries and tolerance for imprecise end positions.
- Configuration backup/import and explainable diagnostics schema v4.
- Polish and English translations.

## Requirements

- Home Assistant `2026.7.0` or newer from the `2026.x` line.
- Python `3.14.2` or newer from the `3.14` line on the Home Assistant host.
- A physical `cover` entity supporting position or tilt-position commands.
- Correct Home Assistant location and time-zone configuration.

## Installation

### HACS

1. Add `https://github.com/rako79/adaptive-cover` as a custom integration
   repository in HACS.
2. Find and install **Adaptive Cover rako Edition**.
3. Restart Home Assistant.
4. Open **Settings -> Devices & services -> Add integration** and choose
   **Adaptive Cover rako Edition**.

> This fork keeps the `adaptive_cover` domain for compatibility with existing
> config entries. Do not install it alongside another Adaptive Cover variant;
> HACS should manage one copy of this integration.

### Manual

1. Copy `custom_components/adaptive_cover` to
   `/config/custom_components/adaptive_cover`.
2. Remove or move duplicate folders such as
   `/config/custom_components/adaptive_cover copy`.
3. Restart Home Assistant and add the integration from the UI.

Always perform a full Home Assistant restart after replacing integration files.

## Configuration

Each config entry represents one group of covers using the same geometry and
decision rules. A physical cover may belong to only one Adaptive Cover entry.
Duplicates are rejected during setup, import and runtime loading.

### Cover types

| Type | Use | Main geometry inputs |
| --- | --- | --- |
| Vertical cover | Up/down roller shutter | window height, required shaded distance, window depth and sill height |
| Horizontal awning | Extending awning | awning length and installation angle |
| Tilt cover | Venetian/slatted blind | slat distance, slat depth and rotation range |

### Solar geometry

- `set_azimuth` defines the window direction.
- `fov_left` and `fov_right` define the window field of view.
- Optional minimum and maximum elevation limit active sun angles.
- A blind spot can exclude a section obstructed by another building.
- Interpolation can assign custom positions to azimuth ranges.
- Geometry calculations are guarded against non-finite values, division by zero
  and extreme angles.

### Operating modes

**Basic mode** uses solar position, geometry, schedule, default position and
night position.

**Climate mode** additionally uses:

- indoor and outdoor temperature,
- `temp_low` and `temp_high` comfort thresholds,
- weather state and forecast temperature,
- occupancy,
- lux or irradiance with hysteresis,
- cold, rain and wind protection,
- night purge and dawn protection,
- Strict Sun Block,
- post-sun thermal hold.

## Decision priority

| Priority | Rule | Result |
| ---: | --- | --- |
| 110 | Control disabled | calculates the target but does not move the cover |
| 105 | Window open | applies the selected window policy |
| 100 | Rain / strong wind | uses the configured emergency position |
| 98 | Minimum / maximum position | applies physical position limits |
| 95 | Cold protection | closes the cover at night below the threshold |
| 90 | Dawn protection | limits early sunlight during selected months |
| 85 | Strict Sun Block | blocks strong direct sunlight in the window |
| 80 | Night purge | opens the cover to the purge position |
| 70 | Schedule / night-purge end | restores the configured night position |
| 60 | Thermal Hold | retains shading after recent direct sun |
| 50 | Night mode | uses the sunset position |
| 40 | Sun shadow | returns to the default position |
| 10 | Comfort automation | uses geometry and climate calculations |

Diagnostics expose a `decision_trace` containing active rules, the selected
rule and candidates overridden by higher priority.

## Climate functions

### Low radiation

In climate mode, the current lux or irradiance signal takes precedence over the
forecast alone. When `low_light=true` and `thermal_stress=0`, the integration
uses the default position even if the forecast classified the day as summer.
Positive thermal stress still retains protection, for example when outdoor air
is hotter than the room.

If a configured indoor-temperature sensor is unavailable, the integration does
not replace it with the outdoor temperature. Thermal protection remains
inactive until a reliable indoor reading returns, and diagnostics report
`temperature_source=inside_unavailable`.

### Night purge

Night purge operates between sunset and `night_purge_end_time` when the room is
above its comfort threshold and outdoor air is cooler than the room. At the
deadline, the integration applies the configured night position. A restart or
reload after the deadline but before the daily schedule starts immediately
catches up the missed close. Cold, rain and wind protection remain higher
priority. Cold protection uses a `1°C` hysteresis: once activated below the
configured threshold, it remains active until the outdoor temperature reaches
the threshold plus `1°C`.
An outdoor-temperature jump greater than `3°C` must persist for five minutes.
Shorter spikes are rejected before cold protection and night purge are
evaluated. Diagnostics expose the raw and accepted values, the pending
candidate and the rejected-reading count.

Starting purge requires a room temperature above `temp_low + 0.5°C` and outdoor
air cooler by more than `1°C`. Once started, purge continues until the room
reaches `temp_low` or the temperature difference falls to `0.2°C`.
A contact sensor is not required to start purge; configured open-window
policies still apply.

### Thermal Hold

`thermal_hold_after_sun` can activate only after actual direct sun on that
specific window. It is released when its configured duration expires, when
outdoor air is cooler by at least `thermal_hold_release_delta`, or when thermal
stress is no longer present.

### Rain and wind

- A physical rain sensor takes precedence over the weather forecast state.
- Wind values are normalized from `m/s`, `mph` or knots to `km/h`.
- Rain and wind can use separate emergency positions.
- `rain_night_only` limits rain protection to nighttime.
- Rain and wind bypass the schedule, manual override, cooldown and movement
  limits. The open-window policy still has the highest priority.

Strict Sun Block requires a current numeric irradiance or lux reading above its
activation threshold. `unknown`, `unavailable` and missing readings are not
treated as strong sunlight. During Home Assistant startup, the integration waits
for `async_at_started` and for entities to settle before it can send its first
command. The same lifecycle path is used when the integration is reloaded.

## Open-window policies

| Policy | Behavior |
| --- | --- |
| `pause` | pauses automatic movement |
| `move_to_position` | moves to `window_open_position` |
| `block_closing_only` | permits opening but blocks further closing |
| `return_after_close` | pauses and returns to the current target after closing |

## Manual override

The integration distinguishes its own service calls from user movement. A
manually adjusted cover remains outside automation for none, 15, 30, 60, 120
or 240 minutes, or until sunset. Intermediate `opening` and `closing` states can
be ignored. The reset button restores the current safe target and waits up to
120 seconds for completion.
Position reports received for two minutes after a command are attributed to the
integration's own movement. A duplicate final report is compared with the last
physical target instead of a newer automation calculation.

The override deadline is stored as one fixed timestamp. The “until sunset”
variant does not shrink on each refresh and selects the next sunset when the
current day's sunset has already passed.

## BehavioralLearner

Learning data is stored per config entry in Home Assistant Store. A verified
manual override updates:

- a position bias limited to `-25...+25` percentage points,
- a comfort-temperature offset limited to `-3...+3°C`,
- the override counter.

Learning is applied only during the active adaptive schedule and only to comfort
decisions. It cannot alter rain, wind, cold-protection or Strict Sun Block
targets. **Reset Behavioral Learning** clears all learned values for the entry.
The last direct-sun timestamp is persisted separately across Home Assistant
restarts, preserving Thermal Hold context.
The movement and schedule guard upgrade resets older learned offsets once
because they may have been created from intermediate motor reports or movement
outside the adaptive schedule. The direct-sun timestamp is retained.

## Schedule and time-source precedence

Start-time precedence is: configured start entity, workday/weekend time when a
Workday entity is configured, then universal `start_time`. An unavailable
Workday entity is not silently treated as a weekend.

End-time precedence is: configured end entity, explicit `end_time`, then sunset
plus `close_sunset_offset`. The sunset-offset number entity remains available
after switching the end-time source, but affects the schedule only for solar
closing. Earlier schedule changes and deadlines missed during a restart are
handled on the next refresh.

## Motor protection and retry

| Option | Default | Purpose |
| --- | ---: | --- |
| `delta_position` | `1%` | minimum difference required for movement |
| `delta_time` | `2 min` | minimum interval between automatic changes |
| `global_cooldown` | `5 min` | delay after any command for the same cover |
| `max_moves_per_hour` | `8` | hourly command limit; `0` disables it |
| `max_moves_per_day` | `40` | daily command limit; `0` disables it |

Commands receive generation numbers. A delayed retry rechecks the current
target, automation state, manual override, window policy and movement limits.
Stale tasks cannot move a cover after conditions change. Retry tasks are
background tasks, do not delay Home Assistant startup and are cancelled on
integration unload.

Conditions are reevaluated every minute, even without sensor changes. After a
movement block or manual override expires, automation resumes with the current
target. Motor verification runs after `45 s`, or immediately on a confirming
event; retries still respect movement limits. Identical pending commands are
coalesced. Command history includes the decision, trigger, readings, initial
position, target and command kind (`initial`, `retry`, `dry_run`). Diagnostics
export neither sends commands nor consumes pending execution events.

## Important defaults

| Option | Value |
| --- | ---: |
| Default position | `60%` |
| Sunset position | `0%` |
| Low / high comfort temperature | `21°C / 25°C` |
| Cold threshold | `16°C` |
| Strong-wind threshold | `40 km/h` |
| Night purge | enabled |
| Night purge end | `07:00` |
| Night purge position | `15%` |
| Thermal Hold | disabled |
| Thermal Hold position | `30%` |
| Thermal Hold duration | `120 min` |
| Thermal Hold release delta | `1°C` |
| Manual override duration | `15 min` |

## Entities

Every config entry creates:

- calculated-position sensor,
- solar start and end sensors,
- control-method sensor: `winter`, `intermediate` or `summer`,
- algorithm-status and decision-reason sensors,
- schedule sensor: `active`, `disabled` or `outside_schedule`,
- direct-sun and manual-override binary sensors,
- automation, manual detection and Dry Run switches,
- manual-override duration select,
- manual-override reset button,
- BehavioralLearner reset button,
- sunset-close offset number,
- opening-time entity, split into workday/weekend times when configured.

Climate mode may also create climate, temperature-source, lux, irradiance and
Strict Sun Block switches depending on configured inputs.

## Services

### Export configuration

```yaml
action: adaptive_cover.export_config
data:
  filename: adaptive_cover_settings.json
  include_date: true
```

The default result is a file such as
`12.07.2026_adaptive_cover_settings.json` in `/config`.

### Import configuration

```yaml
action: adaptive_cover.import_config
data:
  filename: 12.07.2026_adaptive_cover_settings.json
```

Import is validated transactionally and remains compatible with older files.
It updates existing entries matched by `entry_id` or title and does not create
missing config entries.

### Export diagnostics

```yaml
action: adaptive_cover.export_diagnostics
data:
  filename: adaptive_cover_diagnostics.json
  include_date: true
  refresh: true
```

Refresh is enabled by default, read-only, limited to 30 seconds and never issues
cover movement commands.

## Diagnostics schema v4

The service export and native Home Assistant diagnostics share one schema. It
contains:

- integration, Home Assistant and Python versions,
- time zone and loaded component path,
- config-entry version, state, source and validation,
- current decision and up to 50 recent decisions,
- `decision_trace` with evaluated priorities,
- current position, error, tolerance and `target_satisfied`,
- recent commands and their timestamps, service errors and movement history,
- retry task state and deadlines,
- coordinator health and refresh timing,
- schedule, forecast cache, `low_light`, seasonal mode, night-purge state and
  cold-protection thresholds,
- freshness of every related Home Assistant entity,
- BehavioralLearner load, save and override information.

Runtime histories are limited to 50 records and restart with Home Assistant.
Review paths, entity IDs and state context before sharing diagnostics publicly.

## Troubleshooting

1. Read the decision-reason sensor and `target_position`.
2. Check `control_toggle`, `manual_override`, `window_open` and `dry_run`.
3. Compare `current_position`, `position_error`, `effective_tolerance` and
   `target_satisfied`.
4. Inspect `last_skip_reason`, `last_service_error` and `verify_tasks`.
5. Confirm that only `/config/custom_components/adaptive_cover` is installed.
6. Export diagnostics with `refresh: true` and include current HA logs.

`position_delta_too_small` usually means the target is already satisfied within
the configured tolerance, not that automation failed.

## Architecture 1.6

Every refresh uses one execution path:

`event/timer -> input snapshot -> candidates -> arbiter -> limits and runtime policies -> movement.py -> cover service`

- `coordinator.py` composes dependencies, while `coordinator_pipeline.py`
  runs the short phases of one update cycle.
- `coordinator_events.py` owns refresh causes, entity events and timers.
- `coordinator_data.py` reads HA values once and builds the input snapshot.
- `geometry.py` computes solar geometry, while `climate.py` creates candidates
  without reading `hass.states` directly.
- `decision.py` owns priority arbitration, the decision trace and physical
  position constraints.
- `coordinator_execution.py` applies runtime policies.
- `movement.py` is the only gateway for `cover` service calls, verification and
  retries.
- `manual_control.py`, `learning.py`, `schedule.py`, `models.py` and
  `options.py` hold independent domain policies.

Refresh causes use a monotonic generation. When a newer event arrives while a
group is being controlled, remaining stale targets are skipped and the next
cycle evaluates the latest conditions. The night-purge deadline never sends a
position directly.

## Development and validation

```powershell
.\.venv\Scripts\ruff.exe check --no-cache custom_components\adaptive_cover tests
.\.venv\Scripts\ruff.exe format --check custom_components\adaptive_cover tests
.\.venv\Scripts\python.exe tests\run_pytest.py -q
.\.venv\Scripts\python.exe -m compileall -q custom_components\adaptive_cover tests
```

Blueprints under `custom_components/adaptive_cover/blueprints` are legacy tools
for additional covers only. Do not use them to control covers already assigned
directly to the integration.
