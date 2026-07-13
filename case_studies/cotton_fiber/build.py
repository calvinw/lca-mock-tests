import uuid, os, sys
import olca_schema as o
from olca_schema import units

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))
from ld_dir import write_ld_dir

def uid():
    return str(uuid.uuid4())

# ---- Flow property / unit refs (from standard olca reference data) ----
KG = dict(unit=units.unit_ref("kg"), prop=units.property_ref("kg"))
L = dict(unit=units.unit_ref("l"), prop=units.property_ref("l"))

def flow_prop_factor(prop_ref):
    return o.FlowPropertyFactor(conversion_factor=1.0, flow_property=prop_ref, is_ref_flow_property=True)

def make_product_flow(name, unit_kind):
    return o.Flow(
        id=uid(), name=name, flow_type=o.FlowType.PRODUCT_FLOW,
        category="products", flow_properties=[flow_prop_factor(unit_kind["prop"])],
    )

def make_elem_flow(name, unit_kind=KG, category="elementary flows/air"):
    return o.Flow(
        id=uid(), name=name, flow_type=o.FlowType.ELEMENTARY_FLOW,
        category=category, flow_properties=[flow_prop_factor(unit_kind["prop"])],
    )

# ---- Flows ----
fertilizer = make_product_flow("N-fertilizer", KG)
cotton = make_product_flow("Cotton fiber", KG)
co2 = make_elem_flow("CO2")
n2o = make_elem_flow("N2O")
nh3 = make_elem_flow("NH3")
water = make_elem_flow("Water", L, "elementary flows/resource/water")

flows = [fertilizer, cotton, co2, n2o, nh3, water]

def ref_to(flow):
    return o.Ref(id=flow.id, ref_type=o.RefType.Flow, name=flow.name, flow_type=flow.flow_type)

def proc_ref(p):
    return o.Ref(id=p.id, ref_type=o.RefType.Process, name=p.name)

def output_exchange(flow, unit_kind, amount, internal_id):
    return o.Exchange(
        flow=ref_to(flow), amount=amount, unit=unit_kind["unit"], flow_property=unit_kind["prop"],
        internal_id=internal_id, is_input=False, is_quantitative_reference=True,
    )

def input_exchange(flow, unit_kind, amount, provider_ref, internal_id):
    return o.Exchange(
        flow=ref_to(flow), amount=amount, unit=unit_kind["unit"], flow_property=unit_kind["prop"],
        internal_id=internal_id, is_input=True, is_quantitative_reference=False, default_provider=provider_ref,
    )

def emission_exchange(flow, amount, internal_id):
    return o.Exchange(
        flow=ref_to(flow), amount=amount, unit=KG["unit"], flow_property=KG["prop"],
        internal_id=internal_id, is_input=False, is_quantitative_reference=False,
    )

def resource_exchange(flow, unit_kind, amount, internal_id):
    return o.Exchange(
        flow=ref_to(flow), amount=amount, unit=unit_kind["unit"], flow_property=unit_kind["prop"],
        internal_id=internal_id, is_input=True, is_quantitative_reference=False,
    )

GLO = o.Ref(id=uid(), ref_type=o.RefType.Location, name="GLO")

# ---- Processes ----
proc_fertilizer = o.Process(
    id=uid(), name="Fertilizer production", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(fertilizer, KG, 1.0, 1),
        emission_exchange(co2, 3.5, 2),
    ],
)

proc_cotton = o.Process(
    id=uid(), name="Cotton farming", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(cotton, KG, 1.0, 1),
        input_exchange(fertilizer, KG, 0.2, proc_ref(proc_fertilizer), 2),
        emission_exchange(co2, 0.8, 3),
        emission_exchange(n2o, 0.015, 4),
        emission_exchange(nh3, 0.010, 5),
        resource_exchange(water, L, 8000.0, 6),
    ],
)

processes = [proc_fertilizer, proc_cotton]

