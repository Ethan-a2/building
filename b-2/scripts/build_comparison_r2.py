"""Four editable Blender comparisons, plans and quantity schedules for B-2 R2.

Run in isolated Blender background processes. Native files preserve full-height
walls, night/day south-room furniture, upper-floor display offset and routing.
No foundations, reinforcement or structural capacity are inferred.
"""
import bpy
import csv
import json
import math
import subprocess
from pathlib import Path
from mathutils import Vector

ROOT=Path('/media/code/tools/building/b-2')
CFG=json.loads((ROOT/'design/comparison_r2/options.json').read_text())
OUT=ROOT/'models/comparison_r2'
IMG=ROOT/'previews/comparison_r2'
OUT.mkdir(parents=True,exist_ok=True)
IMG.mkdir(parents=True,exist_ok=True)
F=CFG['shared_assumptions']['floor_to_floor_m']
EXP=CFG['shared_assumptions']['display_explode_m']
BASE=.30
WALL_Q=[]
OPENINGS=[]


def enum_set(owner,prop,value):
    allowed=[v.identifier for v in owner.bl_rna.properties[prop].enum_items]
    if value not in allowed:raise ValueError((prop,value,allowed))
    setattr(owner,prop,value)


def coll(name):
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c)
    return c


def mat(name,color):
    m=bpy.data.materials.new('R2 '+name);m.use_nodes=True;m.diffuse_color=(*color,1)
    n=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=.65
    return m


def init_palette():
    return {k:mat(k,v) for k,v in {'wall':(.88,.86,.8),'white':(.93,.93,.90),'west':(.56,.75,.75),'east':(.86,.75,.55),'ink':(.05,.14,.19),'wood':(.53,.35,.19),'fabric':(.21,.45,.49),'glass':(.25,.61,.7),'orange':(.94,.36,.08),'blue':(.08,.42,.7),'tile':(.65,.78,.79),'pave':(.62,.63,.58),'green':(.29,.44,.24),'road':(.30,.35,.37)}.items()}


def move(o,c):
    for old in list(o.users_collection):old.objects.unlink(o)
    c.objects.link(o)


def box(name,xyz,dims,key,c,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=xyz);o=bpy.context.object;o.name=name;o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);move(o,c);o.data.materials.append(M[key])
    if bevel:
        mod=o.modifiers.new('Rounded edges','BEVEL');mod.width=bevel;mod.segments=2
    if c.name.startswith('F2_'):o['display_explode_m']=EXP;o['floor']=2
    if c.name.startswith('F1_'):o['floor']=1
    return o


def line(name,a,b,key,c,r=.023):
    d=Vector(b)-Vector(a)
    bpy.ops.mesh.primitive_cylinder_add(vertices=10,radius=r,depth=d.length,location=(Vector(a)+Vector(b))/2)
    o=bpy.context.object;o.name=name;o.rotation_euler=d.to_track_quat('Z','Y').to_euler();move(o,c);o.data.materials.append(M[key])
    if c.name.startswith('F2_'):o['display_explode_m']=EXP;o['floor']=2
    return o


def label(name,body,xyz,c,size=.25,key='ink'):
    cu=bpy.data.curves.new(name,'FONT');cu.body=body;cu.size=size*2.3;cu.extrude=.001;cu.font=FONT
    o=bpy.data.objects.new(name,cu);c.objects.link(o);o.location=xyz;cu.materials.append(M[key])
    if c.name.startswith('F2_'):o['display_explode_m']=EXP;o['floor']=2
    return o


def offset(floor):return 0 if floor==1 else F+EXP


def wall(name,axis,fixed,start,end,floor,holes=(),external=False,infill=False):
    """Holes = (start,end,sill,head,type). All dimensions are reference geometry."""
    lo=coll(f'F{floor}_Walls_cutaway');hi=coll(f'F{floor}_Walls_upper_ENABLE_FOR_FULL_HEIGHT')
    hi.hide_render=hi.hide_viewport=True
    thickness=.24 if external else .16
    zoff=BASE+offset(floor)
    def piece(a,b,z0,z1):
        if b<=a:return
        for bottom,top,c in [(z0,min(z1,1.15),lo),(max(1.15,z0),z1,hi)]:
            if top<=bottom:continue
            xyz=((a+b)/2,fixed,zoff+(bottom+top)/2) if axis=='x' else (fixed,(a+b)/2,zoff+(bottom+top)/2)
            dims=(b-a,thickness,top-bottom) if axis=='x' else (thickness,b-a,top-bottom)
            o=box(f'F{floor}_{name}',xyz,dims,'orange' if infill else 'wall',c)
            o['merge_infill']=infill
    cursor=start
    for a,b,sill,head,kind in sorted(holes):
        if not start<=a<b<=end:raise ValueError((name,start,end,a,b))
        piece(cursor,a,0,3.2);piece(a,b,0,sill);piece(a,b,head,3.2);cursor=b
        OPENINGS.append({'floor':floor,'wall':name,'type':kind,'width_m':round(b-a,3),'height_m':round(head-sill,3)})
        if kind=='window':window(name,axis,fixed,a,b,sill,head,floor)
    piece(cursor,end,0,3.2)
    WALL_Q.append({'floor':floor,'wall':name,'external':external,'reference_length_m':round(end-start,3),'thickness_m':thickness,
                   'gross_area_m2':round((end-start)*3.2,3),'openings_area_m2':round(sum((b-a)*(h-s) for a,b,s,h,_ in holes),3),
                   'note':'参考几何，墙交接重复、梁柱占位与合同计量扣减需最终图纸调整'})


