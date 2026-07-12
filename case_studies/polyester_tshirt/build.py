import uuid, os, sys
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

# ---- Flows ----
oil = make_product_flow("Crude oil", KG)
fiber = make_product_flow("Polyester fiber", KG)
tshirt = make_product_flow("T-shirt", UNIT)
co2 = make_elem_flow("CO2")
ch4 = make_elem_flow("CH4")

flows = [oil, fiber, tshirt, co2, ch4]

def ref_to(flow):
    return o.Ref(id=flow.id, ref_type=o.RefType.Flow, name=flow.name, flow_type=flow.flow_type)

def proc_ref(p):
    return o.Ref(id=p.id, ref_type=o.RefType.Process, name=p.name)

def output_exchange(flow, unit_kind, amount):
    return o.Exchange(
        flow=ref_to(flow), amount=amount, unit=unit_kind["unit"], flow_property=unit_kind["prop"],
        is_input=False, is_quantitative_reference=True,
    )

def input_exchange(flow, unit_kind, amount, provider_ref):
    return o.Exchange(
        flow=ref_to(flow), amount=amount, unit=unit_kind["unit"], flow_property=unit_kind["prop"],
        is_input=True, is_quantitative_reference=False, default_provider=provider_ref,
    )

def emission_exchange(flow, amount):
    return o.Exchange(
        flow=ref_to(flow), amount=amount, unit=KG["unit"], flow_property=KG["prop"],
        is_input=False, is_quantitative_reference=False,
    )

GLO = o.Ref(id=uid(), ref_type=o.RefType.Location, name="GLO")

# ---- Processes ----
proc_oil = o.Process(
    id=uid(), name="Oil extraction", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(oil, KG, 1.0),
        emission_exchange(co2, 0.2),
        emission_exchange(ch4, 0.05),
    ],
)

proc_fiber = o.Process(
    id=uid(), name="Polyester fiber production", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(fiber, KG, 1.0),
        input_exchange(oil, KG, 1.5, proc_ref(proc_oil)),
        emission_exchange(co2, 5.5),
    ],
)

proc_tshirt = o.Process(
    id=uid(), name="T-shirt assembly", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(tshirt, UNIT, 1.0),
        input_exchange(fiber, KG, 0.2, proc_ref(proc_fiber)),
        emission_exchange(co2, 1.0),
    ],
)

processes = [proc_oil, proc_fiber, proc_tshirt]

# ---- LCIA method (CFs are the real TRACI v2.1 values used in the
# recipe-card teaching case this is modeled on, not invented round numbers --
# see life-cycle-assessment-mcp/case_studies/polyester_tshirt.md) ----
gwp = o.ImpactCategory(
    id=uid(), name="GWP", ref_unit="kg CO2-eq",
    description="impact category for testing calculation engines only. CFs match TRACI v2.1 GWP100.",
    impact_factors=[
        o.ImpactFactor(flow=ref_to(co2), unit=KG["unit"], flow_property=KG["prop"], value=1.0),
        o.ImpactFactor(flow=ref_to(ch4), unit=KG["unit"], flow_property=KG["prop"], value=25.0),
    ],
)
mir = o.ImpactCategory(
    id=uid(), name="MIR", ref_unit="kg O3-eq",
    description="photochemical oxidant formation category for testing calculation engines only. CF matches TRACI v2.1 MIR.",
    impact_factors=[
        o.ImpactFactor(flow=ref_to(ch4), unit=KG["unit"], flow_property=KG["prop"], value=0.014379488),
    ],
)
method = o.ImpactMethod(
    id=uid(), name="LCIA Method",
    description="LCIA method for cross-engine testing only. Not for real assessment.",
    impact_categories=[
        o.Ref(id=gwp.id, ref_type=o.RefType.ImpactCategory, name=gwp.name),
        o.Ref(id=mir.id, ref_type=o.RefType.ImpactCategory, name=mir.name),
    ],
)

def make_unit_group(symbol):
    u_ref = units.unit_ref(symbol)
    g_ref = units.group_ref(symbol)
    unit_entity = o.Unit(id=u_ref.id, name=symbol, conversion_factor=1.0, is_ref_unit=True)
    return o.UnitGroup(id=g_ref.id, name=g_ref.name, units=[unit_entity])

unit_groups = {sym: make_unit_group(sym) for sym in ["kg", "unit"]}

# ---- Write the expanded JSON-LD directory (checked-in source of truth) ----
outdir = os.path.dirname(os.path.abspath(__file__))
ld_dir = os.path.join(outdir, "olca_ld")
entities = flows + processes + [gwp, mir, method] + list(unit_groups.values())
write_ld_dir(ld_dir, entities)

print("Wrote", ld_dir)
print("T-shirt process id:", proc_tshirt.id)
print("Method id:", method.id)
