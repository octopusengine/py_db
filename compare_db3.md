# pyDb Emulator vs. dBASE III PLUS

Tento dokument srovnává pyDb Emulator s dBASE III PLUS, často zapisovaným jako
dBASE III+. Popis odpovídá verzi pyDb **0.3.1**.

pyDb není emulátor formátu DBF ani úplná implementace jazyka dBASE. Je to malý
interaktivní shell inspirovaný stylem dBASE III+, který ukládá data do SQLite.

## Základní rozdíl v architektuře

| Téma | dBASE III PLUS | pyDb Emulator |
| --- | --- | --- |
| Uložení dat | Tabulky v souborech DBF | Tabulky uvnitř jednoho SQLite souboru |
| Databázový soubor | Tabulka je typicky samostatný datový soubor | Jeden soubor může obsahovat mnoho tabulek |
| Schéma | DBF hlavička a typy pole | SQLite schéma, například TEXT, INTEGER, REAL |
| Dotazování | Příkazy a výrazový jazyk dBASE | Jednoduché příkazy plus SQLite přes SQL |
| Skripty | Programové soubory a jazyk dBASE | Lineární textové skripty DBS |
| Kompatibilita souborů | Práce s DBF | Bez přímého čtení a zápisu DBF |

Přípona určená přes volbu --name neurčuje datový formát. Například soubor
projects.b je stále SQLite databáze, nikoli soubor DBF.

## Co jsme zachovali z dBASE stylu

### Interaktivní práce v promptu

Emulátor se spustí do promptu pyDb>, kde příkazy zadáváme postupně:

~~~
pyDb> CREATE customers (id INTEGER PRIMARY KEY, name TEXT)
pyDb> USE customers
pyDb> INSERT (name) VALUES ('Alice')
pyDb> LIST
~~~

### Krátké příkazy a aliasy

| Krátký tvar | Plný tvar |
| --- | --- |
| CREA | CREATE |
| INSE | INSERT |
| SELE | SELECT |
| DELE | DELETE |
| STRU | STRUCT |
| MODI | MODIF |
| EXPO | EXPORT |

Zachován je koncept aktivní tabulky. Po USE customers pracují LIST, INSERT,
DELETE, STRUCT, MODIF a EXPORT s tabulkou customers.

### Podporované příkazy

| Příkaz | Současné chování |
| --- | --- |
| CREATE nebo CREA | Vytvoří SQLite tabulku a nastaví ji jako aktivní. |
| USE | Vybere existující aktivní tabulku. |
| SHOW | Vypíše tabulky v otevřené databázi. |
| LIST se sloupci | Vypíše řádky, případně jen vybrané sloupce. |
| STRUCT | Vypíše sloupce, SQLite typy a primární klíč. |
| INSERT nebo INSE | Vloží řádek do aktivní tabulky. |
| DELETE nebo DELE | Maže řádky podle podmínky WHERE. |
| DROP | Po potvrzení odstraní tabulku. |
| MODIF ADD | Přidá sloupec. |
| MODIF DROP | Odstraní sloupec přestavbou tabulky. |
| RUN | Spustí textový skript DBS. |
| EXPORT | Zapíše aktivní tabulku jako CSV, JSON nebo XML. |
| SQL | Provede vlastní SQLite dotaz. |

SELECT je v současné verzi praktický alias pro LIST. Není to plná implementace
dBASE SELECT ani SQL SELECT se všemi klauzulemi. Vlastní SQLite dotaz patří do
příkazu SQL.

### JSON definice tabulky

Volby -c, --crea a --create vytvoří tabulku z JSON souboru v datové složce.
Položka table určuje název tabulky a columns[].field určuje sloupce:

~~~
{
  "table": "tasks",
  "columns": [
    {"field": "uid"},
    {"field": "project"},
    {"field": "prompt"}
  ]
}
~~~

Pole uid vznikne jako INTEGER PRIMARY KEY, ostatní pole jako TEXT. Tento JSON
formát je vlastní pyDb, nikoli formát DBF.

## Co chybí nebo je jinak

### Formáty a typy

