#!/usr/bin/env bash
set -euo pipefail

cd /root/savant-runtime

ROOT="/root/savant-runtime"
ONTOLOGY="$ROOT/ontology"
OBELISKS="$ONTOLOGY/obelisks"
EXILES="$OBELISKS/_template/segue/gates/_template/segue/innates/_template/segue/exiles"

AUDIT="$ROOT/audit/scope_tree"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$AUDIT/classified_scope_objects_$STAMP.tsv"

mkdir -p "$AUDIT"

hash_id() {
    printf '%s' "$1" | sha256sum | awk '{print $1}'
}

file_kind() {
    local p="$1"

    if [ -d "$p" ]; then
        echo "directory"
    elif [ -f "$p" ]; then
        echo "file"
    elif [ -L "$p" ]; then
        echo "symlink"
    else
        echo "unknown"
    fi
}

extension_of() {
    local base
    base="$(basename "$1")"

    case "$base" in
        *.*)
            echo "${base##*.}"
            ;;
        *)
            echo ""
            ;;
    esac
}

is_generated_or_vendor() {
    local p="$1"

    case "$p" in
        */node_modules/*|*/.venv/*|*/__pycache__/*|*/.git/*|*/dist/*|*/build/*|*/.cache/*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

detect_owner() {
    local p="$1"
    local b
    b="$(basename "$p" | tr '[:upper:]' '[:lower:]')"

    for exile in \
        carbon cataxis coda envoy filament graffiti lore mobius modus niche \
        notary opus pact palaver shatter underscore urge zero
    do
        case "$p" in
            *"/exiles/$exile/"*|*"/exiles/$exile"|*"${exile}"*)
                echo "$exile"
                return
                ;;
        esac

        case "$b" in
            *"$exile"*)
                echo "$exile"
                return
                ;;
        esac
    done

    echo "unknown"
}

detect_scope() {
    local p="$1"
    local b
    b="$(basename "$p" | tr '[:upper:]' '[:lower:]')"

    case "$p" in
        "$ROOT"/*.sh)
            case "$b" in
                *18*exile*|*exiles*|*exile*)
                    echo "all_exiles"
                    ;;
                *ontology*)
                    echo "entire_ontology"
                    ;;
                *runtime*|*savant*)
                    echo "entire_runtime"
                    ;;
                *)
                    echo "unknown"
                    ;;
            esac
            return
            ;;
    esac

    case "$p" in
        "$ONTOLOGY"/segue/*|"$ONTOLOGY"/authority_graph/*|"$ONTOLOGY"/authority_db/*|"$ONTOLOGY"/indexes/*)
            echo "all_obelisks"
            return
            ;;
        "$EXILES"/segue/*)
            echo "all_exiles"
            return
            ;;
        "$EXILES"/*/segue/*)
            echo "single_exile"
            return
            ;;
        "$EXILES"/*)
            echo "single_exile"
            return
            ;;
    esac

    echo "unknown"
}

detect_level() {
    local scope="$1"

    case "$scope" in
        entire_runtime)
            echo "runtime"
            ;;
        entire_ontology)
            echo "ontology"
            ;;
        all_obelisks)
            echo "obelisks.segue"
            ;;
        all_exiles)
            echo "exiles.segue"
            ;;
        single_exile)
            echo "exile"
            ;;
        single_prodigal)
            echo "prodigal"
            ;;
        single_quirk)
            echo "quirk"
            ;;
        single_mote)
            echo "mote"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

detect_authority_type() {
    local p="$1"
    local b
    b="$(basename "$p" | tr '[:upper:]' '[:lower:]')"

    case "$p" in
        */projections/*|*/reports/*|*/audit/*)
            echo "generated"
            return
            ;;
    esac

    case "$b" in
        *.sh)
            echo "operational_mote"
            ;;
        *.json|*.md|*.sql)
            echo "authority_or_projection"
            ;;
        *.py)
            echo "runtime_implementation"
            ;;
        *)
            echo "unknown"
            ;;
    esac
}

propose_target() {
    local p="$1"
    local scope="$2"
    local owner="$3"
    local kind="$4"
    local ext="$5"
    local base
    base="$(basename "$p")"

    if [ "$kind" = "directory" ]; then
        echo ""
        return
    fi

    case "$scope:$ext" in
        all_exiles:sh)
            echo "$EXILES/segue/authority_db/seeds/$base"
            ;;
        all_obelisks:sh)
            echo "$OBELISKS/segue/authority_db/seeds/$base"
            ;;
        entire_ontology:sh)
            echo "$OBELISKS/segue/ontology_ops/scripts/$base"
            ;;
        entire_runtime:sh)
            echo "$ROOT/ops/runtime/scripts/$base"
            ;;
        single_exile:sh)
            if [ "$owner" != "unknown" ]; then
                echo "$EXILES/$owner/segue/scripts/$base"
            else
                echo ""
            fi
            ;;
        single_exile:py)
            if [ "$owner" != "unknown" ]; then
                echo "$EXILES/$owner/runtime/$base"
            else
                echo ""
            fi
            ;;
        *)
            echo ""
            ;;
    esac
}

confidence_for() {
    local scope="$1"
    local owner="$2"
    local target="$3"

    if [ -z "$target" ]; then
        echo "0"
    elif [ "$scope" = "all_exiles" ]; then
        echo "95"
    elif [ "$scope" = "all_obelisks" ]; then
        echo "90"
    elif [ "$scope" = "single_exile" ] && [ "$owner" != "unknown" ]; then
        echo "90"
    elif [ "$scope" = "entire_runtime" ]; then
        echo "80"
    elif [ "$scope" = "entire_ontology" ]; then
        echo "80"
    else
        echo "40"
    fi
}

move_reason_for() {
    local scope="$1"
    local owner="$2"
    local ext="$3"

    case "$scope" in
        all_exiles)
            echo "operates_on_all_exiles_place_under_exiles_segue"
            ;;
        all_obelisks)
            echo "operates_on_obelisk_level_infrastructure_place_under_obelisks_segue"
            ;;
        single_exile)
            echo "mentions_or_resides_under_single_exile_owner_${owner}"
            ;;
        entire_runtime)
            echo "runtime_wide_operational_asset"
            ;;
        entire_ontology)
            echo "ontology_wide_operational_asset"
            ;;
        *)
            echo "unclassified_requires_manual_review"
            ;;
    esac
}

printf "id\tpath\tbasename\tkind\textension\tscope\towner\tedifice_level\tauthority_type\tconfidence\tproposed_target\tmove_reason\twarnings\n" > "$OUT"

find "$ROOT" -mindepth 1 \( -type f -o -type d -o -type l \) | sort |
while IFS= read -r path
do
    if is_generated_or_vendor "$path"; then
        continue
    fi

    kind="$(file_kind "$path")"
    ext="$(extension_of "$path")"
    scope="$(detect_scope "$path")"
    owner="$(detect_owner "$path")"
    level="$(detect_level "$scope")"
    authority_type="$(detect_authority_type "$path")"
    target="$(propose_target "$path" "$scope" "$owner" "$kind" "$ext")"
    confidence="$(confidence_for "$scope" "$owner" "$target")"
    reason="$(move_reason_for "$scope" "$owner" "$ext")"

    warnings=""

    if [ "$scope" = "unknown" ]; then
        warnings="unknown_scope"
    fi

    if [ -n "$target" ] && [ -e "$target" ] && [ "$target" != "$path" ]; then
        warnings="${warnings:+$warnings,}target_exists"
    fi

    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" \
        "$(hash_id "$path")" \
        "$path" \
        "$(basename "$path")" \
        "$kind" \
        "$ext" \
        "$scope" \
        "$owner" \
        "$level" \
        "$authority_type" \
        "$confidence" \
        "$target" \
        "$reason" \
        "$warnings" >> "$OUT"
done

echo
echo "[OK] classified scope objects:"
echo "$OUT"

echo
echo "=== HIGH CONFIDENCE MOVABLE FILES ==="
awk -F '\t' 'NR>1 && $10>=90 && $11!="" {print $6 "\t" $7 "\t" $10 "\t" $3 "\t" $2 " -> " $11}' "$OUT" | column -t -s $'\t' | sed -n '1,120p'

echo
echo "=== LOW / UNKNOWN ==="
awk -F '\t' 'NR>1 && ($10<90 || $11=="") {print $6 "\t" $7 "\t" $10 "\t" $3 "\t" $13}' "$OUT" | column -t -s $'\t' | sed -n '1,80p'

echo
echo "No files moved."
