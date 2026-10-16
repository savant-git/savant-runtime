#!/usr/bin/env bash

_savant_jump() {
    local destination="${1:?destination required}"

    if [[ ! -d "$destination" ]]; then
        printf 'savant: directory unavailable: %s\n' \
            "$destination" >&2
        return 1
    fi

    builtin cd -- "$destination"
}


svr() {
    _savant_jump \
        "/root/savant-runtime"
}


xil() {
    _savant_jump \
        "/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles"
}


ont() {
    _savant_jump \
        "/root/savant-runtime/ontology"
}


liv() {
    _savant_jump \
        "/root/savant-runtime/runtime/living-state"
}


sdp() {
    _savant_jump \
        "/root/savant-runtime/tools/sdump-enterprise"
}


src() {
    _savant_jump \
        "/root/savant-runtime/source"
}


vlt() {
    _savant_jump \
        "/root/savant-runtime/vault"
}


pal() {
    _savant_jump \
        "/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/palaver"
}


mod() {
    _savant_jump \
        "/root/savant-runtime/ontology/obelisks/_template/segue/gates/_template/segue/innates/_template/segue/exiles/modus"
}


can() {
    _savant_jump \
        "/root/savant-runtime/canon"
}


too() {
    _savant_jump \
        "/root/savant-runtime/tools"
}


rpt() {
    _savant_jump \
        "/root/savant-runtime/runtime/reports"
}


upp() {
    builtin cd -- ..
}


prv() {
    builtin cd -- -
}


lst() {
    command ls \
        -lah \
        --group-directories-first \
        --time-style=long-iso \
        "${@:-.}"
}


tre() {
    local destination="${1:-.}"

    if command -v tree >/dev/null 2>&1; then
        command tree \
            -a \
            -L 3 \
            -- "$destination"
        return
    fi

    command find \
        "$destination" \
        -maxdepth 3 \
        -print
}


fnd() {
    if [[ "$#" -lt 1 ]]; then
        printf '%s\n' \
            "usage: fnd <name-fragment> [root]" >&2
        return 2
    fi

    local pattern="$1"
    local root="${2:-/root/savant-runtime}"

    command find \
        "$root" \
        -type f \
        -iname "*${pattern}*" \
        -print
}


drf() {
    if [[ "$#" -lt 1 ]]; then
        printf '%s\n' \
            "usage: drf <name-fragment> [root]" >&2
        return 2
    fi

    local pattern="$1"
    local root="${2:-/root/savant-runtime}"

    command find \
        "$root" \
        -type d \
        -iname "*${pattern}*" \
        -print
}


gre() {
    if [[ "$#" -lt 1 ]]; then
        printf '%s\n' \
            "usage: gre <pattern> [root]" >&2
        return 2
    fi

    local pattern="$1"
    local root="${2:-/root/savant-runtime}"

    if command -v rg >/dev/null 2>&1; then
        command rg \
            --hidden \
            --glob '!.git/**' \
            --glob '!source/**' \
            --glob '!vault/**' \
            --line-number \
            --smart-case \
            -- "$pattern" "$root"
        return
    fi

    command grep \
        -RIn \
        --exclude-dir=.git \
        --exclude-dir=source \
        --exclude-dir=vault \
        -- "$pattern" "$root"
}


sta() {
    /usr/local/bin/savant-living-state-status
}


sqs() {
    /usr/local/bin/savant-state \
        --status
}


chg() {
    /usr/local/bin/savant-state \
        delta
}


his() {
    if [[ "$#" -ne 1 ]]; then
        printf '%s\n' \
            "usage: his <file>" >&2
        return 2
    fi

    /usr/local/bin/wip \
        --history \
        "$1"
}


rst() {
    if [[ "$#" -ne 1 ]]; then
        printf '%s\n' \
            "usage: rst <file>" >&2
        return 2
    fi

    /usr/local/bin/wip \
        --restore \
        "$1"
}


cmd() {
    /usr/local/bin/savant-command
}