- PyDb neotevírá, nevytváří ani neexportuje soubory DBF.
- Nepracuje s klasickými DBF typy Character, Numeric, Date, Logical a Memo.
- Hodnota None ve výpisu je SQLite NULL, ne dBASE prázdná hodnota.
- JSON položka width se zatím nepoužívá pro schéma ani formátování výpisu.

### Databázové chování

- SQLite soubor může obsahovat více tabulek. DBASE pracoval především s
  jednotlivými DBF tabulkami a pracovními oblastmi.
- Neexistují více work areas, aliasy tabulek ani více současně otevřených
  databází v jednom promptu.
- Nejsou indexové soubory NDX, SET ORDER, SEEK, LOCATE, GO TOP, SKIP ani EOF().
- DELETE v pyDb řádky skutečně smaže; neexistuje příznak smazání a následný
  příkaz PACK.
- MODIF DROP zachová zbývající data, ale při přestavbě nepřenáší všechny
  pokročilé SQLite vlastnosti, například indexy, triggery a omezení.

### Příkazový jazyk a rozhraní

- Nejsou implementovány APPEND, BROWSE, EDIT, REPLACE, FIND, COUNT, SUM,
  AVERAGE, COPY, JOIN ani REPORT FORM.
- DBS je lineární seznam příkazů. Není to jazyk PRG: nemá proměnné, procedury,
  funkce, makra, IF, DO WHILE ani ošetření chyb.
- SQL používá SQLite syntaxi, funkce a typové chování.
- Není zde celoobrazovkový BROWSE ani formulářový editor.
- Barvy jsou dostupné pouze v ANSI terminálu; při přesměrovaném výstupu nebo s
  proměnnou NO_COLOR zůstává výpis bez barev.

## Náměty pro TODO

Tyto body nejsou závazný plán. Jsou kandidáty podle toho, zda má pyDb směřovat
více k dBASE kompatibilitě, nebo k pohodlnému SQLite nástroji.

### Praktická práce s daty

- [ ] Přidat LIST WHERE, LIST ORDER BY, LIMIT a stránkování.
- [ ] Přidat FIND nebo LOCATE nad aktivní tabulkou.
- [ ] Přidat UPDATE nebo dBASE-style REPLACE.
- [ ] Přidat import CSV a JSON, nejen export.
- [ ] Pro hodnoty z promptu doplnit bezpečné parametrizované vkládání.
- [ ] Nastavitelně zobrazovat SQLite NULL místo Python hodnoty None.

### Lepší schéma

- [ ] Rozšířit JSON o typ, NOT NULL, výchozí hodnotu, UNIQUE, cizí klíč a popis.
- [ ] Použít JSON width při LIST a STRUCT.
- [ ] Přidat CREATE INDEX a SHOW INDEXES.
- [ ] MODIF DROP změnit na migraci, která zachová indexy, triggery a omezení.
- [ ] Přidat DESCRIBE pro tabulku bez změny aktivní tabulky.

### dBASE-style kompatibilita

- [ ] Rozhodnout, zda přidat volitelný import a export DBF.
- [ ] Navrhnout omezenou podporu APPEND, REPLACE, BROWSE a LOCATE.
- [ ] Přidat pracovní oblasti nebo pojmenované aliasy tabulek.
- [ ] Vyjasnit rozsah skriptů: jednoduché DBS, nebo malý jazyk s podmínkami.

### Provoz a kvalita

- [ ] Přidat automatické testy příkazů, chybných vstupů a JSON definic.
- [ ] Doplnit návratové kódy CLI a strojově čitelný výstup pro --list.
- [ ] Přidat --no-debug nebo přesunout debug výpisy pod vlastní přepínač.
- [ ] Zobrazit volitelný stavový řádek s verzí, databází a aktivní tabulkou.
- [ ] Před DROP a MODIF DROP nabídnout zálohu databáze.

## Doporučený směr

Nejpřirozenější je držet pyDb jako malý nástroj inspirovaný dBASE nad SQLite:
krátké příkazy, aktivní tabulka a přímočarý prompt, ale nové funkce navrhované
s ohledem na SQLite schéma a transakce. Přímou DBF kompatibilitu má smysl
přidávat až při konkrétní potřebě číst nebo migrovat historická data.
