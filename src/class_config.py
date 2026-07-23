"""Class mapping: model class IDs to custom export names."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ClassMapping:
    model_class_id: int
    model_class_name: str
    export_name: str
    enabled: bool = True


def build_mappings_from_model(class_names: dict[int, str]) -> list[ClassMapping]:
    return [
        ClassMapping(
            model_class_id=cid,
            model_class_name=name,
            export_name=name,
            enabled=True,
        )
        for cid, name in sorted(class_names.items())
    ]


def enabled_mappings(mappings: list[ClassMapping]) -> list[ClassMapping]:
    return [m for m in mappings if m.enabled]


def export_id_for_model_class(mappings: list[ClassMapping], model_class_id: int) -> int | None:
    active = enabled_mappings(mappings)
    for export_id, mapping in enumerate(active):
        if mapping.model_class_id == model_class_id:
            return export_id
    return None


def export_name_for_model_class(mappings: list[ClassMapping], model_class_id: int) -> str | None:
    for mapping in enabled_mappings(mappings):
        if mapping.model_class_id == model_class_id:
            return mapping.export_name
    return None


def export_class_names(mappings: list[ClassMapping]) -> dict[int, str]:
    return {i: m.export_name for i, m in enumerate(enabled_mappings(mappings))}


def enabled_model_class_ids(mappings: list[ClassMapping]) -> set[int]:
    return {m.model_class_id for m in enabled_mappings(mappings)}
