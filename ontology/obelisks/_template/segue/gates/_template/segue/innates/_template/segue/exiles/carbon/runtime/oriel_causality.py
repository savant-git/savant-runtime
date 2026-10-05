#!/usr/bin/env python3
from __future__ import annotations
import copy
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Mapping, Sequence
from oriel import oriel_engine, parse_datetime, to_utc
owner = 'carbon'
component = 'oriel-causality'
authority_effect = 'none'
schema = 'savant.carbon.oriel-causality.v1'
immutable_source_classes = {'verified_external', 'admitted_evidence'}
intervention_kinds = {'delay', 'relocate', 'cancel'}
enhancements = ('entity precedence graph', 'resource precedence graph', 'travel-mediated causality', 'setup propagation', 'teardown propagation', 'recovery propagation', 'minimum-separation contracts', 'schedule slack projection', 'critical-edge classification', 'chronometric pressure', 'historical-anchor immutability', 'locked-anchor immutability', 'delay ripple propagation', 'relocation ripple propagation', 'cancellation reflow', 'multi-predecessor convergence', 'downstream delay accumulation', 'blocked-ripple reporting', 'unresolved-route reporting', 'deterministic graph identity', 'deterministic intervention identity', 'critical corridor discovery', 'minimum-slack corridor ranking', 'inevitability horizon', 'locked-target breach threshold', 'counterfactual intervention packets', 'quantum-compatible causal packets', 'inverse-compatible causal packets', 'filament-projectable causal packets', 'modus-maskable causal metadata', 'source-state immutability', 'canon-neutral causal projection', 'evidence-neutral causal projection')

class oriel_causality_error(RuntimeError):
    pass

def clone(value: Any) -> Any:
    return copy.deepcopy(value)

def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str)

def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()

def stable_id(prefix: str, value: Any) -> str:
    return prefix + ':' + digest(value)[:24]

def minutes_between(left: datetime, right: datetime) -> float:
    return (to_utc(right) - to_utc(left)).total_seconds() / 60.0

def event_locked(raw: Mapping[str, Any]) -> bool:
    metadata = raw.get('metadata', {})
    start = raw.get('start')
    end = raw.get('end')
    return bool(raw.get('locked', False) or (isinstance(metadata, Mapping) and metadata.get('locked', False)) or (isinstance(start, Mapping) and start.get('locked', False)) or (isinstance(end, Mapping) and end.get('locked', False)))

def event_immutable(raw: Mapping[str, Any]) -> bool:
    return event_locked(raw) or str(raw.get('source_class', 'unknown')).strip().lower() in immutable_source_classes