def window(name,axis,fixed,a,b,sill,head,floor):
    c=coll(f'F{floor}_Windows');zoff=BASE+offset(floor)
    def part(tag,u,z,du,dz,dep,key):
        xyz=(u,fixed,zoff+z) if axis=='x' else (fixed,u,zoff+z)
        dims=(du,dep,dz) if axis=='x' else (dep,du,dz)
        return box(f'F{floor}_{name}_{tag}',xyz,dims,key,c)
    for u in [a,(a+b)/2,b]:part('frame',u,(sill+head)/2,.045,head-sill,.07,'ink')
    for z in [sill,head]:part('rail',(a+b)/2,z,b-a,.045,.07,'ink')
    part('low_glass',(a+b)/2,(sill+min(1.13,head))/2,b-a-.05,min(1.13,head)-sill,.022,'glass')
    up=part('upper_glass',(a+b)/2,(max(1.13,sill)+head)/2,b-a-.05,head-max(1.13,sill),.022,'glass')
    move(up,coll(f'F{floor}_Walls_upper_ENABLE_FOR_FULL_HEIGHT'))


def door(name,x,y,angle,floor,width=.96):
    c=coll(f'F{floor}_Doors')
    o=box(f'F{floor}_{name}',(x+math.cos(angle)*width/2,y+math.sin(angle)*width/2,BASE+offset(floor)+1.04),(width,.045,2.08),'wood',c,.015)
    o.rotation_euler.z=angle


def furniture_bed(x,y,floor,name,wide=1.5,c=None):
    c=c or coll(f'F{floor}_Guest_furniture');z=offset(floor)
    box(name+' base',(x,y,z+.52),(wide,2,.35),'wood',c,.04)
    box(name+' mattress',(x,y,z+.76),(wide-.02,1.98,.22),'white',c,.07)
    box(name+' quilt',(x,y-.27,z+.92),(wide-.03,1.36,.13),'fabric',c,.04)
    box(name+' pillow',(x,y+.67,z+.93),(wide-.20,.42,.16),'white',c,.05)


def south_room(xmin,xmax,floor,side):
    z=offset(floor);c=coll(f'F{floor}_South_NIGHT_MODE')
    center=(xmin+xmax)/2
    furniture_bed(center,2.7,floor,f'{side} south convertible bed',1.5,c)
    box('Night side table',(center-1.05,3.25,z+.56),(.44,.45,.5),'wood',c,.025)
    d=coll(f'F{floor}_South_DAY_MODE_enable_instead_of_NIGHT');d.hide_render=d.hide_viewport=True
    box('Convertible sofa folded',(center,3.3,z+.59),(2.15,.85,.50),'fabric',d,.08)
    box('Sofa back',(center,3.62,z+.98),(2.15,.18,.6),'fabric',d,.04)
    box('Movable coffee table',(center,2.0,z+.58),(.75,.85,.12),'wood',d,.04)
    box('South clear floor',(center,2.6,z+.313),(xmax-xmin-.18,4.92,.025),'west' if side=='W' else 'east',coll(f'F{floor}_Finishes'))
    label('South mode label',('西户' if side=='W' else '东户')+'南向客厅 / 夜间床位', (xmin+.25,.32,z+.345),coll(f'F{floor}_Labels'),.22)


def stair_bounds(opt):
    if opt['stair']=='southwest':return -6.3,-3.6,0,5.2
    if opt['stair']=='southeast':return 3.6,6.3,0,5.2
    if opt['stair']=='center_north':return -1.35,1.35,opt['house_depth_m']-5.2,opt['house_depth_m']
    return -1.35,1.35,0,5.2


