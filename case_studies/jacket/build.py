import os
import sys
import uuid

import olca_schema as o
from olca_schema import units

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))
from ld_dir import write_ld_dir


def uid():
    return str(uuid.uuid4())


KG = dict(unit=units.unit_ref("kg"), prop=units.property_ref("kg"))
UNIT = dict(unit=units.unit_ref("unit"), prop=units.property_ref("unit"))


def flow_prop_factor(prop_ref):
    return o.FlowPropertyFactor(conversion_factor=1.0, flow_property=prop_ref, is_ref_flow_property=True)


def make_product_flow(name, unit_kind):
    return o.Flow(
        id=uid(), name=name, flow_type=o.FlowType.PRODUCT_FLOW,
        category="products", flow_properties=[flow_prop_factor(unit_kind["prop"])],
    )


def make_elem_flow(name):
    return o.Flow(
        id=uid(), name=name, flow_type=o.FlowType.ELEMENTARY_FLOW,
        category="elementary flows/air", flow_properties=[flow_prop_factor(KG["prop"])],
    )


def ref_to(flow):
    return o.Ref(id=flow.id, ref_type=o.RefType.Flow, name=flow.name, flow_type=flow.flow_type)


def proc_ref(process):
    return o.Ref(id=process.id, ref_type=o.RefType.Process, name=process.name)


def output_exchange(flow, unit_kind, amount, internal_id):
    return o.Exchange(
        flow=ref_to(flow), amount=amount, unit=unit_kind["unit"], flow_property=unit_kind["prop"],
        internal_id=internal_id, is_input=False, is_quantitative_reference=True,
    )


def input_exchange(flow, unit_kind, amount, provider_ref, internal_id):
    return o.Exchange(
        flow=ref_to(flow), amount=amount, unit=unit_kind["unit"], flow_property=unit_kind["prop"],
        internal_id=internal_id, is_input=True, is_quantitative_reference=False,
        default_provider=provider_ref,
    )


def emission_exchange(flow, amount, internal_id):
    return o.Exchange(
        flow=ref_to(flow), amount=amount, unit=KG["unit"], flow_property=KG["prop"],
        internal_id=internal_id, is_input=False, is_quantitative_reference=False,
    )


# ---- Flows ----
raw_fiber = make_product_flow("Raw fiber material", KG)
fiber = make_product_flow("Fiber", KG)
fabric = make_product_flow("Fabric", KG)
zipper = make_product_flow("Zipper", UNIT)
jacket = make_product_flow("Jacket", UNIT)
co2 = make_elem_flow("CO2")
ch4 = make_elem_flow("CH4")
nox = make_elem_flow("NOx")
flows = [raw_fiber, fiber, fabric, zipper, jacket, co2, ch4, nox]

GLO = o.Ref(id=uid(), ref_type=o.RefType.Location, name="GLO")

# ---- Processes ----
proc_raw = o.Process(
    id=uid(), name="Raw material extraction", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(raw_fiber, KG, 1.0, 1),
        emission_exchange(co2, 1.8, 2),
        emission_exchange(ch4, 0.02, 3),
    ],
)
proc_spinning = o.Process(
    id=uid(), name="Spinning", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(fiber, KG, 1.0, 1),
        input_exchange(raw_fiber, KG, 1.2, proc_ref(proc_raw), 2),
        emission_exchange(co2, 1.2, 3),
        emission_exchange(ch4, 0.01, 4),
    ],
)
proc_weaving = o.Process(
    id=uid(), name="Fabric weaving", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(fabric, KG, 1.0, 1),
        input_exchange(fiber, KG, 1.1, proc_ref(proc_spinning), 2),
        emission_exchange(co2, 1.5, 3),
        emission_exchange(nox, 0.01, 4),
    ],
)
proc_zipper = o.Process(
    id=uid(), name="Zipper production", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(zipper, UNIT, 1.0, 1),
        emission_exchange(co2, 0.4, 2),
        emission_exchange(nox, 0.005, 3),
    ],
)
proc_assembly = o.Process(
    id=uid(), name="Jacket assembly", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(jacket, UNIT, 1.0, 1),
        input_exchange(fabric, KG, 0.6, proc_ref(proc_weaving), 2),
        input_exchange(zipper, UNIT, 1.0, proc_ref(proc_zipper), 3),
        emission_exchange(co2, 0.8, 4),
    ],
)
processes = [proc_raw, proc_spinning, proc_weaving, proc_zipper, proc_assembly]

