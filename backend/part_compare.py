"""部件级跨琴/跨书对照：从图结构 flatten statement 并按 slot 对齐。"""

import difflib
import json
import os
from collections import defaultdict

CONFIG_DIR = os.path.dirname(__file__)
DEFAULT_CONFIG_PATH = os.path.join(CONFIG_DIR, "part_config.json")

CONTAINS_REL = "包含组件"
BODY_PART = "__body__"
BODY_PART_LABEL = "琴体"


def load_part_config(config_path=None):
    path = config_path or DEFAULT_CONFIG_PATH
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_part_taxonomy(config=None):
    """供前端部件树使用的标准部件与语义层配置。"""
    config = config or load_part_config()
    part_aliases = config.get("part_aliases", {})
    parts = list(part_aliases.keys())
    for aliases in part_aliases.values():
        for alias in aliases:
            if alias not in parts:
                parts.append(alias)
    ordered = []
    for p in config.get("part_order", []):
        if p not in ordered:
            ordered.append(p)
    for p in parts:
        if p not in ordered:
            ordered.append(p)
    if BODY_PART_LABEL not in ordered:
        ordered.insert(0, BODY_PART_LABEL)
    return {
        "parts": ordered,
        "part_aliases": part_aliases,
        "semantic_layers": config.get("semantic_layers", {}),
        "layer_order": config.get("layer_order", []),
        "diff_kind_labels": config.get("diff_kind_labels", {}),
    }


def _build_alias_map(alias_dict):
    mapping = {}
    for canonical, aliases in (alias_dict or {}).items():
        mapping[canonical] = canonical
        for alias in aliases:
            mapping[str(alias).strip()] = canonical
    return mapping


def _build_value_canonical(value_aliases):
    mapping = {}
    for canonical, variants in (value_aliases or {}).items():
        mapping[canonical] = canonical
        for variant in variants:
            mapping[str(variant).strip()] = canonical
    return mapping


def _strip_entity_prefix(name):
    text = str(name or "").strip()
    if "_" in text:
        return text.split("_", 1)[-1]
    return text


def node_display_name(node_id, node_properties):
    props = node_properties.get(node_id, {})
    name = str(props.get("original_name", "") or "").strip()
    return name if name else str(node_id)


def canonicalize_part(node_id, node_properties, part_alias_map, config):
    props = node_properties.get(node_id, {})
    raw = str(props.get("original_name", "") or _strip_entity_prefix(node_id)).strip()
    stripped = _strip_entity_prefix(raw)
    size_names = set(config.get("size_part_names", ["尺寸"]))
    if raw in size_names or stripped in size_names:
        return BODY_PART
    if raw in part_alias_map:
        return part_alias_map[raw]
    if stripped in part_alias_map:
        return part_alias_map[stripped]
    return stripped


def canonical_part_label(canonical_part):
    return BODY_PART_LABEL if canonical_part == BODY_PART else canonical_part


def normalize_predicate(relation, predicate_map):
    rel = str(relation or "").strip() or "关联"
    return predicate_map.get(rel, rel)


def canonical_value_key(value, value_canonical_map):
    text = str(value or "").strip()
    return value_canonical_map.get(text, text)


def value_from_neighbor(nbr_id, node_properties):
    props = node_properties.get(nbr_id, {})
    desc = str(props.get("description", "") or "").strip()
    name = node_display_name(nbr_id, node_properties)
    if desc and (not name or len(desc) >= len(name)):
        return desc
    return name


def get_relation(G, u, v):
    if G.has_edge(u, v):
        return str(G[u][v].get("relation", "关联") or "关联").strip()
    if G.has_edge(v, u):
        return str(G[v][u].get("relation", "关联") or "关联").strip()
    return "关联"


def artifact_parts(G, artifact_id):
    if artifact_id not in G.nodes:
        return []
    parts = []
    for nbr in G.neighbors(artifact_id):
        if get_relation(G, artifact_id, nbr) == CONTAINS_REL:
            parts.append(nbr)
    return parts