def event_index(document: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    output = {}
    for value in document.get('events', []):
        if not isinstance(value, Mapping):
            continue
        identifier = str(value.get('id', '')).strip()
        if identifier:
            output[identifier] = clone(dict(value))
    return output

def shift_temporal(value: Any, minutes: int) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        return (value + timedelta(minutes=minutes)).isoformat()
    if isinstance(value, str):
        return (parse_datetime(value) + timedelta(minutes=minutes)).isoformat()
    if not isinstance(value, Mapping):
        raise oriel_causality_error('unsupported temporal value')
    output = clone(dict(value))
    timezone_name = str(value.get('timezone')) if value.get('timezone') is not None else None
    for key in ('at', 'earliest', 'latest'):
        if value.get(key) is None:
            continue
        output[key] = (parse_datetime(value[key], timezone_name=timezone_name) + timedelta(minutes=minutes)).isoformat()
    return output

def shift_event(raw: Mapping[str, Any], minutes: int) -> dict[str, Any]:
    output = clone(dict(raw))
    output['start'] = shift_temporal(output.get('start'), minutes)
    if output.get('end') is not None:
        output['end'] = shift_temporal(output.get('end'), minutes)
    return output

def replace_event(document: Mapping[str, Any], replacement: Mapping[str, Any]) -> dict[str, Any]:
    identifier = str(replacement.get('id', '')).strip()
    output = clone(dict(document))
    values = []
    replaced = False
    for value in output.get('events', []):
        if isinstance(value, Mapping) and str(value.get('id', '')) == identifier:
            values.append(clone(dict(replacement)))
            replaced = True
        else:
            values.append(clone(value))
    if not replaced:
        raise oriel_causality_error('unknown event: ' + identifier)
    output['events'] = values
    return output

def remove_event(document: Mapping[str, Any], identifier: str) -> dict[str, Any]:
    output = clone(dict(document))
    original = list(output.get('events', []))
    values = [clone(value) for value in original if not (isinstance(value, Mapping) and str(value.get('id', '')) == identifier)]
    if len(values) == len(original):
        raise oriel_causality_error('unknown event: ' + identifier)
    output['events'] = values
    return output

def pressure_state(slack: float | None, threshold_minutes: float) -> str:
    if slack is None:
        return 'unresolved'
    if slack < 0:
        return 'blocked'
    if slack == 0:
        return 'critical'
    if slack <= threshold_minutes:
        return 'pressured'
    return 'buffered'

class OrielCausalityEngine:

    def graph(self, document: Mapping[str, Any], *, mode: str='tour_bus', pressure_threshold_minutes: float=60.0) -> dict[str, Any]:
        engine = oriel_engine.from_document(document)
        raw = event_index(document)
        events = sorted(engine.events.values(), key=lambda value: (to_utc(value.start.earliest), value.id))
        nodes = []
        for value in events:
            nodes.append({'id': value.id, 'kind': value.kind, 'entities': list(value.entities), 'resources': list(value.resources), 'location_id': value.location_id, 'scheduled_start': to_utc(value.start.earliest).isoformat(), 'duration_minutes': value.duration_minutes, 'source_class': value.source_class, 'locked': event_locked(raw[value.id]), 'immutable': event_immutable(raw[value.id])})
        candidates = []
        entity_groups = {}
        for value in events:
            for entity_id in value.entities:
                entity_groups.setdefault(entity_id, []).append(value)
        for entity_id, values in entity_groups.items():
            ordered = sorted(values, key=lambda value: (to_utc(value.start.earliest), value.id))
            for left, right in zip(ordered, ordered[1:]):
                travel = engine.travel(left.location_id, right.location_id, mode=mode)
                if travel.get('outcome') == 'unknown':
                    minimum = None
                    maximum = None
                    slack = None
                else:
                    minimum = left.duration_minutes + left.teardown_minutes + int(travel['minimum_minutes']) + max(left.recovery_minutes, 0) + right.setup_minutes
                    maximum = left.duration_minutes + left.teardown_minutes + int(travel['maximum_minutes']) + max(left.recovery_minutes, 0) + right.setup_minutes
                    slack = minutes_between(left.start.earliest, right.start.earliest) - minimum
                candidates.append({'source': left.id, 'target': right.id, 'cause': 'entity', 'cause_id': entity_id, 'minimum_separation_minutes': minimum, 'maximum_separation_minutes': maximum, 'slack_minutes': round(slack, 3) if slack is not None else None, 'pressure_state': pressure_state(slack, pressure_threshold_minutes), 'travel': travel})
        resource_groups = {}
        for value in events:
            for resource in value.resources:
                resource_groups.setdefault(resource, []).append(value)
        for resource, values in resource_groups.items():
            ordered = sorted(values, key=lambda value: (to_utc(value.start.earliest), value.id))
            for left, right in zip(ordered, ordered[1:]):
                minimum = left.duration_minutes + left.teardown_minutes + right.setup_minutes
                slack = minutes_between(left.start.earliest, right.start.earliest) - minimum
                candidates.append({'source': left.id, 'target': right.id, 'cause': 'resource', 'cause_id': resource, 'minimum_separation_minutes': minimum, 'maximum_separation_minutes': minimum, 'slack_minutes': round(slack, 3), 'pressure_state': pressure_state(slack, pressure_threshold_minutes), 'travel': None})
        merged = {}
        for value in candidates:
            key = (value['source'], value['target'])
            current = merged.get(key)
            cause = {'kind': value['cause'], 'id': value['cause_id']}
            if current is None:
                current = clone(value)
                current['causes'] = [cause]
                merged[key] = current
                continue
            current['causes'].append(cause)
            left_min = current.get('minimum_separation_minutes')
            right_min = value.get('minimum_separation_minutes')
            if left_min is None or right_min is None:
                current['minimum_separation_minutes'] = None
                current['maximum_separation_minutes'] = None
                current['slack_minutes'] = None
                current['pressure_state'] = 'unresolved'
            elif right_min > left_min:
                current['minimum_separation_minutes'] = right_min
                current['maximum_separation_minutes'] = value.get('maximum_separation_minutes')
                current['slack_minutes'] = value.get('slack_minutes')
                current['pressure_state'] = value.get('pressure_state')
                current['travel'] = clone(value.get('travel'))
        order = {value['id']: index for index, value in enumerate(nodes)}
        edges = sorted(merged.values(), key=lambda value: (order[value['source']], order[value['target']]))
        result = {'schema': schema, 'kind': 'causal-logistics-graph', 'owner': owner, 'component': component, 'authority_effect': authority_effect, 'mode': mode, 'pressure_threshold_minutes': pressure_threshold_minutes, 'nodes': nodes, 'edges': edges, 'node_count': len(nodes), 'edge_count': len(edges), 'blocked_edge_count': sum((1 for value in edges if value['pressure_state'] == 'blocked')), 'critical_edge_count': sum((1 for value in edges if value['pressure_state'] == 'critical')), 'pressured_edge_count': sum((1 for value in edges if value['pressure_state'] == 'pressured')), 'unresolved_edge_count': sum((1 for value in edges if value['pressure_state'] == 'unresolved')), 'source_state_mutated': False, 'canon_effect': 'none', 'evidence_admission': False}
        result['id'] = stable_id('carbon-oriel-causal-graph', result)
        result['digest'] = digest(result)
        return result

    def critical_corridor(self, document: Mapping[str, Any], *, target_event: str, mode: str='tour_bus') -> dict[str, Any]:
        graph = self.graph(document, mode=mode)
        nodes = {value['id']: value for value in graph['nodes']}
        if target_event not in nodes:
            raise oriel_causality_error('unknown target event: ' + target_event)
        predecessors = {}
        for edge in graph['edges']:
            predecessors.setdefault(edge['target'], []).append(edge)
        cost = {}
        path = {}
        for node in [value['id'] for value in graph['nodes']]:
            incoming = predecessors.get(node, [])
            if not incoming:
                cost[node] = 0.0
                path[node] = [node]
                continue
            choices = []
            for edge in incoming:
                source = edge['source']
                slack = edge.get('slack_minutes')
                if source not in cost or slack is None:
                    continue
                choices.append((cost[source] + max(0.0, float(slack)), source))
            if not choices:
                continue
            selected_cost, source = min(choices, key=lambda value: (value[0], value[1]))
            cost[node] = selected_cost
            path[node] = [*path[source], node]
        selected_path = path.get(target_event, [target_event])
        result = {'schema': schema, 'kind': 'critical-corridor', 'owner': owner, 'component': component, 'authority_effect': authority_effect, 'graph_id': graph['id'], 'target_event': target_event, 'path': selected_path, 'cumulative_absorbable_delay_minutes': round(cost.get(target_event, 0.0), 3), 'target_locked': nodes[target_event]['locked'], 'target_immutable': nodes[target_event]['immutable'], 'source_state_mutated': False, 'canon_effect': 'none'}
        result['digest'] = digest(result)
        return result

    def inevitability_horizon(self, document: Mapping[str, Any], *, source_event: str, target_event: str, mode: str='tour_bus') -> dict[str, Any]:
        graph = self.graph(document, mode=mode)
        nodes = {value['id']: value for value in graph['nodes']}
        if source_event not in nodes:
            raise oriel_causality_error('unknown source event: ' + source_event)
        if target_event not in nodes:
            raise oriel_causality_error('unknown target event: ' + target_event)
        successors = {}
        for edge in graph['edges']:
            successors.setdefault(edge['source'], []).append(edge)
        queue = [(0.0, source_event, [source_event])]
        best = {source_event: 0.0}
        selected = None
        unresolved = False
        while queue:
            queue.sort(key=lambda value: (value[0], value[1]))
            current_cost, node, current_path = queue.pop(0)
            if node == target_event:
                selected = (current_cost, current_path)
                break
            if current_cost > best.get(node, float('inf')):
                continue
            for edge in successors.get(node, []):
                slack = edge.get('slack_minutes')
                if slack is None:
                    unresolved = True
                    continue
                target = edge['target']
                next_cost = current_cost + max(0.0, float(slack))
                if next_cost >= best.get(target, float('inf')):
                    continue
                best[target] = next_cost
                queue.append((next_cost, target, [*current_path, target]))
        if selected is None:
            state = 'unresolved' if unresolved else 'disconnected'
            absorbable = None
            selected_path = []
        else:
            state = 'resolved'
            absorbable, selected_path = selected
        result = {'schema': schema, 'kind': 'inevitability-horizon', 'owner': owner, 'component': component, 'authority_effect': authority_effect, 'graph_id': graph['id'], 'source_event': source_event, 'target_event': target_event, 'state': state, 'path': selected_path, 'absorbable_delay_minutes': round(absorbable, 3) if absorbable is not None else None, 'target_locked': nodes[target_event]['locked'], 'target_immutable': nodes[target_event]['immutable'], 'causal_claim_is_projection': True, 'canon_effect': 'none'}
        result['digest'] = digest(result)
        return result

    def _apply_intervention(self, document: Mapping[str, Any], intervention: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        kind = str(intervention.get('kind', '')).strip().lower()
        if kind not in intervention_kinds:
            raise oriel_causality_error('unsupported intervention kind: ' + kind)
        identifier = str(intervention.get('event', '')).strip()
        if not identifier:
            raise oriel_causality_error('intervention event is required')
        raw = event_index(document).get(identifier)
        if raw is None:
            raise oriel_causality_error('unknown intervention event: ' + identifier)
        if event_immutable(raw):
            raise oriel_causality_error('intervention may not mutate immutable event: ' + identifier)
        if kind == 'delay':
            minutes = int(intervention.get('minutes', 0))
            if minutes < 0:
                raise oriel_causality_error('delay minutes may not be negative')
            return (replace_event(document, shift_event(raw, minutes)), {'kind': 'delay', 'event': identifier, 'minutes': minutes})
        if kind == 'relocate':
            location_id = str(intervention.get('location_id', '')).strip()
            if not location_id:
                raise oriel_causality_error('relocation requires location_id')
            changed = clone(raw)
            changed['location_id'] = location_id
            return (replace_event(document, changed), {'kind': 'relocate', 'event': identifier, 'from': raw.get('location_id'), 'to': location_id})
        return (remove_event(document, identifier), {'kind': 'cancel', 'event': identifier})

    def propagate(self, document: Mapping[str, Any], intervention: Mapping[str, Any], *, mode: str='tour_bus') -> dict[str, Any]:
        original_graph = self.graph(document, mode=mode)
        changed_document, normalized = self._apply_intervention(document, intervention)
        if normalized['kind'] == 'cancel':
            projected_graph = self.graph(changed_document, mode=mode)
            result = {'schema': schema, 'kind': 'causal-propagation', 'owner': owner, 'component': component, 'authority_effect': authority_effect, 'intervention': normalized, 'outcome': 'projected', 'original_graph_id': original_graph['id'], 'projected_graph': projected_graph, 'schedule': [], 'violations': [], 'source_state_mutated': False, 'canon_effect': 'none', 'evidence_admission': False}
            result['id'] = stable_id('carbon-oriel-propagation', result)
            result['digest'] = digest(result)
            return result
        changed_engine = oriel_engine.from_document(changed_document)
        raw_changed = event_index(changed_document)
        parsed = changed_engine.events
        ordered_ids = [value['id'] for value in original_graph['nodes'] if value['id'] in parsed]
        original_start = {value['id']: datetime.fromisoformat(value['scheduled_start']) for value in original_graph['nodes']}
        scheduled_start = {identifier: to_utc(parsed[identifier].start.earliest) for identifier in ordered_ids}
        effective_start = dict(scheduled_start)
        predecessors = {}
        for edge in original_graph['edges']:
            predecessors.setdefault(edge['target'], []).append(edge)
        violations = []
        unresolved_dependencies = []
        for identifier in ordered_ids:
            required_candidates = []
            for edge in predecessors.get(identifier, []):
                source = edge['source']
                if source not in effective_start:
                    continue
                left = parsed[source]
                right = parsed[identifier]
                separations = []
                for cause in edge.get('causes', []):
                    if cause['kind'] == 'entity':
                        travel = changed_engine.travel(left.location_id, right.location_id, mode=mode)
                        if travel.get('outcome') == 'unknown':
                            unresolved_dependencies.append({'source': source, 'target': identifier, 'reason': 'travel unresolved'})
                            continue
                        separations.append(left.duration_minutes + left.teardown_minutes + int(travel['minimum_minutes']) + max(left.recovery_minutes, 0) + right.setup_minutes)
                    elif cause['kind'] == 'resource':
                        separations.append(left.duration_minutes + left.teardown_minutes + right.setup_minutes)
                if not separations:
                    continue
                separation = max(separations)
                required_candidates.append((effective_start[source] + timedelta(minutes=separation), source, separation))
            if not required_candidates:
                continue
            required_start, source, separation = max(required_candidates, key=lambda value: value[0])
            if required_start <= effective_start[identifier]:
                continue
            required_shift = round(minutes_between(effective_start[identifier], required_start), 3)
            if event_immutable(raw_changed[identifier]):
                violations.append({'event': identifier, 'blocking_predecessor': source, 'required_shift_minutes': required_shift, 'minimum_separation_minutes': separation, 'reason': 'causal ripple reaches an immutable anchor', 'source_class': raw_changed[identifier].get('source_class', 'unknown'), 'locked': event_locked(raw_changed[identifier])})
                continue
            effective_start[identifier] = required_start
        schedule = []
        for identifier in ordered_ids:
            schedule.append({'event': identifier, 'original_start': original_start[identifier].isoformat(), 'intervention_scheduled_start': scheduled_start[identifier].isoformat(), 'effective_start': effective_start[identifier].isoformat(), 'net_shift_minutes': round(minutes_between(original_start[identifier], effective_start[identifier]), 3), 'ripple_shift_minutes': round(minutes_between(scheduled_start[identifier], effective_start[identifier]), 3), 'immutable': event_immutable(raw_changed[identifier])})
        outcome = 'blocked' if violations else 'unresolved' if unresolved_dependencies else 'projected'
        result = {'schema': schema, 'kind': 'causal-propagation', 'owner': owner, 'component': component, 'authority_effect': authority_effect, 'intervention': normalized, 'outcome': outcome, 'original_graph_id': original_graph['id'], 'schedule': schedule, 'violations': violations, 'unresolved_dependencies': unresolved_dependencies, 'shifted_event_count': sum((1 for value in schedule if value['net_shift_minutes'] != 0)), 'ripple_shifted_event_count': sum((1 for value in schedule if value['ripple_shift_minutes'] > 0)), 'immutable_anchor_breach_count': len(violations), 'projected_document': changed_document, 'source_state_mutated': False, 'canon_effect': 'none', 'evidence_admission': False, 'causal_claim_is_projection': True}
        result['id'] = stable_id('carbon-oriel-propagation', result)
        result['digest'] = digest(result)
        return result

engine = OrielCausalityEngine()

def capability_manifest() -> dict[str, Any]:
    projection = {'modes': ['reference', 'instance', 'composition'], 'instanceable': True, 'composable': True, 'maskable': True, 'ownership_transfer': False, 'authority_transfer': False}

    def capability(identifier: str, kind: str, purpose: str, operations: Sequence[str]) -> dict[str, Any]:
        return {'id': identifier, 'owner': owner, 'component': component, 'kind': kind, 'purpose': purpose, 'version': '1.0.0', 'status': 'active', 'authority_effect': 'none', 'execution_owner': owner, 'projection_owner': 'filament', 'transformation_owner': 'modus', 'operations': list(operations), 'deterministic': True, 'projection': clone(projection)}
    return {'schema': 'savant.carbon.oriel-causality.capabilities.v1', 'owner': owner, 'component': component, 'authority_effect': authority_effect, 'capabilities': [capability('oriel_causal_logistics_graph', 'causal-projection', 'Project causal precedence from chronology, travel, entities and shared resources.', ['graph']), capability('oriel_ripple_propagation', 'counterfactual-projection', 'Project downstream logistical effects of delays, relocations and cancellations.', ['propagate']), capability('oriel_critical_corridor', 'causal-analysis', 'Find the minimum-slack causal corridor terminating at an event.', ['critical_corridor']), capability('oriel_inevitability_horizon', 'causal-analysis', 'Calculate how much disruption a causal corridor can absorb before its target must be affected.', ['inevitability_horizon'])], 'invariants': {'carbon_owns_causal_simulation': True, 'oriel_projects_logistical_causality': True, 'oriel_does_not_create_causal_authority': True, 'historical_anchors_are_immutable': True, 'source_state_is_immutable': True, 'canon_effect': 'none', 'evidence_admission': False}}

def status() -> dict[str, Any]:
    return {'schema': schema, 'kind': 'status', 'owner': owner, 'component': component, 'authority_effect': authority_effect, 'carbon_owned': True, 'intervention_kinds': sorted(intervention_kinds), 'historical_anchor_mutation': False, 'causal_authority_effect': 'none', 'enhancement_count': len(enhancements), 'enhancements': list(enhancements), 'ready': True}

def selftest() -> dict[str, Any]:
    document = {'locations': [{'id': 'alpha', 'name': 'alpha', 'latitude': 40.0, 'longitude': -75.0, 'timezone': 'America/New_York', 'source_class': 'verified_external'}, {'id': 'beta', 'name': 'beta', 'latitude': 41.0, 'longitude': -74.0, 'timezone': 'America/New_York', 'source_class': 'verified_external'}, {'id': 'gamma', 'name': 'gamma', 'latitude': 42.0, 'longitude': -73.0, 'timezone': 'America/New_York', 'source_class': 'verified_external'}], 'routes': [{'source': 'alpha', 'target': 'beta', 'mode': 'tour_bus', 'distance_km': 180, 'minimum_minutes': 120, 'maximum_minutes': 150, 'source_class': 'verified_external'}, {'source': 'beta', 'target': 'gamma', 'mode': 'tour_bus', 'distance_km': 260, 'minimum_minutes': 180, 'maximum_minutes': 210, 'source_class': 'verified_external'}], 'events': [{'id': 'show-a', 'kind': 'show', 'entities': ['band'], 'location_id': 'alpha', 'start': '2026-01-01T10:00:00-05:00', 'duration_minutes': 60, 'source_class': 'simulation'}, {'id': 'show-b', 'kind': 'show', 'entities': ['band'], 'location_id': 'beta', 'start': '2026-01-01T14:00:00-05:00', 'duration_minutes': 60, 'source_class': 'simulation'}, {'id': 'show-c', 'kind': 'show', 'entities': ['band'], 'location_id': 'gamma', 'start': '2026-01-01T20:00:00-05:00', 'duration_minutes': 60, 'source_class': 'verified_external', 'metadata': {'locked': True}}]}
    graph = engine.graph(document)
    if graph['edge_count'] != 2:
        raise oriel_causality_error('selftest expected two causal edges')
    horizon = engine.inevitability_horizon(document, source_event='show-a', target_event='show-c')
    if horizon['absorbable_delay_minutes'] != 180.0:
        raise oriel_causality_error('selftest produced incorrect horizon')
    absorbed = engine.propagate(document, {'kind': 'delay', 'event': 'show-a', 'minutes': 120})
    if absorbed['immutable_anchor_breach_count'] != 0:
        raise oriel_causality_error('absorbable delay breached anchor')
    blocked = engine.propagate(document, {'kind': 'delay', 'event': 'show-a', 'minutes': 240})
    if blocked['immutable_anchor_breach_count'] < 1:
        raise oriel_causality_error('excess delay failed to reach anchor')
    corridor = engine.critical_corridor(document, target_event='show-c')
    return {'schema': schema, 'kind': 'selftest', 'owner': owner, 'component': component, 'authority_effect': authority_effect, 'ok': True, 'edge_count': graph['edge_count'], 'inevitability_horizon_minutes': horizon['absorbable_delay_minutes'], 'absorbable_delay_preserved_anchor': True, 'excess_delay_reached_anchor': True, 'critical_corridor': corridor['path'], 'source_state_mutated': False, 'canon_effect': 'none', 'evidence_admission': False}

__all__ = ['OrielCausalityEngine', 'capability_manifest', 'engine', 'selftest', 'status']