def stairs(opt):
    x0,x1,y0,y1=stair_bounds(opt);cx=(x0+x1)/2;north=opt['stair']=='center_north'
    c=coll('F1_Shared_staircase');direction=-1 if north else 1
    def yy(local):return y1-local if north else y0+local
    for i in range(10):
        z=BASE+(i+1)*.17
        box('Stair A tread', (cx-.61,yy(1.65+i*.28),z-.085),(1.1,.28,.17),'white',c)
        z=BASE+1.7+(i+1)*.17
        box('Stair B tread',(cx+.61,yy(4.17-i*.28),z-.085),(1.1,.28,.17),'white',c)
    box('Intermediate stair landing',(cx,yy(4.66),BASE+1.7-.09),(2.44,.7,.18),'white',c)
    for flight in [0,1]:
        xx=cx+(-.04 if flight==0 else .04)
        a=(xx,yy(1.65 if flight==0 else 4.17),BASE+(.17 if flight==0 else 1.87)+.9)
        b=(xx,yy(4.17 if flight==0 else 1.65),BASE+(1.7 if flight==0 else 3.4)+.9)
        line('Handrail',a,b,'ink',c,.025)
        for i in [0,3,6,9]:
            yl=1.65+i*.28 if flight==0 else 4.17-i*.28
            z=BASE+(i+1)*.17+(1.7 if flight else 0)
            line('Stair baluster',(xx,yy(yl),z),(xx,yy(yl),z+.9),'ink',c,.018)
    # Under-flight support volumes are conceptual, not engineered slabs.
    for xx,aa,bb in [(cx-.61,(1.55,BASE),(4.32,BASE+1.7)),(cx+.61,(4.32,BASE+1.7),(1.51,BASE+3.4))]:
        a=Vector((xx,yy(aa[0]),aa[1]));b=Vector((xx,yy(bb[0]),bb[1]));d=b-a
        o=box('Stair support NOT structural specification',(a+b)/2,(1.02,.14,d.length),'white',c);o.rotation_euler=d.to_track_quat('Z','Y').to_euler()


def slabs(opt,floor):
    dep=opt['house_depth_m'];z=offset(floor);c=coll(f'F{floor}_Slabs')
    if floor==1:pieces=[(-6.3,6.3,0,dep)]
    else:
        x0,x1,y0,y1=stair_bounds(opt)
        hole_y0,hole_y1=(y0,y1-1.51) if opt['stair']=='center_north' else (y0+1.51,y1)
        pieces=[(-6.3,x0,0,dep),(x1,6.3,0,dep),(x0,x1,0,hole_y0),(x0,x1,hole_y1,dep)]
    for i,(x0,x1,y0,y1) in enumerate(pieces):
        if x1-x0<.01 or y1-y0<.01:continue
        box(f'F{floor}_slab_zone_{i}',((x0+x1)/2,(y0+y1)/2,z+.17),(x1-x0,y1-y0,.22),'white',c)
    if floor==2:
        x0,x1,y0,y1=stair_bounds(opt);cx=(x0+x1)/2
        yy=y1-1.51 if opt['stair']=='center_north' else y0+1.51
        for x in [cx-1.05,cx-.55,cx-.05]:line('Upper platform guard',(x,yy,z+BASE),(x,yy,z+BASE+1.1),'ink',c)
        line('Upper platform guard top',(cx-1.05,yy,z+BASE+1.1),(cx-.05,yy,z+BASE+1.1),'ink',c)