def flatten_artifact(artifact_id, G, node_properties, config):
    part_alias_map = _build_alias_map(config.get("part_aliases", {}))
    predicate_map = _build_alias_map(config.get("predicate_aliases", {}))
    value_canonical_map = _build_value_canonical(config.get("value_aliases", {}))

    statements = []
    parts = artifact_parts(G, artifact_id)

    def add_statement(canonical_part, predicate, value, level, path_nodes, path_edges):
        slot_key = f"{canonical_part}::{predicate}"
        statements.append({
            "slot_key": slot_key,
            "canonical_part": canonical_part,
            "canonical_part_label": canonical_part_label(canonical_part),
            "predicate": predicate,
            "value": value,
            "value_normalized": canonical_value_key(value, value_canonical_map),
            "level": level,
            "highlight_path": {
                "node_ids": path_nodes,
                "edges": path_edges,
            },
        })

    for nbr in G.neighbors(artifact_id):
        rel = get_relation(G, artifact_id, nbr)
        if rel == CONTAINS_REL:
            continue
        pred = normalize_predicate(rel, predicate_map)
        val = value_from_neighbor(nbr, node_properties)
        add_statement(
            BODY_PART,
            pred,
            val,
            "artifact",
            [artifact_id, nbr],
            [{"source": artifact_id, "target": nbr, "relation": rel}],
        )

    for part_id in parts:
        canonical_part = canonicalize_part(part_id, node_properties, part_alias_map, config)
        for nbr in G.neighbors(part_id):
            rel = get_relation(G, part_id, nbr)
            if rel == CONTAINS_REL or nbr == artifact_id:
                continue
            pred = normalize_predicate(rel, predicate_map)
            val = value_from_neighbor(nbr, node_properties)
            add_statement(
                canonical_part,
                pred,
                val,
                "part",
                [artifact_id, part_id, nbr],
                [
                    {"source": artifact_id, "target": part_id, "relation": CONTAINS_REL},
                    {"source": part_id, "target": nbr, "relation": rel},
                ],
            )

    by_slot = {}
    for stmt in statements:
        key = stmt["slot_key"]
        existing = by_slot.get(key)
        if not existing:
            by_slot[key] = stmt
        elif stmt["level"] == "part" and existing["level"] == "artifact":
            by_slot[key] = stmt
    return list(by_slot.values())


def classify_row(cell_list, predicate, config):
    present = [cell for cell in cell_list if cell[0]]
    if len(present) == len(cell_list):
        norm_vals = {cell[1] for cell in present if cell[1] is not None}
        if len(norm_vals) <= 1:
            return "S"
        if predicate in config.get("interpretation_predicates", []):
            return "I"
        return "V"
    if not present:
        return "M"
    return "A"


def build_inscription_diff(text_a, text_b):
    left = str(text_a or "")
    right = str(text_b or "")
    if not left or not right:
        return None
    if left == right:
        return {"equal": True, "segments": [{"type": "equal", "text": left}]}
    matcher = difflib.SequenceMatcher(None, left, right)
    segments = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            segments.append({"type": "equal", "text": left[i1:i2]})
        elif tag == "replace":
            segments.append({"type": "replace", "left": left[i1:i2], "right": right[j1:j2]})
        elif tag == "delete":
            segments.append({"type": "delete", "left": left[i1:i2], "right": ""})
        elif tag == "insert":
            segments.append({"type": "insert", "left": "", "right": right[j1:j2]})
    return {"equal": False, "segments": segments}


def semantic_layer(predicate, config):
    for layer_name, predicates in (config.get("semantic_layers") or {}).items():
        if predicate in predicates:
            return layer_name
    return "其他"


def _normalize_artifact_ids(artifact_ids, G):
    valid = []
    seen = set()
    for raw in artifact_ids or []:
        aid = str(raw).strip()
        if not aid or aid in seen:
            continue
        if aid not in G.nodes:
            continue
        props = G.nodes[aid]
        if int(props.get("is_artifact", 0) or 0) != 1:
            continue
        seen.add(aid)
        valid.append(aid)
    return valid


