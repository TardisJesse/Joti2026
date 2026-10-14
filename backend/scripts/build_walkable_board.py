"""Build the 2026 v3 board from public OSM paths and the supplied duck list."""
import copy
import hashlib
import heapq
import json
import math
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET
import openpyxl

DATA = Path(__file__).parents[1] / 'app/data'
HQ = (51.94281191, 4.3553432)

def distance(a, b):
    lat = math.radians((a[0]+b[0])/2)
    return math.hypot((a[0]-b[0])*111195, (a[1]-b[1])*111195*math.cos(lat))

def shortest(graph, start):
    costs = {start: 0}; queue = [(0, start)]
    while queue:
        cost, node = heapq.heappop(queue)
        if cost != costs[node]: continue
        for other, length in graph[node].items():
            total = cost + length
            if total < costs.get(other, math.inf):
                costs[other] = total; heapq.heappush(queue, (total, other))
    return costs

root = ET.parse(DATA / 'allart_walk_network.osm').getroot()
nodes = {int(n.attrib['id']): (float(n.attrib['lat']), float(n.attrib['lon'])) for n in root.findall('node')}
blocked = {int(n.attrib['id']) for n in root.findall('node') if any(t.attrib.get('k') == 'access' and t.attrib.get('v') in ('no', 'private') for t in n.findall('tag'))}
graph = {}; ways = {}; path_nodes = set()
for way in root.findall('way'):
    tags = {t.attrib['k']: t.attrib['v'] for t in way.findall('tag')}
    highway = tags.get('highway')
    if highway not in ('footway', 'path', 'pedestrian', 'living_street', 'residential', 'service', 'cycleway', 'unclassified', 'steps'): continue
    if tags.get('foot') in ('no', 'private') or (tags.get('access') in ('no', 'private') and tags.get('foot') not in ('yes', 'designated', 'permissive')): continue
    if tags.get('service') in ('driveway', 'parking_aisle'): continue
    refs = [int(n.attrib['ref']) for n in way.findall('nd')]
    for a, b in zip(refs, refs[1:]):
        if a not in nodes or b not in nodes or a in blocked or b in blocked: continue
        length = distance(nodes[a], nodes[b])
        graph.setdefault(a, {})[b] = length; graph.setdefault(b, {})[a] = length
        for node in (a,b): ways.setdefault(node, set()).add(int(way.attrib['id']))
        if highway in ('footway', 'path', 'pedestrian'): path_nodes.update((a,b))
start = min(graph, key=lambda n: distance(HQ, nodes[n]))
hq_offset = distance(HQ, nodes[start])
costs = shortest(graph, start)
# Every point is reached by an actual connected route, with a 100 m allowance.
candidates = [n for n in path_nodes if n in costs and costs[n]+hq_offset <= 1100 and 51.9367 <= nodes[n][0] <= 51.9458 and 4.347 <= nodes[n][1] <= 4.3592]
chosen = [min(candidates, key=lambda n: distance(HQ, nodes[n]))]
routes = [shortest(graph, chosen[0])]
while len(chosen) < 46:
    eligible = [n for n in candidates if n not in chosen and all(r.get(n, math.inf) <= 1800 for r in routes)]
    node = max(eligible, key=lambda n: min(distance(nodes[n], nodes[x]) for x in chosen))
    chosen.append(node); routes.append(shortest(graph, node))
minimum_spacing = min(distance(nodes[a], nodes[b]) for i,a in enumerate(chosen) for b in chosen[i+1:])
assert minimum_spacing > 45, minimum_spacing
# Convex hull around the selected path nodes, padded to include activation zones.
points = sorted({(round(nodes[n][1]+dx/68500,7),round(nodes[n][0]+dy/111195,7)) for n in chosen+[start] for dx in (-50,50) for dy in (-50,50)})
def cross(o,a,b): return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
lower=[]; upper=[]
for target, seq in ((lower,points),(upper,reversed(points))):
    for p in seq:
        while len(target)>=2 and cross(target[-2],target[-1],p)<=0: target.pop()
        target.append(p)