def plan(opt,floor):
    dep=opt['house_depth_m'];kind=opt['stair'];z=offset(floor);x0,x1,sy0,sy1=stair_bounds(opt)
    labs=coll(f'F{floor}_Labels');finish=coll(f'F{floor}_Finishes')
    # Outer wall openings and private south entrances.
    if kind=='center_south':
        south=[(-5.65,-2.0,.72,2.65,'window'),(-.65,.65,0,2.4,'door'),(2,5.65,.72,2.65,'window')]
        if floor==2:south[1]=(-.65,.65,1.0,2.5,'window')
    else:
        south=[(-1.65,-.6,0,2.25,'door'),(.6,1.65,0,2.25,'door')]
        south += ([(-5.65,-2.0,.72,2.65,'window')] if kind!='southwest' else [(-3.30,-1.85,.72,2.65,'window')])
        south += ([(2.,5.65,.72,2.65,'window')] if kind!='southeast' else [(1.85,3.30,.72,2.65,'window')])
        if kind in ['southwest','southeast']:
            sc=(x0+x1)/2;south.append((sc-.65,sc+.65,0,2.4,'door'))
        if kind=='center_north' and floor==2:
            south=[(a,b,.72,2.65,'window') if typ=='door' else (a,b,sill,head,typ) for a,b,sill,head,typ in south]
        else:
            for x in [-1.65,.6]:door('South private door',x,0,math.pi/2,floor,1.)
    if floor==2 and kind in ['center_south','center_north']:
        assert all(h[4]!='door' for h in south), 'Upper south door requires a landing/gallery'
    wall('South facade','x',0,-6.3,6.3,floor,south,True)
    if kind in ['center_south','southwest','southeast'] and (kind!='center_south' or floor==1):
        door('Shared stair south entry',(x0+x1)/2-.65,0,math.pi/2,floor,1.25)
    # Side service windows remain modest; eastern strip is not assumed to provide good daylight.
    for sign in [-1,1]:
        wall('Side exterior','y',sign*6.3,0,dep,floor,[(5.5,6.9,1.02,2.4,'window'),(7.7,8.7,1.02,2.45,'window')],True)
    if kind=='center_north':
        rear=[(-5.7,-3.9,.78,2.6,'window'),(-2.9,-1.7,.85,2.5,'window'),(-.65,.65,0,2.4,'door'),(1.7,2.9,.85,2.5,'window'),(3.9,5.7,.78,2.6,'window')]
        if floor==2:rear[2]=(-.65,.65,1.0,2.5,'window')
        if floor==1:door('North shared stair entry',-.65,dep,-math.pi/2,floor,1.25)
    else:
        rear=[(x-1.02,x+1.02,.78,2.6,'window') for x in [-4.725,-1.575,1.575,4.725]]
    wall('North facade','x',dep,-6.3,6.3,floor,rear,True)
    # Shared staircase enclosure; corner variants use gallery, never pass through a private unit.
    if kind=='center_north':
        for xx in [x0,x1]:
            wall('North stair side','y',xx,sy0,sy1,floor,[(dep-1.45,dep-.4,0,2.25,'door')])
            door('Private entry from north stair',xx,dep-1.45,math.pi if xx<0 else 0,floor,1.)
        wall('North stair south enclosure','x',sy0,x0,x1,floor)
        wall('Central south divider','y',0,0,opt['merge_y_start_m'],floor)
        wall('Central divider above connection','y',0,opt['merge_y_start_m']+1.5,sy0,floor)
        west_bounds,east_bounds=(-6.3,0),(0,6.3)
    else:
        for xx in [x0,x1]:
            if abs(xx)==6.3:continue
            holes=[(.4,1.45,0,2.25,'door')] if kind=='center_south' else []
            wall('South stair side','y',xx,0,5.2,floor,holes)
            if holes:door('Private entry from common stair',xx,.4,math.pi if xx<0 else 0,floor,1.)
        wall('Stair north enclosure','x',5.2,x0,x1,floor)
        if kind=='center_south':west_bounds,east_bounds=(-6.3,-1.35),(1.35,6.3)
        elif kind=='southwest':west_bounds,east_bounds=(-3.6,0),(0,6.3)
        else:west_bounds,east_bounds=(-6.3,0),(0,3.6)
        if kind!='center_south':wall('Central living divider','y',0,0,5.2,floor)
        wall('Central middle south','y',0,5.2,opt['merge_y_start_m'],floor)
        wall('Central middle north','y',0,opt['merge_y_start_m']+1.5,dep,floor)
    wall('MERGE_INFILL','y',0,opt['merge_y_start_m'],opt['merge_y_start_m']+1.5,floor,[(opt['merge_y_start_m'],opt['merge_y_start_m']+1.5,0,2.4,'future connection')])
    # Fill only the future portal; upper lintel above remains ordinary retained wall.
    for bottom,top,c in [(0,1.15,coll(f'F{floor}_MERGE_INFILL')), (1.15,2.4,coll(f'F{floor}_Walls_upper_ENABLE_FOR_FULL_HEIGHT'))]:
        o=box('Removable acoustic infill',(0,opt['merge_y_start_m']+.75,z+BASE+(bottom+top)/2),(.12,1.5,top-bottom),'orange',c);o['merge_infill']=True
    south_room(*west_bounds,floor,'W');south_room(*east_bounds,floor,'E')
    # Service strips and wide connections from south living to dining.
    for sign in [-1,1]:
        a,b=sorted([sign*6.3,sign*3.7])
        wall('Kitchen south partition','x',5.2,a,b,floor)
        wall('Kitchen bathroom partition','x',7.3,a,b,floor)
        wall('Service corridor side','y',sign*3.7,5.2,9.2,floor,[(5.5,6.5,0,2.2,'door'),(7.65,8.65,0,2.2,'door')])
        for y in [5.5,7.65]:door('Service door',sign*3.7,y,math.pi if sign<0 else 0,floor,.95)
        k=coll(f'F{floor}_Kitchen_bath_furniture')
        box('Kitchen floor',(sign*5,6.25,z+.313),(2.42,1.94,.025),'tile',finish)
        box('Bath floor',(sign*5,8.25,z+.313),(2.42,1.74,.025),'tile',finish)
        box('Kitchen standard cabinet',(sign*5.79,6.25,z+.76),(.64,1.75,.88),'white',k,.02)
        box('Kitchen worktop',(sign*5.79,6.25,z+1.22),(.7,1.80,.07),'wood',k,.025)
        box('Sink',(sign*5.79,6.70,z+1.27),(.46,.48,.04),'ink',k,.03)
        box('Hob',(sign*5.79,5.80,z+1.27),(.48,.48,.04),'ink',k,.02)
        box('Fridge',(sign*4.18,6.82,z+1.18),(.63,.63,1.75),'white',k,.03)
        box('Shower tray',(sign*5.73,8.6,z+.37),(.86,.87,.12),'white',k,.025)
        box('Toilet',(sign*4.33,8.60,z+.62),(.45,.66,.57),'white',k,.10)
        box('Toilet tank',(sign*4.33,8.9,z+.86),(.47,.20,.75),'white',k,.05)
        box('Basin',(sign*5.20,7.68,z+.99),(.64,.4,.21),'white',k,.035)
        label('Kitchen label','厨房',(sign*5.1-.32,5.29,z+.345),labs,.20)
        label('Bath label','卫生间',(sign*5.1-.45,7.4,z+.345),labs,.18)
        # Dining is off the main passage and outside the future connection footprint.
        box('Dining table',(sign*2.35,6.20,z+1.0),(1.15,1.3,.1),'wood',coll(f'F{floor}_Dining'),.04)
        for yy in [5.35,7.05]:box('Dining chair',(sign*2.35,yy,z+.70),(.45,.45,.10),'fabric',coll(f'F{floor}_Dining'),.025)
    # Guest bedrooms: D trades the two inner north bedrooms for private entry foyers.
    if kind=='center_north':
        for sign in [-1,1]:
            a,b=sorted([sign*6.3,sign*3.4])
            hole=(-4.1,-3.1) if sign<0 else (3.1,4.1)
            # Use an entry in the inward vertical partition, not outside the room span.
            wall('D guest south partition','x',9.2,a,b,floor)
            wall('D guest inward partition','y',sign*3.4,9.2,dep,floor,[(9.5,10.5,0,2.2,'door')])
            door('Guest bedroom door',sign*3.4,9.5,math.pi if sign<0 else 0,floor,.95)
            furniture_bed(sign*4.85,dep-1.48,floor,'North guest',1.35)
            box('Guest timber floor',(sign*4.85,(dep+9.2)/2,z+.313),(2.67,dep-9.2-.18,.025),'wood',finish)
            label('Guest label','北客卧',(sign*4.85-.46,9.38,z+.345),labs,.22)
            label('Private foyer','户内玄关',(sign*2.3-.5,dep-1.85,z+.345),labs,.21)
            box('Private foyer floor',(sign*2.38,(dep+9.2)/2,z+.313),(1.85,dep-9.2-.15,.025),'west' if sign<0 else 'east',finish)
    else:
        wall('North bedroom front','x',9.2,-6.3,6.3,floor,[(-4.1,-3.1,0,2.2,'door'),(-1.4,-.4,0,2.2,'door'),(.4,1.4,0,2.2,'door'),(3.1,4.1,0,2.2,'door')])
        for xx in [-3.15,3.15]:wall('North bedroom divider','y',xx,9.2,dep,floor)
        for xx in [-4.725,-1.575,1.575,4.725]:
            furniture_bed(xx,dep-1.52,floor,'North guest',1.5)
            box('Guest timber floor',(xx,(dep+9.2)/2,z+.313),(2.96,dep-9.2-.18,.025),'wood',finish)
            label('Guest label','北客卧',(xx-.47,9.4,z+.345),labs,.21)
        for xx in [-4.1,-1.4,.4,3.1]:door('North guest door',xx,9.2,math.pi/2,floor,.95)
    # Explicit public/private floor markings at stair arrival.
    landing_y=dep-.79 if kind=='center_north' else .79
    box('Common landing floor',((x0+x1)/2,landing_y,z+.314),(2.43,1.30,.028),'pave',finish)
    label('Common stair label','公共楼梯',((x0+x1)/2-.55,landing_y-.38,z+.35),labs,.23)