product_system = o.ProductSystem(
    id=uid(), name="Jacket product system",
    description="Pre-linked product system for one jacket.",
    ref_process=proc_ref(proc_assembly), ref_exchange=o.ExchangeRef(internal_id=1),
    target_amount=1.0, target_flow_property=UNIT["prop"], target_unit=UNIT["unit"],
    processes=[proc_ref(process) for process in processes],
    process_links=[
        o.ProcessLink(provider=proc_ref(proc_raw), flow=ref_to(raw_fiber), process=proc_ref(proc_spinning), exchange=o.ExchangeRef(internal_id=2)),
        o.ProcessLink(provider=proc_ref(proc_spinning), flow=ref_to(fiber), process=proc_ref(proc_weaving), exchange=o.ExchangeRef(internal_id=2)),
        o.ProcessLink(provider=proc_ref(proc_weaving), flow=ref_to(fabric), process=proc_ref(proc_assembly), exchange=o.ExchangeRef(internal_id=2)),
        o.ProcessLink(provider=proc_ref(proc_zipper), flow=ref_to(zipper), process=proc_ref(proc_assembly), exchange=o.ExchangeRef(internal_id=3)),
    ],
)

# ---- LCIA method: TRACI v2.1 characterization factors ----
gwp = o.ImpactCategory(
    id=uid(), name="GWP", ref_unit="kg CO2-eq",
    description="Climate change category for testing calculation engines only. CFs match TRACI v2.1 GWP100.",
    impact_factors=[
        o.ImpactFactor(flow=ref_to(co2), unit=KG["unit"], flow_property=KG["prop"], value=1.0),
        o.ImpactFactor(flow=ref_to(ch4), unit=KG["unit"], flow_property=KG["prop"], value=25.0),
    ],
)
ap = o.ImpactCategory(
    id=uid(), name="AP", ref_unit="kg SO2-eq",
    description="Acidification category for testing calculation engines only. CF matches TRACI v2.1 AP.",
    impact_factors=[o.ImpactFactor(flow=ref_to(nox), unit=KG["unit"], flow_property=KG["prop"], value=0.7)],
)
ep = o.ImpactCategory(
    id=uid(), name="EP", ref_unit="kg N-eq",
    description="Eutrophication category for testing calculation engines only. CF matches TRACI v2.1 EP.",
    impact_factors=[o.ImpactFactor(flow=ref_to(nox), unit=KG["unit"], flow_property=KG["prop"], value=0.04429)],
)
mir = o.ImpactCategory(
    id=uid(), name="MIR", ref_unit="kg O3-eq",
    description="Photochemical oxidant formation category for testing calculation engines only. CFs match TRACI v2.1 MIR.",
    impact_factors=[
        o.ImpactFactor(flow=ref_to(ch4), unit=KG["unit"], flow_property=KG["prop"], value=0.01437948717948718),
        o.ImpactFactor(flow=ref_to(nox), unit=KG["unit"], flow_property=KG["prop"], value=24.79358974358974),
    ],
)
pmfp = o.ImpactCategory(
    id=uid(), name="PMFP", ref_unit="kg PM2.5-eq",
    description="Particulate matter formation category for testing calculation engines only. CF matches TRACI v2.1 PMFP.",
    impact_factors=[o.ImpactFactor(flow=ref_to(nox), unit=KG["unit"], flow_property=KG["prop"], value=0.007222222222222222)],
)
method = o.ImpactMethod(
    id=uid(), name="LCIA Method",
    description="LCIA method for cross-engine testing only. Not for real assessment.",
    impact_categories=[
        o.Ref(id=gwp.id, ref_type=o.RefType.ImpactCategory, name=gwp.name),
        o.Ref(id=ap.id, ref_type=o.RefType.ImpactCategory, name=ap.name),
        o.Ref(id=ep.id, ref_type=o.RefType.ImpactCategory, name=ep.name),
        o.Ref(id=mir.id, ref_type=o.RefType.ImpactCategory, name=mir.name),
        o.Ref(id=pmfp.id, ref_type=o.RefType.ImpactCategory, name=pmfp.name),
    ],
)


def make_unit_group(symbol):
    unit_ref = units.unit_ref(symbol)
    group_ref = units.group_ref(symbol)
    unit_entity = o.Unit(id=unit_ref.id, name=symbol, conversion_factor=1.0, is_ref_unit=True)
    return o.UnitGroup(id=group_ref.id, name=group_ref.name, units=[unit_entity])


unit_groups = {symbol: make_unit_group(symbol) for symbol in ["kg", "unit"]}

outdir = os.path.dirname(os.path.abspath(__file__))
ld_dir = os.path.join(outdir, "olca_ld")
entities = flows + processes + [product_system, gwp, ap, ep, mir, pmfp, method] + list(unit_groups.values())
write_ld_dir(ld_dir, entities)

print("Wrote", ld_dir)
print("Jacket assembly process id:", proc_assembly.id)
print("Method id:", method.id)