ring = lower[:-1]+upper[:-1]; ring.append(ring[0])
old = json.loads((DATA/'allart_joti_2026_compact_v2.json').read_text(encoding='utf-8'))
rows = list(openpyxl.load_workbook(r'C:/Users/jesse/Downloads/nfc-serienummers-eenden.xlsx', read_only=True, data_only=True)['Serienummers'].values)[5:25]
ducks = [{'number':r[0], 'name':r[1], 'nfc_serial_hash':hashlib.sha256(''.join(r[2].split()).lower().encode()).hexdigest()} for r in rows]
assert [d['number'] for d in ducks] == list(range(1,21))
assert len({d['nfc_serial_hash'] for d in ducks}) == 20
pack = {k:copy.deepcopy(old[k]) for k in ('hq','sources')}
pack.update(version='allart-joti-2026-walkable-v3', map_timestamp='2026-10-14', play_area={'type':'Polygon','coordinates':[ring]}, boards=[])
pack['sources'].append('https://api.openstreetmap.org/api/0.6/map?bbox=4.345,51.935,4.361,51.947')
pack['walking'] = {'speed_kmh':4, 'route_allowance_m':100, 'max_from_hq_m':math.ceil(max(costs[n]+hq_offset for n in chosen))+100, 'max_between_points_m':math.ceil(max(r.get(n,math.inf) for r in routes for n in chosen))+100, 'minimum_point_spacing_m':round(minimum_spacing,1), 'meaning':'Walking time excludes searching, solving activities and visiting every point. Routes follow the downloaded public OSM walking network.'}
for board in old['boards']:
    result = {k:copy.deepcopy(v) for k,v in board.items() if k!='objects'}; result['objects']=[]
    for i, point in enumerate(board['objects']):
        p = copy.deepcopy(point); n=chosen[i]
        p.update(id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{pack['version']}:{board['key']}:{i}")), latitude=nodes[n][0], longitude=nodes[n][1], activation_radius_meters=20, osm_node_id=n, osm_way_ids=sorted(ways[n]), walk_from_hq_m=math.ceil(costs[n]+hq_offset)+100)
        if p['type']=='SCANNER_POINT': p['name'] = 'S1 Scanner Parkradar' if p['name'].startswith('S1 ') else 'S2 Scanner Allart-radar'
        result['objects'].append(p)
    for i, duck in enumerate(ducks):
        n=chosen[26+i]
        result['objects'].append({'id':str(uuid.uuid5(uuid.NAMESPACE_URL,f"{pack['version']}:{board['key']}:duck:{duck['number']}")), 'type':'PHYSICAL_DUCK','name':f"Eend {duck['number']} · {duck['name']}", 'description':'Zoek het fysieke eendje. Druk op SCAN NFC en houd je telefoon tegen de tag. Werkt NFC niet? Vul het nummer op het eendje in (1 t/m 20). Je team krijgt de beloning eenmaal per eendje.', 'latitude':nodes[n][0], 'longitude':nodes[n][1], 'activation_radius_meters':20, 'reward_points':50, 'duck_number':duck['number'], 'nfc_serial_hash':duck['nfc_serial_hash'], 'osm_node_id':n, 'osm_way_ids':sorted(ways[n]), 'walk_from_hq_m':math.ceil(costs[n]+hq_offset)+100})
    pack['boards'].append(result)
(DATA/'allart_joti_2026_walkable_v3.json').write_text(json.dumps(pack,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# Save only the relevant routing graph, retaining public source provenance.
network = {'source':pack['sources'][-1], 'hq_node_id':start, 'hq_offset_m':hq_offset, 'nodes':{str(n):nodes[n] for n in graph}, 'edges':[[a,b,w] for a,adj in graph.items() for b,w in adj.items() if a<b]}
(DATA/'allart_walk_routes.json').write_text(json.dumps(network,separators=(',',':')),encoding='utf-8')
print(json.dumps(pack['walking'], indent=2));print('46 objects per main round, including 20 ducks. Area:',ring)