def gallery(opt):
    if opt['stair'] not in ['southwest','southeast']:return
    c=coll('F2_Added_south_common_gallery');z=F+EXP
    a,b=(-5.7,1.75) if opt['stair']=='southwest' else (-1.75,5.7)
    box('Gallery slab NOT engineered section',((a+b)/2,-.725,z+.17),(b-a,1.25,.22),'white',c)
    box('Gallery clear walking strip',((a+b)/2,-.725,z+.314),(b-a-.1,1.15,.025),'orange',c)
    for x in [a,a+(b-a)/3,a+2*(b-a)/3,b]:
        line('Gallery railing post',(x,-1.35,z+.30),(x,-1.35,z+1.40),'ink',c,.025)
        # Ground supports stay at actual levels in their own collection.
        box('Gallery support placeholder',(x,-1.35,F/2+.17),(.15,.15,F),'ink',coll('F1_Gallery_supports_NOT_structural_design'))
    line('Gallery guard rail',(a,-1.35,z+1.4),(b,-1.35,z+1.4),'ink',c,.028)
    for x in [a,b]:line('Gallery end guard',(x,-1.35,z+1.4),(x,-.1,z+1.4),'ink',c,.028)
    label('Gallery note','新增公共连廊 / 净宽与结构待复核',(a+.15,-1.20,z+.36),c,.21)
    canopy=coll('F2_Gallery_weather_cover_ENABLE');canopy.hide_render=canopy.hide_viewport=True
    box('Required weather cover concept',((a+b)/2,-.77,z+3.0),(b-a+.15,1.4,.10),'glass',canopy)


