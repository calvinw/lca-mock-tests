import uuid, os, zipfile, shutil
import olca_schema as o
from olca_schema import units
from olca_schema.zipio import ZipWriter

def uid():
    return str(uuid.uuid4())

# ---- Flow property / unit refs (from standard olca reference data) ----
KG = dict(unit=units.unit_ref("kg"), prop=units.property_ref("kg"))
KWH = dict(unit=units.unit_ref("kWh"), prop=units.property_ref("kWh"))
TKM = dict(unit=units.unit_ref("tkm"), prop=units.property_ref("tkm"))
UNIT = dict(unit=units.unit_ref("unit"), prop=units.property_ref("unit"))

def flow_prop_factor(prop_ref):
    return o.FlowPropertyFactor(conversion_factor=1.0, flow_property=prop_ref, is_ref_flow_property=True)

def make_product_flow(name, unit_kind):
    f = o.Flow(
        id=uid(),
        name=name,
        flow_type=o.FlowType.PRODUCT_FLOW,
        category="Mock products",
        flow_properties=[flow_prop_factor(unit_kind["prop"])],
    )
    return f

def make_elem_flow(name):
    f = o.Flow(
        id=uid(),
        name=name,
        flow_type=o.FlowType.ELEMENTARY_FLOW,
        category="Mock elementary flows/air",
        flow_properties=[flow_prop_factor(KG["prop"])],
    )
    return f

# ---- Flows ----
electricity = make_product_flow("Mock Electricity", KWH)
steel = make_product_flow("Mock Steel", KG)
transport = make_product_flow("Mock Transport service", TKM)
widget = make_product_flow("Mock Widget", UNIT)
co2 = make_elem_flow("Mock CO2")
ch4 = make_elem_flow("Mock CH4")

flows = [electricity, steel, transport, widget, co2, ch4]

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
proc_electricity = o.Process(
    id=uid(), name="Mock Electricity production", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(electricity, KWH, 1.0),
        emission_exchange(co2, 0.5),
    ],
)

proc_transport = o.Process(
    id=uid(), name="Mock Transport service", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(transport, TKM, 1.0),
        emission_exchange(co2, 0.1),
    ],
)

proc_steel = o.Process(
    id=uid(), name="Mock Steel production", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(steel, KG, 1.0),
        input_exchange(electricity, KWH, 2.0, proc_ref(proc_electricity)),
        emission_exchange(co2, 1.0),
    ],
)

proc_widget = o.Process(
    id=uid(), name="Mock Widget production", process_type=o.ProcessType.UNIT_PROCESS,
    location=GLO,
    exchanges=[
        output_exchange(widget, UNIT, 1.0),
        input_exchange(steel, KG, 3.0, proc_ref(proc_steel)),
        input_exchange(transport, TKM, 5.0, proc_ref(proc_transport)),
        emission_exchange(ch4, 0.02),
    ],
)

processes = [proc_electricity, proc_transport, proc_steel, proc_widget]

# ---- Mock LCIA method ----
cat = o.ImpactCategory(
    id=uid(), name="Mock GWP", ref_unit="kg Mock-CO2-eq",
    description="Mock impact category for testing calculation engines only.",
    impact_factors=[
        o.ImpactFactor(flow=ref_to(co2), unit=KG["unit"], flow_property=KG["prop"], value=1.0),
        o.ImpactFactor(flow=ref_to(ch4), unit=KG["unit"], flow_property=KG["prop"], value=10.0),
    ],
)
method = o.ImpactMethod(
    id=uid(), name="Mock LCIA Method",
    description="Mock LCIA method for cross-engine testing only. Not for real assessment.",
    impact_categories=[o.Ref(id=cat.id, ref_type=o.RefType.ImpactCategory, name=cat.name)],
)

# ---- Write zip ----
outdir = "/home/claude/mock_lca"
zpath = os.path.join(outdir, "mock_lca.zip")
if os.path.exists(zpath):
    os.remove(zpath)
with ZipWriter(zpath) as zw:
    for f in flows:
        zw.write(f)
    for p in processes:
        zw.write(p)
    zw.write(cat)
    zw.write(method)

print("Wrote", zpath)
print("Widget process id:", proc_widget.id)
print("Mock GWP category id:", cat.id)
print("Mock GWP method id:", method.id)

# Save ids for later use
with open(os.path.join(outdir, "ids.txt"), "w") as fh:
    fh.write(f"widget_process={proc_widget.id}\n")
    fh.write(f"method_id={method.id}\n")
    fh.write(f"category_id={cat.id}\n")

# ---- Minimal unit groups (conversion_factor=1.0 for each, so no rescaling) ----
def make_unit_group(symbol):
    u_ref = units.unit_ref(symbol)
    g_ref = units.group_ref(symbol)
    unit_entity = o.Unit(id=u_ref.id, name=symbol, conversion_factor=1.0, is_ref_unit=True)
    return o.UnitGroup(id=g_ref.id, name=g_ref.name, units=[unit_entity])

unit_groups = {sym: make_unit_group(sym) for sym in ["kg", "kWh", "tkm", "unit"]}

with ZipWriter(zpath) as zw:
    for ug in unit_groups.values():
        zw.write(ug)

print("Added unit groups:", list(unit_groups.keys()))
