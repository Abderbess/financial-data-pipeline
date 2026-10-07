# Pipeline de transactions

Des fichiers CSV de transactions sont générés, validés, agrégés puis insérés dans une base SQLite.
Seuls `pytest` et `mypy` sont installés, tout le reste vient de la bibliothèque standard.

## Installation

```powershell
git clone https://github.com/Abderbess/financial-data-pipeline.git
cd financial-data-pipeline
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

(Linux / macOS : `source .venv/bin/activate`.)

## Commandes

```powershell
$env:PYTHONPATH = "src"        # Linux / macOS : export PYTHONPATH=src
python -m txpipe               # génère les CSV, les traite, crée pipeline.db
python -m txpipe --skip-generate   # retraite les CSV déjà dans data/ sans en générer
pytest
mypy src/ tests/
```

Code de retour : 0 si tout va bien, 1 si au moins un fichier échoue, 2 s'il n'y a aucun CSV.
Les exercices sqlite3 sont dans `preambule/`.

## Base de données

```
fichiers      (id, nom, sha256 UNIQUE, nb_transactions, traite_le)
transactions  (id, fichier_id -> fichiers, datetime_transaction, iban_origine, pays_source,
               banque_source, iban_destinataire, pays_destinataire, montant_centimes,
               devise, depasse_seuil)
agregats      (fichier_id -> fichiers, type, cle, total_centimes)
```

Les montants sont des `Decimal` dans le code et des centimes entiers en base, jamais des `float`.
`depasse_seuil` vaut 1 si le montant est strictement supérieur à 5000.

## Lignes invalides

Rejet global : si une seule ligne d'un fichier est invalide (montant non numérique, `NaN`, négatif,
plus de 2 décimales, date illisible, colonne manquante...), tout le fichier est refusé, rien n'est
inséré et la pipeline renvoie un code non nul. Je l'ai choisi parce qu'un fichier chargé à moitié
donnerait des totaux faux sans que personne s'en aperçoive.

## Idempotence

Chaque fichier est identifié par le SHA-256 de son contenu (colonne `sha256`, `UNIQUE`), pas par
son nom. Un contenu déjà vu est ignoré même sous un autre nom, et un nom déjà vu avec un contenu
différent est traité. La vérification et l'insertion se font dans la même transaction.

## Étape 6 : échec de la pipeline

Avec un fichier `transactions_04.csv` dont une ligne a le montant `abc` :

```
> python -m txpipe --skip-generate
[SKIP] transactions_01.csv : déjà traité (sha256=1c9a325e6dff...)
[SKIP] transactions_02.csv : déjà traité (sha256=7feb1ddbfa3d...)
[SKIP] transactions_03.csv : déjà traité (sha256=d7b0e319b580...)
[FAIL] transactions_04.csv : fichier invalide: ligne 3: montant non numérique: 'abc'
Résumé : 0 inséré(s), 3 ignoré(s), 1 en échec -> code de retour 1
```

La base ne contient que les trois fichiers valides : même la première ligne, correcte, du fichier
en échec n'a pas été insérée (testé dans `tests/test_failure.py`, aussi en cas de panne au milieu
de l'insertion, grâce au `ROLLBACK`).

Erreur vue par mypy mais pas par pytest : une fonction qui annonce `-> str` mais renvoie `None`
quand le dictionnaire est vide. Le test ne regardait que le cas rempli, donc il passait :

```
> pytest
28 passed
> mypy src/ tests/
src\txpipe\demo_mypy.py:7: error: Incompatible return value type (got "None", expected "str")  [return-value]
```

Ce que j'en retiens : un test ne vérifie que les cas auxquels j'ai pensé, alors que mypy lit
le code sans l'exécuter et regarde tous les chemins. À l'inverse, mypy ne sait pas que le seuil doit
être `>` et non `>=`, seuls les tests le vérifient. Les deux se complètent. (J'ai retiré ce code après l'essai.)

## Étape 7 : retry

On réessaie seulement si l'erreur peut disparaître toute seule :

- `OperationalError` « database is locked » : oui, un autre programme finira par libérer la base.
- `IntegrityError` (UNIQUE, NOT NULL, FOREIGN KEY...) : non, avec les mêmes données l'erreur reviendra à
  chaque fois, il faut corriger la donnée.
- `OperationalError` « no such table » : non, même type d'exception mais erreur permanente. Je regarde
  donc aussi le message, pas seulement le type.

`retry` rappelle l'insertion jusqu'à 3 fois en doublant l'attente. C'est sans risque parce que
l'insertion est atomique et qu'un fichier déjà inséré est ignoré. Testé dans `tests/test_retry.py` et
`tests/test_retry_pipeline.py` (dont un vrai verrou SQLite).