def site(opt):
    c=coll('SITE_Confirmed_rectangles_and_concept_approaches');dep=opt['house_depth_m']
    box('House and yard presentation base',(0,4.5,-.01),(12.85,19.3,.18),'ink',c,.03)
    box('South court 5m',(0,-2.5,.12),(12.6,5,.10),'pave',c)
    box('North setback',(0,(dep+14)/2,.12),(12.6,14-dep,.10),'pave',c)
    box('East 0.5m setback OUTSIDE building',(6.55,6.5,.12),(.5,13,.10),'tile',c)
    box('West road schematic',(-7.45,4.5,.05),(2,19,.08),'road',c)
    # A survey-placeholder triangle only: not accepted cadastral geometry.
    tc=coll('SITE_NW_TRIANGLE_SURVEY_PLACEHOLDER')
    pts=[(-6.3,dep,.23),(-6.3,dep+2,.23),(-3.3,dep,.23)]
    for a,b in zip(pts,pts[1:]+pts[:1]):line('Approx NW triangle border',a,b,'orange',tc,.034)
    label('Triangle note','西北三角地约3×2m / 轮廓待测',(-8.3,15.3,.24),tc,.24,'orange')
    label('Triangle caveat','仅示位置尺度，不用于布置楼梯或报价土方',(-8.3,14.8,.24),tc,.20)
    # Existing west vehicle entrance stays in the south court for every option.
    for y in [-4.7,-1.4]:box('West gate post',(-6.3,y,.9),(.20,.2,1.55),'ink',c)
    line('West access arrow',(-7.8,-3.05,.23),(-5.55,-3.05,.23),'orange',c,.055)
    label('West gate','西侧院门 / 人车共用',(-6.0,-4.64,.24),c,.23)
    for x in [-6.3,6.3]:
        if x>0:box('Court east boundary',(x,-2.5,.65),(.16,5,1.05),'wall',c)
    box('South boundary',(-1.4,-5,.65),(9.8,.16,1.05),'wall',c)
    for x in [3.6,5.95]:box('SE gate conditional',(x,-5,.9),(.22,.22,1.55),'ink',c)
    label('SE gate note','东南外门通路待确认',(3.15,-4.75,.25),c,.20)
    box('Simple screen wall deferred',(4.8,-3.55,.83),(2.3,.16,1.4),'wall',c)
    # Vehicle is an envelope, not a turning-track verification.
    box('Car envelope 4.6 x 1.8',(-3.40,-3.2,.69),(4.6,1.8,.9),'west',c,.22)
    box('Car cabin',(-3.45,-3.2,1.25),(2.35,1.56,.55),'glass',c,.18)
    label('Car note','车位示意 / 转弯需实车复核',(-5.55,-2.0,.24),c,.20)
    if opt['stair']=='center_north':
        box('Northwest pedestrian approach',(-2.5,13.25,.20),(7.6,1.35,.07),'orange',c)
        line('Northwest pedestrian direction',(-7.3,13.3,.32),(-.15,13.3,.32),'blue',c,.045)
        line('North entry direction',(-.15,13.3,.32),(-.15,12.6,.32),'blue',c,.045)
        label('North approach','西北到达 → 北侧入梯 / 预留1.5m带',(-5.7,13.58,.27),c,.22)
        canopy=coll('SITE_D_North_weather_cover_ENABLE');canopy.hide_render=canopy.hide_viewport=True
        box('North approach cover concept',(-2.48,13.25,2.75),(7.65,1.5,.08),'glass',canopy)
    label('East setback','东侧0.5m退让',(6.92,5,.24),c,.23)
    label('North marker','北 N',(7.0,12.0,.24),c,.35)
    line('North arrow',(7.25,10.7,.24),(7.25,11.8,.24),'ink',c,.04)
    label('Width dimension','建筑外宽 12.60m',(-2.1,-5.65,.24),c,.30)
    line('Depth reference line',(-8.6,0,.24),(-8.6,dep,.24),'ink',c,.012)
    for yy in [0,dep]:line('Depth dimension tick',(-8.75,yy,.24),(-8.45,yy,.24),'ink',c,.014)
    depth_text=label('Depth dimension',f'主体进深 {dep:.2f}m',(-8.85,3.5,.24),c,.28)
    depth_text.rotation_euler.z=math.pi/2
    label('Title',opt['id']+' / '+opt['name'],(-6.1,-6.7,.23),c,.44)
    label('Subtitle','南向起居睡眠 / 夜间模式 · 二层展示上移5m · 非施工图',(-6.1,-7.3,.23),c,.23)
    box('Studio ground',(0,3,-.22),(150,150,.12),'white',c)


