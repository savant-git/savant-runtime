#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
ONTOLOGY="$ROOT/ontology"
EXILES="$ONTOLOGY/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
REPORT_DIR="$ROOT/audit/scope_tree"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
REPORT="$REPORT_DIR/dry_run_scope_tree_audit_$STAMP.tsv"

mkdir -p "$REPORT_DIR"

classify_scope() {
    local path="$1"
    local base
    base="$(basename "$path")"

    case "$path" in
        "$ROOT"/*.sh)
            case "$base" in
                *EXILE*|*EXILES*|*18_EXILES*)
                    echo "$EXILES/segue/authority_db/seeds/$base"
                    ;;
                *FILAMENT*|*PROJECTION_ENGINE*)
                    echo "$EXILES/filament/segue/projection_engine/scripts/$base"
                    ;;
                *PALAVER*)
                    echo "$EXILES/palaver/segue/scripts/$base"
                    ;;
                *)
                    echo "$ROOT/ops/uncategorized/scripts/$base"
                    ;;
            esac
            ;;

        "$ONTOLOGY"/segue/*)
            echo "${path/$ONTOLOGY\/segue/$ONTOLOGY\/obelisks\/segue}"
            ;;

        "$ONTOLOGY"/authority_graph/*)
            echo "${path/$ONTOLOGY\/authority_graph/$ONTOLOGY\/obelisks\/segue\/authority_graph}"
            ;;

        "$ONTOLOGY"/authority_db/*)
            echo "${path/$ONTOLOGY\/authority_db/$ONTOLOGY\/obelisks\/segue\/authority_db}"
            ;;

        "$ONTOLOGY"/indexes/*)
            echo "${path/$ONTOLOGY\/indexes/$ONTOLOGY\/obelisks\/segue\/indexes}"
            ;;

        "$EXILES"/projection/*)
            echo "${path/$EXILES\/projection/$EXILES\/filament\/segue\/projection_references}"
            ;;

        "$EXILES"/runtime/*)
            echo "${path/$EXILES\/runtime/$EXILES\/segue\/runtime}"
            ;;

        *)
            echo ""
            ;;
    esac
}

is_known_generated_or_vendor() {
    local path="$1"

    case "$path" in
        */node_modules/*|*/.venv/*|*/__pycache__/*|*/.git/*|*/dist/*|*/build/*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

printf "status\tclassification\tsource\tproposed_target\n" > "$REPORT"

find "$ROOT" -mindepth 1 \( -type f -o -type d \) | sort |
while IFS= read -r path
do
    if is_known_generated_or_vendor "$path"; then
        continue
    fi

    target="$(classify_scope "$path")"

    if [ -z "$target" ]; then
        continue
    fi

    if [ "$path" = "$target" ]; then
        printf "OK\talready_correct\t%s\t%s\n" "$path" "$target" >> "$REPORT"
    elif [ -e "$target" ]; then
        printf "CONFLICT\ttarget_exists\t%s\t%s\n" "$path" "$target" >> "$REPORT"
    else
        printf "MOVE\tproposed\t%s\t%s\n" "$path" "$target" >> "$REPORT"
    fi
done

echo
echo "[DRY RUN COMPLETE]"
echo "$REPORT"

echo
echo "=== SUMMARY ==="
cut -f1 "$REPORT" | tail -n +2 | sort | uniq -c

echo
echo "=== PROPOSED MOVES ==="
awk -F '\t' '$1=="MOVE"{print $3 " -> " $4}' "$REPORT" | head -80

echo
echo
echo "No files were moved."