def compare_parts_core(
    artifact_ids,
    G,
    node_properties,
    book_label_fn=None,
    config=None,
    parts_filter=None,
    diff_kind_filter=None,
):
    config = config or load_part_config()
    if book_label_fn is None:
        book_label_fn = lambda code: code or ""

    valid_ids = _normalize_artifact_ids(artifact_ids, G)
    if len(valid_ids) < 2:
        return {
            "meta": {
                "ready": False,
                "reason": "need_two_artifacts",
                "artifact_ids": valid_ids,
            },
            "artifacts": [],
            "rows": [],
            "summary": {},
        }

    books = sorted({
        str(node_properties.get(aid, {}).get("book_clean", "") or "").strip().lower()
        for aid in valid_ids
        if str(node_properties.get(aid, {}).get("book_clean", "") or "").strip()
    })
    cross_book = len(books) > 1

    per_artifact = {
        aid: flatten_artifact(aid, G, node_properties, config)
        for aid in valid_ids
    }

    all_slots = set()
    for statements in per_artifact.values():
        for stmt in statements:
            all_slots.add(stmt["slot_key"])

    artifacts_meta = []
    for aid in valid_ids:
        props = node_properties.get(aid, {})
        book = str(props.get("book_clean", "") or "").strip().lower()
        artifacts_meta.append({
            "id": aid,
            "name": node_display_name(aid, node_properties),
            "book": book,
            "book_label": book_label_fn(book) if book else "",
            "source_text": str(props.get("source_text", "") or ""),
        })

    parts_filter_set = {str(p).strip() for p in (parts_filter or []) if str(p).strip()}
    diff_kind_filter_set = {str(k).strip().upper() for k in (diff_kind_filter or []) if str(k).strip()}

    rows = []
    layer_order = config.get("layer_order", [])
    part_order = config.get("part_order", [])

    def row_sort_key(row):
        layer = row.get("semantic_layer", "其他")
        try:
            layer_idx = layer_order.index(layer)
        except ValueError:
            layer_idx = 99
        part = row.get("canonical_part_label", "")
        try:
            part_idx = part_order.index(part)
        except ValueError:
            part_idx = 999 if part != BODY_PART_LABEL else -1
        return (layer_idx, part_idx, part, row.get("predicate", ""))

    for slot_key in sorted(all_slots):
        sample = None
        for aid in valid_ids:
            for stmt in per_artifact[aid]:
                if stmt["slot_key"] == slot_key:
                    sample = stmt
                    break
            if sample:
                break
        if not sample:
            continue

        if parts_filter_set and sample["canonical_part_label"] not in parts_filter_set:
            continue

        predicate = sample["predicate"]
        cells = {}
        cell_list = []

        for aid in valid_ids:
            match = next((s for s in per_artifact[aid] if s["slot_key"] == slot_key), None)
            if match:
                cells[aid] = {
                    "present": True,
                    "value": match["value"],
                    "value_normalized": match["value_normalized"],
                    "node_ids": match["highlight_path"]["node_ids"],
                    "highlight_path": match["highlight_path"],
                }
                cell_list.append((True, match["value_normalized"], match["value"]))
            else:
                cells[aid] = {
                    "present": False,
                    "value": None,
                    "value_normalized": None,
                    "node_ids": [],
                    "highlight_path": None,
                }
                cell_list.append((False, None, None))

        diff_kind = classify_row(cell_list, predicate, config)
        if diff_kind_filter_set and diff_kind not in diff_kind_filter_set:
            continue

        row = {
            "slot_key": slot_key,
            "canonical_part": sample["canonical_part"],
            "canonical_part_label": sample["canonical_part_label"],
            "predicate": predicate,
            "semantic_layer": semantic_layer(predicate, config),
            "diff_kind": diff_kind,
            "cells": cells,
        }

        if predicate in ("铭文全文", "题刻内容为") or sample["canonical_part_label"] == "铭文":
            texts = [
                (aid, cells[aid].get("value"))
                for aid in valid_ids
                if cells[aid].get("present")
            ]
            if len(texts) >= 2:
                row["inscription_diff"] = build_inscription_diff(texts[0][1], texts[1][1])

        rows.append(row)

    rows.sort(key=row_sort_key)

    by_diff_kind = defaultdict(int)
    for row in rows:
        by_diff_kind[row["diff_kind"]] += 1

    part_sets = {
        aid: {s["canonical_part_label"] for s in per_artifact[aid]}
        for aid in valid_ids
    }
    union_parts = set.union(*part_sets.values()) if part_sets else set()
    parts_only_in = {}
    for aid in valid_ids:
        others = set.union(*(part_sets[oid] for oid in valid_ids if oid != aid)) if len(valid_ids) > 1 else set()
        parts_only_in[aid] = sorted(part_sets[aid] - others)

    return {
        "meta": {
            "ready": True,
            "reason": "",
            "cross_book": cross_book,
            "books": books,
            "artifact_ids": valid_ids,
        },
        "artifacts": artifacts_meta,
        "rows": rows,
        "summary": {
            "by_diff_kind": dict(by_diff_kind),
            "total_slots": len(rows),
            "parts_only_in": parts_only_in,
            "union_parts": sorted(union_parts),
        },
    }
