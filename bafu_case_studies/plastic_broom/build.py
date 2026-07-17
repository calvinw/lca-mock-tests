import json
import os
import sys
import uuid
from pathlib import Path

import olca_schema as o
from olca_schema import units

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from ld_dir import write_ld_dir


CASE_DIR = Path(__file__).resolve().parent
NAMESPACE = uuid.UUID("a7523c8d-0251-4ccb-9877-fb203b72cb1f")
LAST_CHANGE = "2026-07-16T00:00:00Z"


def uid(name):
    return str(uuid.uuid5(NAMESPACE, name))


def flow_property_factor(prop_ref):
    return o.FlowPropertyFactor(
        conversion_factor=1.0,
        flow_property=prop_ref,
        is_ref_flow_property=True,
    )


def make_unit_group(symbol):
    unit_ref = units.unit_ref(symbol)
    group_ref = units.group_ref(symbol)
    return o.UnitGroup(
        id=group_ref.id,
        last_change=LAST_CHANGE,
        name=group_ref.name,
        units=[
            o.Unit(
                id=unit_ref.id,
                name=unit_ref.name,
                conversion_factor=1.0,
                is_ref_unit=True,
            )
        ],
    )


def process_ref(provider):
    return o.Ref(
        id=provider["process_uuid"],
        ref_type=o.RefType.Process,
        name=provider["process_name"],
        process_type=o.ProcessType.UNIT_PROCESS,
    )


def flow_ref(provider):
    return o.Ref(
        id=provider["flow_uuid"],
        ref_type=o.RefType.Flow,
        name=provider["flow_name"],
        flow_type=o.FlowType.PRODUCT_FLOW,
    )


manifest = json.loads((CASE_DIR / "providers.json").read_text())
providers = manifest["providers"]

unit_kind = {
    "unit": {"unit": units.unit_ref("unit"), "prop": units.property_ref("unit")},
    "kg": {"unit": units.unit_ref("kg"), "prop": units.property_ref("kg")},
    "tkm": {"unit": units.unit_ref("tkm"), "prop": units.property_ref("tkm")},
}

plastic_broom = o.Flow(
    id=uid("flow:plastic-broom"),
    last_change=LAST_CHANGE,
    name="Plastic broom",
    flow_type=o.FlowType.PRODUCT_FLOW,
    category="BAFU integration examples/products",
    flow_properties=[flow_property_factor(unit_kind["unit"]["prop"])],
)

plastic_broom_ref = o.Ref(
    id=plastic_broom.id,
    ref_type=o.RefType.Flow,
    name=plastic_broom.name,
    flow_type=plastic_broom.flow_type,
)

assembly_ref = None
exchanges = [
    o.Exchange(
        flow=plastic_broom_ref,
        amount=1.0,
        unit=unit_kind["unit"]["unit"],
        flow_property=unit_kind["unit"]["prop"],
        internal_id=1,
        is_input=False,
        is_quantitative_reference=True,
    )
]

for internal_id, provider in enumerate(providers, start=2):
    kind = unit_kind[provider["unit"]]
    exchanges.append(
        o.Exchange(
            flow=flow_ref(provider),
            amount=provider["amount"],
            unit=kind["unit"],
            flow_property=kind["prop"],
            internal_id=internal_id,
            is_input=True,
            is_quantitative_reference=False,
            default_provider=process_ref(provider),
        )
    )

assembly = o.Process(
    id=uid("process:plastic-broom-assembly"),
    last_change=LAST_CHANGE,
    name="Plastic broom assembly",
    description=(
        "Foreground-only integration process. Its three inputs reference "
        "providers in the separately installed BAFU-2026 v1 database."
    ),
    process_type=o.ProcessType.UNIT_PROCESS,
    location=o.Ref(
        id="56bca136-90bb-3a77-9abb-7ce558af711e",
        ref_type=o.RefType.Location,
        name="GLO",
    ),
    exchanges=exchanges,
)
assembly_ref = o.Ref(
    id=assembly.id,
    ref_type=o.RefType.Process,
    name=assembly.name,
    process_type=assembly.process_type,
)

product_system = o.ProductSystem(
    id=uid("product-system:plastic-broom"),
    last_change=LAST_CHANGE,
    name="Plastic broom — BAFU-2026 v1 (foreground seed)",
    description=(
        "Foreground-only seed containing the three direct BAFU links. Import "
        "BAFU-2026 v1 first, then create an automatically linked product "
        "system from the assembly process to include BAFU's upstream graph."
    ),
    ref_process=assembly_ref,
    ref_exchange=o.ExchangeRef(internal_id=1),
    target_amount=1.0,
    target_flow_property=unit_kind["unit"]["prop"],
    target_unit=unit_kind["unit"]["unit"],
    processes=[assembly_ref] + [process_ref(provider) for provider in providers],
    process_links=[
        o.ProcessLink(
            provider=process_ref(provider),
            flow=flow_ref(provider),
            process=assembly_ref,
            exchange=o.ExchangeRef(internal_id=internal_id),
        )
        for internal_id, provider in enumerate(providers, start=2)
    ],
)

entities = [
    plastic_broom,
    assembly,
    product_system,
    make_unit_group("unit"),
    make_unit_group("kg"),
    make_unit_group("tkm"),
]

ld_dir = CASE_DIR / "olca_ld"
write_ld_dir(ld_dir, entities)
(ld_dir / "locations").mkdir(exist_ok=True)
(ld_dir / "locations" / ".gitkeep").touch()

print("Wrote", ld_dir)
print("Foreground process id:", assembly.id)
print("Product system id:", product_system.id)