def cam(name,xyz,target,scale):
    c=coll('PRESENTATION');d=bpy.data.cameras.new(name);enum_set(d,'type','ORTHO');d.ortho_scale=scale
    o=bpy.data.objects.new(name,d);c.objects.link(o);o.location=xyz;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();return o


def lighting():
    s=bpy.context.scene;c=coll('PRESENTATION')
    for xyz,energy in [((-7,-8,28),3400),((13,9,25),2300)]:
        assert 'AREA' in [i.identifier for i in bpy.types.Light.bl_rna.properties['type'].enum_items]
        d=bpy.data.lights.new('Softbox','AREA');d.energy=energy;d.size=12;o=bpy.data.objects.new('Softbox',d);c.objects.link(o);o.location=xyz;o.rotation_euler=(Vector((0,4,2))-o.location).to_track_quat('-Z','Y').to_euler()
    s.world=bpy.data.worlds.new('R2 studio');s.world.use_nodes=True
    bg=next(n for n in s.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.83,.87,.91,1);bg.inputs['Strength'].default_value=.75
    try:s.render.engine='BLENDER_EEVEE'
    except TypeError:pass
    if hasattr(s,'eevee'):
        s.eevee.use_gtao=True;s.eevee.gtao_distance=2;s.eevee.gtao_factor=1.2;s.eevee.taa_render_samples=64
    s.render.resolution_x=1600;s.render.resolution_y=1600;s.render.resolution_percentage=100
    enum_set(s.render.image_settings,'file_format','PNG')


def quantities(opt):
    house=12.6*opt['house_depth_m'];stair=2.7*5.2;gallery_area=opt['gallery_length_m']*opt['gallery_width_m']
    south_widths={'A':[4.95,4.95],'B':[3.6,6.3],'C':[6.3,3.6],'D':[6.3,6.3]}[opt['id']]
    q={'id':opt['id'],'name':opt['name'],'building_width_m':12.6,'house_depth_m':opt['house_depth_m'],
       'north_setback_m':opt['north_setback_m'],'south_court_m':5,'dimension_chain_m':opt['house_depth_m']+opt['north_setback_m']+5,
       'body_projection_per_floor_m2':round(house,2),'body_projection_two_floors_m2':round(house*2,2),
       'stair_reference_footprint_per_floor_m2':round(stair,2),'upper_gallery_reference_area_m2':round(gallery_area,2),
       'upper_gallery_length_m':opt['gallery_length_m'],'upper_gallery_reference_width_m':opt['gallery_width_m'],
       'north_approach_cover_option_m2':11.475 if opt['id']=='D' else 0,
       'south_living_reference_widths_W_E_m':south_widths,'north_guest_rooms_per_floor':opt['guest_rooms_per_floor'],
       'south_convertible_rooms_per_floor':2,'structural_design_complete':False,
       'common_area_note':'楼梯参考投影已包含在主体投影内，禁止另加；连廊单列，正式建筑面积按当地计量规则核算',
       'wall_reference_gross_area_two_floors_m2':round(sum(r['gross_area_m2'] for r in WALL_Q),2),
       'wall_opening_area_two_floors_m2':round(sum(r['openings_area_m2'] for r in WALL_Q),2),
       'window_reference_area_two_floors_m2':round(sum(r['width_m']*r['height_m'] for r in OPENINGS if r['type']=='window'),2),
       'objects':len(bpy.context.scene.objects)}
    (OUT/f'{opt["id"]}_quantities.json').write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for suffix,rows in [('walls_reference',WALL_Q),('openings_reference',OPENINGS)]:
        with (OUT/f'{opt["id"]}_{suffix}.csv').open('w',encoding='utf-8-sig',newline='') as f:
            wr=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');wr.writeheader();wr.writerows(rows)
    return q


