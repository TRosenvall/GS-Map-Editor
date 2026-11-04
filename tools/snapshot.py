"""Everything the editor derives from a checkout, as JSON, so two versions can be compared.

Use it before adopting a new alchemy version, or after a refactor: snapshot the
old and the new, then diff. Results should only differ where you meant them to.

    python3 tools/snapshot.py ALCHEMY_ROOT OUT.json       # needs a built checkout
    python3 tools/snapshot.py --compare OLD.json NEW.json
"""
import sys, json, hashlib, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))


def compare(a, b):
    from collections import Counter
    counts, examples = Counter(), {}

    def note(path, kind, x, y):
        key = (path[0], str(path[-1]) if not isinstance(path[-1], int) else "#", kind)
        counts[key] += 1
        examples.setdefault(key, (path, repr(x)[:120], repr(y)[:120]))

    def walk(x, y, path):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in set(x) | set(y):
                if k not in x or k not in y:
                    note(path + [k], "only-old" if k in x else "only-new", x.get(k), y.get(k))
                else:
                    walk(x[k], y[k], path + [k])
        elif isinstance(x, list) and isinstance(y, list):
            if len(x) != len(y):
                note(path, "length", len(x), len(y))
            for i, (p, q) in enumerate(zip(x, y)):
                walk(p, q, path + [i])
        elif x != y:
            note(path, "differs", x, y)

    walk(a, b, [])
    print("differences:", sum(counts.values()))
    for key, n in counts.most_common(40):
        print(n, key, examples[key])
    return 1 if counts else 0


if sys.argv[1:2] == ["--compare"]:
    sys.exit(compare(json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))))

root, outp = sys.argv[1:3]
from gsmap.project import Project
from gsmap.scenes import Scenes
from gsmap.names import Names
from gsmap.doors import DoorEditor
from gsmap.chests import ChestEditor
from gsmap.events import EventEditor
from gsmap.connections import Connections
from gsmap.checks import Checker
from gsmap import world as W
from gsmap.setup import build_env
os.environ['PATH']=build_env()['PATH']
p=Project(root); sc=Scenes(root); n=Names(root)
d=DoorEditor(p,sc,n,stock=True); c=ChestEditor(p,sc,n,stock=True); e=EventEditor(p,sc,n,stock=True)
out={'maps':{}, 'scenes':sc.scenes}
ovs={}
for s in sc.scenes:
    try: o=sc.overlay(s['overlay'])
    except FileNotFoundError: continue
    ovs[s['overlay']]=o
out['tables']={f"{i}:{t['addr']:x}":{'kind':t['kind'],'size':t['size'],'editable':t['editable']} for i,o in ovs.items() for t in o.tables.values()}
for num,info in sorted(p.maps.items()):
    m={}
    m['bounds']=info.bounds; m['priority']=info.priority; m['char_base']=info.char_base; m['layers']=info.layers
    m['tileset']=info.tileset; m['palette']=info.palette; m['resources']=info.resources; m['alternates']=info.alternates
    try:
        m['planes']={pl:hashlib.sha1(json.dumps(p.load_grid(info,pl).cells).encode()).hexdigest() for pl in ('metatile','collision','shape')}
        m['blocks']=len(p.load_metatiles(info).rows)
        m['shape_rows']=p.shape_rows(info)
        m['markers']=[list(x) for x in p.markers(info)]
    except FileNotFoundError as ex: m['missing']=True
    if info.resources and not m.get('missing'):
        try:
            img=p.render(info); m['render']=hashlib.sha1(img.tobytes()).hexdigest()
        except Exception as ex: m['render_err']=type(ex).__name__
        try: m['chests']=c.list(info)
        except Exception as ex: m['chests_err']=repr(ex)
        try: m['doors']={str(k):v for k,v in d.list(info).items()}
        except Exception as ex: m['doors_err']=repr(ex)
        rows={r['row'] for r in [info.resources]+info.alternates if r}
        try: m['legend']={str(k):v for k,v in n.map_legend(sc.for_rows(rows),sc).items()}
        except Exception as ex: m['legend_err']=repr(ex)
        ev={}
        for s in sc.for_rows(rows):
            try:
                o=sc.overlay(s['overlay'])
                for name,t in o.tables.items():
                    if t['kind']=='events' and t['editable']:
                        r=e.describe(info,s['id'],name)
                        ev[f"{s['id']}:{t['addr']:x}"]={'events':r['events'],'people':r['people']}
                ev[f"regions:{s['id']}"]=[{k:v for k,v in x.items() if k!='table'} for x in e.regions(s['id'])]
            except Exception as ex: ev[f"err:{s['id']}"]=repr(ex)
        m['events']=ev
    out['maps'][num]=m
con=Connections(p,sc,n); out['connections']={str(k):v for k,v in con.index().items()}
w=W.World(root)
out['world']={'cells':hashlib.sha1(json.dumps(w.rows).encode()).hexdigest(),'tiles':len(w.block_tiles),'attr':hashlib.sha1(bytes(w.attr)).hexdigest(),
 'chunk':hashlib.sha1(w.render_chunk(3,3).tobytes()).hexdigest(),'walk':hashlib.sha1(w.render_walk(3,3).tobytes()).hexdigest()}
pl=W.world_places(w,p,sc,n); out['world']['places']=pl
out['checks']=[{k:v for k,v in i.items()} for i in Checker(p,sc,n)._issues(stock=True)]
json.dump(out,open(outp,'w'),indent=0,sort_keys=True,default=str)
print('maps',len(out['maps']),'tables',len(out['tables']))
