# Pipeline de transactions

Mini projet de remise à niveau Python. Des fichiers CSV de transactions sont générés, lus, validés,
agrégés, puis rangés dans une base SQLite. Tout est fait avec la bibliothèque standard, sauf `pytest`
et `mypy` (tests et typage).

## Installation

Il faut Python 3.11 ou plus.

```powershell
git clone https://github.com/Abderbess/financial-data-pipeline.git
cd financial-data-pipeline
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Sous Linux ou macOS, l'activation se fait avec `source .venv/bin/activate`.

## Commandes

Le code est dans `src/`, il faut donc le dire à Python avant de lancer la pipeline :

```powershell
$env:PYTHONPATH = "src"   
python -m txpipe
```

Cette commande génère les CSV dans `data/`, les traite, crée `pipeline.db` et y insère les données.
Pour retraiter les fichiers déjà présents dans `data/` sans en regénérer, on ajoute
`--skip-generate` (ça ne marche donc qu'après une première génération). Les autres options sont
`--data-dir`, `--db`, `--files` et `--seed`.

Le code de retour vaut 0 si tout s'est bien passé (les fichiers déjà traités comptent comme OK),
1 si au moins un fichier a échoué, et 2 s'il n'y a aucun CSV à traiter.

Tests et typage :

```powershell
pytest
mypy src/ tests/
```

Les exercices sur sqlite3 du préambule sont dans le dossier `preambule/`.

## Organisation du code

- `models.py` : le type `Transaction` (un `TypedDict`) et les résultats du traitement
- `generate.py` : génération des CSV, avec une graine fixe pour avoir toujours les mêmes données
- `loader.py` : lecture et validation des lignes, empreinte SHA-256 d'un fichier
- `processing.py` : les calculs, écrits comme des fonctions pures (pas de fichier, pas de `print`,
  les arguments ne sont pas modifiés)
- `db.py` : le schéma SQLite et l'insertion d'un fichier
- `retry.py` : le retry des erreurs temporaires
- `pipeline.py` : l'assemblage de tout ça et la ligne de commande

Les montants sont des `Decimal` dans le code et des entiers en centimes dans la base. Je n'utilise
jamais de `float`, parce que `0.1 + 0.2` donne `0.30000000000000004`.

## Schéma de la base

```
fichiers      (id, nom, sha256 UNIQUE, nb_transactions, traite_le)
transactions  (id, fichier_id -> fichiers, datetime_transaction, iban_origine, pays_source,
               banque_source, iban_destinataire, pays_destinataire,
               montant_centimes, devise, depasse_seuil)
agregats      (fichier_id -> fichiers, type, cle, total_centimes)
              type vaut envoye_par_iban, envoye_par_banque ou recu_par_iban
```

`depasse_seuil` vaut 1 quand le montant est strictement supérieur à 5000. Les clés étrangères sont
activées à chaque connexion avec `PRAGMA foreign_keys = ON`, car SQLite ne les vérifie pas par défaut.
Les agrégats sont enregistrés fichier par fichier ; pour avoir le total sur tous les fichiers, on
fait un `SUM(total_centimes)` avec un `GROUP BY cle`.

## Lignes invalides

J'ai choisi le rejet global : si une seule ligne d'un fichier est invalide, tout le fichier est refusé
et rien n'est inséré. Le fichier est affiché en `FAIL` et la pipeline renvoie un code non nul. Toutes les
erreurs du fichier sont listées avec leur numéro de ligne, pour pouvoir tout corriger en une fois.

J'ai pris cette stratégie parce qu'avec des données financières, un fichier chargé à moitié donnerait
des totaux faux sans que personne ne le remarque. Elle va aussi bien avec le principe « un fichier
est inséré en entier ou pas du tout », et avec l'idempotence : une fois corrigé, le fichier a un autre
contenu donc une autre empreinte, il sera traité normalement.

Une ligne est invalide si le montant n'est pas un nombre, s'il vaut `NaN` ou `Infinity` (`Decimal`
les accepte), s'il est nul ou négatif, s'il a plus de deux décimales, si la date est illisible, si
le nombre de colonnes est faux ou si l'en-tête est incomplet. Un fichier vide est aussi refusé.
Tout est testé dans `tests/test_loader.py`.

## Idempotence

Un fichier est identifié par le SHA-256 de son contenu, stocké dans `fichiers.sha256` (colonne
`UNIQUE`). Le nom n'a donc pas d'importance :

- même nom mais contenu différent : l'empreinte change, le fichier est traité
- même contenu sous deux noms : l'empreinte est la même, le deuxième est ignoré (`SKIP`)
- relance de la pipeline : les fichiers déjà insérés sont ignorés

Le test « ce fichier est-il déjà traité ? » et l'insertion se font dans la même transaction
(`BEGIN IMMEDIATE`), pour qu'un autre processus ne puisse pas insérer le même fichier entre les deux.
Ces cas sont dans `tests/test_integration.py`.

## Étape 6 : quand ça échoue

J'ai ajouté dans `data/` un fichier `transactions_04.csv` dont la deuxième ligne a le montant `abc`,
puis relancé la pipeline :

```
> python -m txpipe --skip-generate
[SKIP] transactions_01.csv : déjà traité (sha256=1c9a325e6dff...)
[SKIP] transactions_02.csv : déjà traité (sha256=7feb1ddbfa3d...)
[SKIP] transactions_03.csv : déjà traité (sha256=d7b0e319b580...)
[FAIL] transactions_04.csv : fichier invalide: ligne 3: montant non numérique: 'abc'
Résumé : 0 inséré(s), 3 ignoré(s), 1 en échec -> code de retour 1
> echo $LASTEXITCODE
1
```

La base ne contient que les trois fichiers valides. La première ligne de `transactions_04.csv`,
pourtant correcte, n'a pas été insérée : il n'y a pas d'insertion partielle. Les tests de
`tests/test_failure.py` le vérifient, y compris quand la panne arrive au milieu de l'insertion
(après l'écriture des transactions et avant celle des agrégats) : le `ROLLBACK` annule tout.

### Une erreur vue par mypy mais pas par les tests

```python
def largest_sender(totals: dict[str, Decimal]) -> str:
    if not totals:
        return None
    return max(totals, key=lambda iban: totals[iban])
