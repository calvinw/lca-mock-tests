import uuid, os, sys
import olca_schema as o
from olca_schema import units

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))
from ld_dir import write_ld_dir

def uid():
    return str(uuid.uuid4())

# ---- Flow property / unit refs (from standard olca reference data) ----
KG = dict(unit=units.unit_ref("kg"), prop=units.property_ref("kg"))

def flow_prop_factor(prop_ref):
    return o.FlowPropertyFactor(conversion_factor=1.0, flow_property=prop_ref, is_ref_flow_property=True)

def make_product_flow(name, unit_kind):
    return o.Flow(
        id=uid(), name=name, flow_type=o.FlowType.PRODUCT_FLOW,
        category="Mock products", flow_properties=[flow_prop_factor(unit_kind["prop"])],
    )

def make_elem_flow(name):
    return o.Flow(
        id=uid(), name=name, flow_type=o.FlowType.ELEMENTARY_FLOW,
        category="Mock elementary flows/air", flow_properties=[flow_prop_factor(KG["prop"])],
    )

# ---- Flows ----
fertilizer = make_product_flow("Mock N-fertilizer", KG)
cotton = make_product_flow("Mock Cotton fiber", KG)
co2 = make_elem_flow("Mock CO2")
n2o = make_elem_flow("Mock N2O")
nh3 = make_elem_flow("Mock NH3")

flows = [fertilizer, cotton, co2, n2o, nh3]

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
proc_fertilizer = o.Process(
    id=uid(), name="Mock Fertilizer production", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(fertilizer, KG, 1.0),
        emission_exchange(co2, 3.0),
    ],
)

proc_cotton = o.Process(
    id=uid(), name="Mock Cotton farming", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(cotton, KG, 1.0),
        input_exchange(fertilizer, KG, 0.2, proc_ref(proc_fertilizer)),
        emission_exchange(co2, 1.0),
        emission_exchange(n2o, 0.1),
        emission_exchange(nh3, 0.1),
    ],
)

processes = [proc_fertilizer, proc_cotton]

# ---- Mock LCIA method (two categories, like the real cotton_fiber teaching case) ----
gwp = o.ImpactCategory(
    id=uid(), name="Mock GWP", ref_unit="kg Mock-CO2-eq",
    description="Mock climate change category for testing calculation engines only.",
    impact_factors=[
        o.ImpactFactor(flow=ref_to(co2), unit=KG["unit"], flow_property=KG["prop"], value=1.0),
        o.ImpactFactor(flow=ref_to(n2o), unit=KG["unit"], flow_property=KG["prop"], value=10.0),
    ],
)
ep = o.ImpactCategory(
    id=uid(), name="Mock EP", ref_unit="kg Mock-N-eq",
    description="Mock eutrophication category for testing calculation engines only.",
    impact_factors=[
        o.ImpactFactor(flow=ref_to(nh3), unit=KG["unit"], flow_property=KG["prop"], value=1.0),
    ],
)
method = o.ImpactMethod(
    id=uid(), name="Mock LCIA Method",
    description="Mock LCIA method for cross-engine testing only. Not for real assessment.",
    impact_categories=[
        o.Ref(id=gwp.id, ref_type=o.RefType.ImpactCategory, name=gwp.name),
        o.Ref(id=ep.id, ref_type=o.RefType.ImpactCategory, name=ep.name),
    ],
)

def make_unit_group(symbol):
    u_ref = units.unit_ref(symbol)
    g_ref = units.group_ref(symbol)
    unit_entity = o.Unit(id=u_ref.id, name=symbol, conversion_factor=1.0, is_ref_unit=True)
    return o.UnitGroup(id=g_ref.id, name=g_ref.name, units=[unit_entity])

unit_groups = {sym: make_unit_group(sym) for sym in ["kg"]}

# ---- Write the expanded JSON-LD directory (checked-in source of truth) ----
outdir = os.path.dirname(os.path.abspath(__file__))
ld_dir = os.path.join(outdir, "olca_ld")
entities = flows + processes + [gwp, ep, method] + list(unit_groups.values())
write_ld_dir(ld_dir, entities)

print("Wrote", ld_dir)
print("Cotton fiber process id:", proc_cotton.id)
print("Method id:", method.id)