product_system = o.ProductSystem(
    id=uid(), name="Cotton fiber product system",
    description="Pre-linked product system for 1 kg of cotton fiber.",
    ref_process=proc_ref(proc_cotton), ref_exchange=o.ExchangeRef(internal_id=1),
    target_amount=1.0, target_flow_property=KG["prop"], target_unit=KG["unit"],
    processes=[proc_ref(process) for process in processes],
    process_links=[
        o.ProcessLink(
            provider=proc_ref(proc_fertilizer), flow=ref_to(fertilizer),
            process=proc_ref(proc_cotton), exchange=o.ExchangeRef(internal_id=2),
        ),
    ],
)

# ---- LCIA method (four categories; CFs are the real TRACI v2.1 values
# used in the recipe-card teaching case this is modeled on, not invented
# round numbers -- see life-cycle-assessment-mcp/case_studies/cotton_fiber.md) ----
gwp = o.ImpactCategory(
    id=uid(), name="GWP", ref_unit="kg CO2-eq",
    description="climate change category for testing calculation engines only. CFs match TRACI v2.1 GWP100.",
    impact_factors=[
        o.ImpactFactor(flow=ref_to(co2), unit=KG["unit"], flow_property=KG["prop"], value=1.0),
        o.ImpactFactor(flow=ref_to(n2o), unit=KG["unit"], flow_property=KG["prop"], value=298.0),
    ],
)
ep = o.ImpactCategory(
    id=uid(), name="EP", ref_unit="kg N-eq",
    description="eutrophication category for testing calculation engines only. CF matches TRACI v2.1 EP.",
    impact_factors=[
        o.ImpactFactor(flow=ref_to(nh3), unit=KG["unit"], flow_property=KG["prop"], value=0.1186),
    ],
)
ap = o.ImpactCategory(
    id=uid(), name="AP", ref_unit="kg SO2-eq",
    description="acidification category for testing calculation engines only. CF matches TRACI v2.1 AP.",
    impact_factors=[
        o.ImpactFactor(flow=ref_to(nh3), unit=KG["unit"], flow_property=KG["prop"], value=1.88),
    ],
)
pmfp = o.ImpactCategory(
    id=uid(), name="PMFP", ref_unit="kg PM2.5-eq",
    description="particulate matter formation category for testing calculation engines only. CF matches TRACI v2.1 PMFP.",
    impact_factors=[
        o.ImpactFactor(flow=ref_to(nh3), unit=KG["unit"], flow_property=KG["prop"], value=1.0 / 15.0),
    ],
)
method = o.ImpactMethod(
    id=uid(), name="LCIA Method",
    description="LCIA method for cross-engine testing only. Not for real assessment.",
    impact_categories=[
        o.Ref(id=gwp.id, ref_type=o.RefType.ImpactCategory, name=gwp.name),
        o.Ref(id=ep.id, ref_type=o.RefType.ImpactCategory, name=ep.name),
        o.Ref(id=ap.id, ref_type=o.RefType.ImpactCategory, name=ap.name),
        o.Ref(id=pmfp.id, ref_type=o.RefType.ImpactCategory, name=pmfp.name),
    ],
)

def make_unit_group(symbol):
    u_ref = units.unit_ref(symbol)
    g_ref = units.group_ref(symbol)
    unit_entity = o.Unit(id=u_ref.id, name=symbol, conversion_factor=1.0, is_ref_unit=True)
    return o.UnitGroup(id=g_ref.id, name=g_ref.name, units=[unit_entity])

unit_groups = {sym: make_unit_group(sym) for sym in ["kg"]}

volume_group_ref = units.group_ref("m3")
volume_group = o.UnitGroup(
    id=volume_group_ref.id, name=volume_group_ref.name,
    units=[
        o.Unit(id=units.unit_ref("m3").id, name="m3", conversion_factor=1.0, is_ref_unit=True),
        o.Unit(id=units.unit_ref("l").id, name="l", conversion_factor=0.001, is_ref_unit=False),
    ],
)

# ---- Write the expanded JSON-LD directory (checked-in source of truth) ----
outdir = os.path.dirname(os.path.abspath(__file__))
ld_dir = os.path.join(outdir, "olca_ld")
entities = flows + processes + [product_system, gwp, ep, ap, pmfp, method] + list(unit_groups.values()) + [volume_group]
write_ld_dir(ld_dir, entities)

print("Wrote", ld_dir)
print("Cotton fiber process id:", proc_cotton.id)
print("Method id:", method.id)