```

Mon test ne vérifie que le cas où le dictionnaire est rempli :

```
> pytest
28 passed in 0.34s

> mypy src/ tests/
src\txpipe\demo_mypy.py:7: error: Incompatible return value type (got "None", expected "str")  [return-value]
Found 1 error in 1 file (checked 14 source files)
```

J'ai retiré ce code du dépôt après l'essai.

Ce que j'en retiens : un test ne vérifie que ce que j'ai pensé à tester. Ici, le cas du dictionnaire
vide n'est jamais exécuté, donc le test passe. mypy lit le code sans le lancer et regarde tous les
chemins possibles : il voit que la fonction annonce un `str` et peut renvoyer `None`. En revanche, mypy
ne peut pas savoir que j'aurais dû écrire `>` plutôt que `>=` pour le seuil de 5000, c'est un choix
métier que seuls les tests vérifient (`test_threshold_is_strict`). Les deux outils se complètent :
mypy surveille les types sur tout le code, les tests surveillent les valeurs.

## Étape 7 : retry

Je réessaie seulement quand l'erreur peut disparaître toute seule si on attend un peu.

- `OperationalError` « database is locked » : oui. Un autre programme écrit dans la base, il finira
  par libérer le verrou.
- `IntegrityError` (UNIQUE, NOT NULL, CHECK, FOREIGN KEY) : non. Avec les mêmes données, l'erreur sera
  la même à chaque essai. Il faut corriger la donnée ou le code.
- `OperationalError` « no such table » : non, même si c'est le même type d'exception. L'erreur est permanente.

Comme `OperationalError` mélange des erreurs temporaires et permanentes, le type seul ne suffit pas :
`is_retryable` regarde aussi le message (`locked` ou `busy`).

`retry(func, attempts=3, base_delay=0.1)` rappelle la fonction seulement si l'erreur est réessayable,
en doublant l'attente à chaque fois (0,1 s puis 0,2 s...). Au dernier échec, l'erreur est relancée telle
quelle. Je peux réessayer sans risque parce que `insert_file` est atomique (tout est annulé si ça
plante) et idempotente (un fichier déjà inséré est ignoré) : un nouvel essai ne peut ni dupliquer des
lignes ni laisser un état à moitié écrit.

Les tests sont dans `tests/test_retry.py` (classement des erreurs, succès après deux erreurs, abandon,
aucun retry sur `IntegrityError`) et `tests/test_retry_pipeline.py` (une erreur de verrou simulée suivie
d'une réinsertion réussie, et un vrai verrou SQLite tenu par une deuxième connexion).

## Ce qui manque

Je n'ai pas fait les bonus (PostgreSQL, CI GitHub Actions, S3, logging, ruff). Je ne gère pas non plus
le multi-devises : les agrégats ne sont pas indexés par `(iban, devise)`.