def render_views(opt):
    s=bpy.context.scene;id=opt['id'];s.camera=cam('01 Two floor exploded',(25,-35,35),(0,4,4.5),33)
    ax=s.camera;plan_cam=cam('02 Plan north up',(0,4,45),(0,4,0),25)
    for sc in bpy.data.screens:
        for a in sc.areas:
            if a.type=='VIEW_3D':
                enum_set(a.spaces.active.region_3d,'view_perspective','CAMERA');enum_set(a.spaces.active.shading,'color_type','MATERIAL');a.spaces.active.overlay.show_overlays=False
    s['display_explode_m']=EXP;s['actual_floor_to_floor_m']=F;s['option']=id;s['design_status']=CFG['status']
    note=bpy.data.texts.new('READ ME / R2对比与编辑')
    note.write('详见 design/comparison_r2/方案对比与报价说明.md。\n默认二层展示上移5m，不可直接量总高。\n将所有F2_集合对象Z减5m可恢复实际层间关系（每对象仅一次），同时更改自定义偏移属性。\n南向客厅默认夜间床位，切换F*_South_DAY_MODE与F*_South_NIGHT_MODE查看日间。\n上部墙体默认隐藏，可开启F*_Walls_upper。连廊/北通道雨棚概念单独隐藏，报价需计入适当防雨雪措施。\n楼梯2.7×5.2m、20级、3.4m层间高为待校核尺寸，无基础、挡土、配筋、构件规格及施工放样设计。\n')
    bpy.context.preferences.filepaths.save_version=0
    s.render.filepath=str(IMG/f'{id}_axon.png');bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'{id}_comparison.blend'))
    bpy.ops.render.render(write_still=True)
    # First floor: omit the upper floor, preserve site and staircase.
    saved=[]
    for c in s.collection.children:
        if c.name.startswith('F2_'):saved.append((c,c.hide_render));c.hide_render=True
    s.camera=plan_cam;s.render.filepath=str(IMG/f'{id}_floor1.png');bpy.ops.render.render(write_still=True)
    for c,v in saved:c.hide_render=v
    saved=[]
    for c in s.collection.children:
        if c.name.startswith('F1_') and c.name!='F1_Shared_staircase':saved.append((c,c.hide_render));c.hide_render=True
    s.render.filepath=str(IMG/f'{id}_floor2.png');bpy.ops.render.render(write_still=True)
    for c,v in saved:c.hide_render=v
    s.camera=ax;s.render.filepath=str(IMG/f'{id}_axon.png');bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'{id}_comparison.blend'))


def build(id):
    global M,FONT
    opt=next(o for o in CFG['options'] if o['id']==id)
    assert opt['house_depth_m']+opt['north_setback_m']+5==19
    # Each child is a fresh background Blender process; no live user scene is changed.
    for o in list(bpy.data.objects):bpy.data.objects.remove(o,do_unlink=True)
    for c in list(bpy.data.collections):bpy.data.collections.remove(c)
    s=bpy.context.scene;s.name='B2_R2_'+id+'_'+opt['name'];enum_set(s.unit_settings,'system','METRIC')
    M=init_palette();FONT=bpy.data.fonts.load('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    site(opt)
    for floor in [1,2]:slabs(opt,floor);plan(opt,floor)
    stairs(opt);gallery(opt);lighting();q=quantities(opt);render_views(opt)
    print('R2_COMPLETE',json.dumps(q,ensure_ascii=False),flush=True)


if globals().get('R2_CHILD'):
    build(globals()['R2_OPTION'])
else:
    for id in ['A','B','C','D']:
        expression="exec(compile(open(%r,encoding='utf-8').read(),'build_comparison_r2.py','exec'),{'R2_CHILD':True,'R2_OPTION':%r})"%(str(ROOT/'scripts/build_comparison_r2.py'),id)
        subprocess.run([bpy.app.binary_path,'--background','--factory-startup','--python-exit-code','1','--python-expr',expression],check=True)
