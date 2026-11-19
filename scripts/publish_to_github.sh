#!/usr/bin/env bash
# Publishes ReAqua to GitHub: placeholders, commit history, repository, collaborators, issues, project board.
# Usage (Git Bash on Windows, Linux, macOS):
#   OWNER=twoj-login scripts/publish_to_github.sh
#   OWNER=twoj-login COLLABORATORS="login2 login3 login4 loginProwadzacej" scripts/publish_to_github.sh
#   OWNER=twoj-login STEPS="issues project" ASSIGN=1 PEOPLE="Maciej Andrzejewski=login1;Weronika Zator=login2;Kacper Mikołajczyk=login3;Tomasz Szulski=login4" scripts/publish_to_github.sh
# Variables: OWNER (required), REPO, VISIBILITY, CONTACT_EMAIL, COLLABORATORS, STEPS, ASSIGN, PEOPLE, DRY_RUN.
set -euo pipefail

OWNER="${OWNER:?Ustaw OWNER na swoj login lub nazwe organizacji GitHub}"
REPO="${REPO:-ReAqua}"
VISIBILITY="${VISIBILITY:-public}"
CONTACT_EMAIL="${CONTACT_EMAIL:-}"
COLLABORATORS="${COLLABORATORS:-}"
STEPS="${STEPS:-repo collab}"
ASSIGN="${ASSIGN:-0}"
PEOPLE="${PEOPLE:-}"
DRY_RUN="${DRY_RUN:-0}"
DESCRIPTION="Mała retencja przeciw suszy: wtyczka QGIS, CLI i panel WWW"

cd "$(dirname "$0")/.."

run() {
  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

has_step() {
  case " $STEPS " in *" $1 "*) return 0 ;; *) return 1 ;; esac
}

require() {
  command -v "$1" >/dev/null 2>&1 || { echo "Brak programu: $1"; exit 1; }
}

require git
if [ "$DRY_RUN" != "1" ]; then
  require gh
  gh auth status >/dev/null 2>&1 || { echo "Zaloguj sie do GitHuba: gh auth login"; exit 1; }
fi
if [ -z "$(git config user.name || true)" ] || [ -z "$(git config user.email || true)" ]; then
  echo "Ustaw dane autora: git config --global user.name \"Imie Nazwisko\" i user.email"
  exit 1
fi

replace_placeholders() {
  sed -i.bak "s/ZASTAP-ORGANIZACJA/${OWNER}/g" README.md src/reaqua/metadata.txt
  if [ -n "$CONTACT_EMAIL" ]; then
    sed -i.bak "s/reaqua@example.com/${CONTACT_EMAIL}/g" src/reaqua/metadata.txt
  fi
  rm -f README.md.bak src/reaqua/metadata.txt.bak
}

commit() {
  local message="$1"
  shift
  git add "$@"
  git commit -q -m "$message"
  echo "commit: $message"
}

make_history() {
  if git rev-parse --verify HEAD >/dev/null 2>&1; then
    echo "Repozytorium ma juz commity, pomijam tworzenie historii."
    return
  fi
  git init -q
  git symbolic-ref HEAD refs/heads/main
  commit "Add project configuration, license and pinned dependencies" .gitignore LICENSE AUTHORS .flake8 requirements.txt requirements-dev.txt pyproject.toml
  commit "Add raster I/O and NDVI/NDMI drought classification with reflectance scaling" src/reaqua/__init__.py src/reaqua/core/__init__.py src/reaqua/core/models.py src/reaqua/core/params.py src/reaqua/core/physics.py src/reaqua/core/io.py src/reaqua/core/spectral.py
  commit "Add reservoir siting with zone quotas, minimum distance and sample data" src/reaqua/core/scout.py src/reaqua/core/synthetic.py scripts/make_sample_data.py data
  commit "Add anisotropic simple and ordinary kriging of reservoir influence" src/reaqua/core/kriging.py
  commit "Add regional water balance, indices, scenarios, costs and HTML report" src/reaqua/core/costs.py src/reaqua/core/hydrology.py src/reaqua/core/report.py src/reaqua/core/charts.py src/reaqua/core/schema.py src/reaqua/core/pipeline.py
  commit "Add GeoPackage writer for runs, reservoirs and metrics" src/reaqua/db
  commit "Add command line interface and file-based scene queue" src/reaqua/__main__.py src/reaqua/cli.py src/reaqua/inbox.py
  commit "Add Flask dashboard, REST API and scene upload" src/reaqua/web
  commit "Add QGIS plugin with layer context menu and background tasks" src/reaqua/gui src/reaqua/metadata.txt src/reaqua/icon.png scripts/make_icon.py scripts/build_plugin.py
  commit "Add pytest suite for core, database, web and plugin registration" tests
  commit "Add Dockerfile and docker-compose with seed, worker and web services" Dockerfile docker-compose.yml .dockerignore
  commit "Add GitHub Actions workflow running flake8, pytest and Docker build" .github
  commit "Add README and project documentation" README.md docs scripts/publish_to_github.sh
  if [ -n "$(git status --porcelain)" ]; then
    echo "Uwaga: sa pliki niedodane do commitow:"
    git status --short
  fi
}

create_repository() {
  run gh repo create "${OWNER}/${REPO}" "--${VISIBILITY}" --description "$DESCRIPTION" --source=. --remote=origin --push
}

invite_collaborators() {
  if [ -z "$COLLABORATORS" ]; then
    echo "Brak COLLABORATORS, pomijam zaproszenia."
    return
  fi
  for login in $COLLABORATORS; do
    run gh api -X PUT "repos/${OWNER}/${REPO}/collaborators/${login}" -f permission=push --silent
    echo "zaproszono: ${login} (musi zaakceptowac zaproszenie)"
  done
}

login_for() {
  local person="$1" pair
  IFS=';' read -ra pairs <<< "$PEOPLE"
  for pair in "${pairs[@]}"; do
    if [ "${pair%%=*}" = "$person" ]; then
      echo "${pair#*=}"
      return
    fi
  done
}

create_issues() {
  local id title section person status due note body login url args
  while IFS=$'\t' read -r id title section person status due note; do
    [ "$id" = "id" ] && continue
    body=$(printf 'Punkt checklisty: %s\nWykonawca (propozycja): %s\nTermin: %s\nUwagi: %s' "$section" "$person" "$due" "$note")
    args=(--repo "${OWNER}/${REPO}" --title "${id}: ${title}" --body "$body")
    login=""
    if [ "$ASSIGN" = "1" ]; then
      login=$(login_for "$person")
      [ -n "$login" ] && args+=(--assignee "$login")
    fi
    if [ "$DRY_RUN" = "1" ]; then
      echo "[dry-run] gh issue create ${args[*]}"
      url="https://github.com/${OWNER}/${REPO}/issues/dry-${id}"
    else
      url=$(gh issue create "${args[@]}")
    fi
    echo "zgloszenie: ${id} (${status})"
    if [ "$status" = "Done" ]; then
      run gh issue close "$url" --reason completed
    fi
  done < docs/zadania.tsv
}

create_project() {
  local number url
  if [ "$DRY_RUN" = "1" ]; then
    echo "[dry-run] gh project create --owner ${OWNER} --title '${REPO} - zadania'"
    return
  fi
  number=$(gh project create --owner "$OWNER" --title "${REPO} - zadania" --format json --jq '.number') || {
    echo "Nie udalo sie utworzyc projektu. Nadaj uprawnienie: gh auth refresh -s project, albo utworz tablice recznie (krok 8 instrukcji)."
    return
  }
  gh project link "$number" --owner "$OWNER" --repo "${OWNER}/${REPO}" || true
  for url in $(gh issue list --repo "${OWNER}/${REPO}" --state all --limit 200 --json url --jq '.[].url'); do
    gh project item-add "$number" --owner "$OWNER" --url "$url" >/dev/null
  done
  echo "Projekt nr ${number} utworzony. Sprawdz kolumny Todo, In Progress, Done i przypisania w zakladce Projects."
}

if has_step repo; then
  replace_placeholders
  make_history
  create_repository
fi
if has_step collab; then
  invite_collaborators
fi
if has_step issues; then
  create_issues
fi
if has_step project; then
  create_project
fi
echo "Gotowe. Repozytorium: https://github.com/${OWNER}/${REPO}"
