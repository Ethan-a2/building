"""B-2 editable design stages. Run inside Blender 3.6+ via MCP or --python.

The original b-2_model.blend is read-only input. Rebuilding replaces derivatives.
Set B2_STAGE in the execution globals to 1..5 to build one stage at a time.
This is concept geometry, not engineered construction details.
"""
import bpy
import json
import math
import subprocess
from pathlib import Path
from mathutils import Vector

ROOT = Path('/media/code/tools/building/b-2')
P = json.loads((ROOT / 'design/parameters.json').read_text(encoding='utf-8'))
MODELS, PREVIEWS = ROOT / 'models', ROOT / 'previews'
MODELS.mkdir(exist_ok=True)
PREVIEWS.mkdir(exist_ok=True)
EXPLODE = 5.0
FLOOR = P['floor_to_floor_m_assumed']
STAGES = {1: '01_site_drainage', 2: '02_two_households',
          3: '03_exposed_services', 4: '04_envelope_roof', 5: '05_future_merge'}


def enum_set(owner, prop, value):
    values = [i.identifier for i in owner.bl_rna.properties[prop].enum_items]
    if value not in values:
        raise ValueError(f'{prop}: {value} not in {values}')
    setattr(owner, prop, value)


def collection(name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def material(name, color):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.diffuse_color = (*color, 1)
    n = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    n.inputs['Base Color'].default_value = (*color, 1)
    n.inputs['Roughness'].default_value = .68
    return m


def palette():
    return {k: material('R1 / '+k, color) for k, color in {
        'wall': (.84,.82,.75), 'white': (.92,.93,.90), 'ink': (.055,.13,.18),
        'west': (.56,.73,.75), 'east': (.82,.72,.53), 'orange': (.93,.38,.09),
        'blue': (.06,.39,.72), 'teal': (.04,.61,.57), 'red': (.8,.13,.08),
        'brown': (.32,.18,.10), 'purple': (.52,.20,.64), 'soil': (.44,.40,.31),
        'road': (.30,.34,.36), 'green': (.26,.45,.27), 'roof': (.19,.24,.27),
        'insulation': (.91,.63,.25)}.items()}


def relocate(o, c):
    for old in list(o.users_collection):
        old.objects.unlink(o)
    c.objects.link(o)


def box(name, xyz, dims, mat, c, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz)
    o = bpy.context.object
    o.name = name
    o.dimensions = dims
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    relocate(o, c)
    o.data.materials.append(mat)
    if bevel:
        mod = o.modifiers.new('Edge softness', 'BEVEL')
        mod.width, mod.segments = bevel, 2
    return o


def line(name, a, b, radius, mat, c):
    d = Vector(b)-Vector(a)
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius, depth=d.length,
                                      location=(Vector(a)+Vector(b))/2)
    o = bpy.context.object
    o.name = name
    o.rotation_euler = d.to_track_quat('Z','Y').to_euler()
    relocate(o, c)
    o.data.materials.append(mat)
    o['routing_status'] = 'schematic; diameter and fall not designed'
    return o


def route(name, points, mat, c, radius=.04):
    return [line(name+f'_{i:02}', a, b, radius, mat, c)
            for i, (a,b) in enumerate(zip(points, points[1:]))]


def label(name, text, xyz, c, mat, size=.24):
    cu = bpy.data.curves.new(name, 'FONT')
    # Noto CJK's Blender font metrics render smaller than the default Bfont.
    cu.body, cu.size, cu.extrude = text, size*2.3, .001
    font_path = Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    if font_path.exists():
        cu.font = next((f for f in bpy.data.fonts if f.filepath == str(font_path)), None) or bpy.data.fonts.load(str(font_path))
    o = bpy.data.objects.new(name, cu)
    c.objects.link(o)
    o.location = xyz
    cu.materials.append(mat)
    return o


def mesh(name, vertices, faces, mat, c):
    me = bpy.data.meshes.new(name)
    me.from_pydata(vertices, [], faces)
    me.update()
    o = bpy.data.objects.new(name, me)
    c.objects.link(o)
    me.materials.append(mat)
    return o


def camera(name, loc, target, scale, c):
    data = bpy.data.cameras.new(name)
    enum_set(data, 'type', 'ORTHO')
    data.ortho_scale = scale
    o = bpy.data.objects.new(name, data)
    c.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    return o


def setup_view(target=(0,4,3), scale=29, loc=(23,-32,34)):
    s = bpy.context.scene
    c = collection('PRESENTATION_Cameras')
    s.camera = camera('R1_Stage camera', loc, target, scale, c)
    s.render.resolution_x = 1500
    s.render.resolution_y = 1500
    s.render.resolution_percentage = 100
    enum_set(s.render.image_settings, 'file_format', 'PNG')
    # Engine enum is dynamic: use accepted current engine or guarded assignment.
    try:
        s.render.engine = 'BLENDER_EEVEE'
    except TypeError:
        pass
    if hasattr(s, 'eevee'):
        s.eevee.use_gtao = True
        s.eevee.gtao_distance = 2.5
        s.eevee.gtao_factor = 1.15
        s.eevee.taa_render_samples = 64
    if s.world is None:
        s.world = bpy.data.worlds.new('R1 Studio')
    s.world.use_nodes = True
    bg = next(n for n in s.world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (.80,.85,.9,1)
    bg.inputs['Strength'].default_value = .8
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                enum_set(area.spaces.active.region_3d, 'view_perspective', 'CAMERA')
                enum_set(area.spaces.active.shading, 'color_type', 'MATERIAL')
                area.spaces.active.overlay.show_overlays = False
    return s.camera


def lights(c):
    for name, xyz, power in [('Key',(-5,-8,24),3000),('Fill',(10,8,23),2200)]:
        # Discover valid light type before creating light data.
        valid = [i.identifier for i in bpy.types.Light.bl_rna.properties['type'].enum_items]
        assert 'AREA' in valid
        d = bpy.data.lights.new('R1 '+name, type='AREA')
        d.energy, d.size = power, 12
        o = bpy.data.objects.new('R1 '+name, d)
        c.objects.link(o)
        o.location = xyz
        o.rotation_euler = (Vector((0,4,1))-o.location).to_track_quat('-Z','Y').to_euler()


def remove_object(o):
    bpy.data.objects.remove(o, do_unlink=True)


def load_scene_copy(filepath):
    """The isolated Blender process receives its input .blend on the CLI.

    Loading files inside a live MCP timer invalidates the UI context in 3.6.
    Process isolation also prevents changes to an open hand-edited scene.
    """
    if Path(bpy.data.filepath).resolve() != Path(filepath).resolve():
        raise ValueError(f'Expected preloaded input {filepath}, got {bpy.data.filepath}')
    return bpy.context.scene


def load_original():
    s = load_scene_copy(ROOT/'b-2_model.blend')
    s['revision'] = P['revision']
    s['model_status'] = 'Concept design; NOT a structural/construction drawing'
    s['survey_levels_confirmed'] = False
    return s


def build_site():
    s = load_original()
    s.name = 'R1_01 Site and drainage / SCHEMATIC'
    for o in list(bpy.data.objects):
        remove_object(o)
    enum_set(s.unit_settings, 'system', 'METRIC')
    m = palette()
    c = collection('SITE_Schematic terrain - no survey levels')
    # Simplified 1m west-east difference only; north-south drop remains unquantified.
    mesh('Indicative terrain west +1 / east 0 NOT SURVEYED',
         [(-6.3,-5,1),(6.3,-5,0),(6.3,14,0),(-6.3,14,1)],[(0,1,2,3)],m['soil'],c)
    box('West road - only confirmed external access',(-7.55,4.5,.92),(2.3,20,.16),m['road'],c)
    box('Horizontal house footprint - FFL UNSET',(0,6.5,1.18),(12.6,13,.15),m['white'],c)
    for x in [-6.3,6.3]:
        line('Boundary', (x,-5,.12 if x>0 else 1.05),(x,14,.12 if x>0 else 1.05),.025,m['ink'],c)
    label('House footprint','主体 12.6 × 13m / 室内标高待测定',(-5.7,6,1.28),c,m['ink'],.42)
    label('North strip','北侧邻居 / 1m检修退让带',(-4.8,13.35,1.3),c,m['ink'],.28)
    label('South court','南院 5m / 地坪需分级找坡',(-4.4,-3.5,1.25),c,m['ink'],.32)
    label('Road','西侧道路 / 主要人车入口',(-9.3,1,1.1),c,m['white'],.25)
    routes = collection('RAIN_Conditional routes - legal outfall TBD')
    for x,z in [(-6.0,1.4),(6.0,.38)]:
        route('Roof and strip collection',[(x,13.3,z),(x,.1,z),(x,-4.5,.4)],m['blue'],routes,.065)
    route('Court collection',[(-6,-4.5,.4),(5.65,-4.5,.4)],m['blue'],routes,.065)
    box('SE collection chamber - outlet NOT approved',(5.6,-4.45,.4),(.8,.8,.6),m['blue'],routes)
    # The return line is conditional, not a fabricated gravity fall.
    route('OPTION B pumped return only if approved',[(5.6,-4.45,.8),(-5.8,-4.45,.8),(-7,-4.45,1.3)],m['purple'],routes,.045)
    label('Drainage legend','蓝：汇水示意   紫：必要时提升回排 / 出口待确认',(-6,-6.1,1.2),routes,m['ink'],.26)
    label('Gate condition','东南门：邻地通路未确认',(3,-3.2,1.2),c,m['orange'],.23)
    label('Boundary condition','东侧邻居 / 禁止默认排水越界',(6.6,4,.4),c,m['ink'],.26)
    label('Title','01 场地、入口与排水决策',(-6,-7,1.2),c,m['ink'],.48)
    label('Disclaimer','地形仅示坡向；约1m非测绘值；基础及挡土未设计',(-6,-7.65,1.2),c,m['orange'],.27)
    box('Studio',(0,3,-.4),(100,100,.2),m['white'],c)
    lights(collection('PRESENTATION_Lights'))
    setup_view(target=(-.5,3,.5),loc=(23,-30,36),scale=28)
    s['terrain_status'] = 'simplified west-east 1m drop; N-S drop not quantified; house FFL unset'
    return {'survey_geometry': False, 'stormwater_outfall_confirmed': False, 'access_from_west': True}


def build_core():
    s = load_original()
    s.name = 'R1_02 Two floors / exploded presentation'
    m = palette()
    for c in list(s.collection.children):
        if c.name[:2] in ['02','03','04','05','06','07','08']:
            c.name = 'L1_'+c.name
    floorcol = bpy.data.collections['L1_02 Floor finishes']
    lower = bpy.data.collections['L1_03 Walls - cutaway']
    upper = bpy.data.collections['L1_04 Upper walls - enable for full height']
    infillcol = bpy.data.collections['L1_08 Removable central partition']
    annotations = bpy.data.collections.get('10 Annotations')
    annotations.hide_render = annotations.hide_viewport = True
    # Refine service spaces: enlarge bathroom 0.45m toward kitchen.
    delta = P['bathroom_south_y_m'] - 7.6
    for o in list(s.objects):
        n = o.name
        if n.startswith('Kitchen bathroom separator'):
            o.location.y += delta
        elif n.startswith('Kitchen tiled floor'):
            o.location.y = (5+P['bathroom_south_y_m'])/2
            o.dimensions.y = P['bathroom_south_y_m']-5-.16
        elif n.startswith('Bathroom tiled floor'):
            o.location.y = (P['bathroom_south_y_m']+9.1)/2
            o.dimensions.y = 9.1-P['bathroom_south_y_m']-.16
        elif n.startswith(('Kitchen base units','Kitchen worktop')):
            o.location.y, o.dimensions.y = 6.08, 1.80
        elif n.startswith('Refrigerator'):
            o.location.y = 6.67
        elif n.startswith(('Basin vanity','Washbasin')):
            o.location.y = 7.5
        if n.startswith('DEMOUNTABLE / future connection'):
            remove_object(o)
    # Rebuild optional upper panes explicitly; legacy long object names had
    # truncated suffixes, so name-based creation missed some mirrored windows.
    for o in list(upper.objects):
        if 'blue glazing' in o.name:
            remove_object(o)
    glazing = material('R1 / glazing',(.24,.57,.65))
    window_specs = [('x',0,-5.55,-2,2.7),('x',0,2,5.55,2.7)]
    window_specs += [('x',13,x-1.02,x+1.02,2.65) for x in [-4.725,-1.575,1.575,4.725]]
    for sign in [-1,1]:
        window_specs += [('y',sign*6.3,5.55,6.9,2.45),('y',sign*6.3,7.9,8.65,2.55)]
    for i,(axis,fixed,lo,hi,head) in enumerate(window_specs):
        xyz=((lo+hi)/2,fixed,.34+(1.16+head)/2) if axis=='x' else (fixed,(lo+hi)/2,.34+(1.16+head)/2)
        dims=(hi-lo-.05,.025,head-1.16) if axis=='x' else (.025,hi-lo-.05,head-1.16)
        box('Upper window pane %02d'%i,xyz,dims,glazing,upper)
    # A designed portal is to be provided here; shown wall/lintel is not a beam design.
    a, b = P['merge_opening_y_start_m'], P['merge_opening_y_start_m']+P['merge_opening_width_m_assumed']
    def wall_part(name,y0,y1,z0,z1,fill=False):
        for lo,hi,c in [(z0,min(z1,1.18),infillcol if fill else lower),
                        (max(z0,1.18),z1,upper)]:
            if hi <= lo:
                continue
            o = box(name,(0,(y0+y1)/2,.34+(lo+hi)/2),(.16,y1-y0,hi-lo),m['orange'] if fill else m['wall'],c)
            o['merge_infill'] = fill
            o['structural_status'] = 'portal framing requires structural design'
    wall_part('Central retained wall south',5.08,a,0,3.2)
    wall_part('Central retained wall north',b,9.02,0,3.2)
    wall_part('Portal head - NOT engineered beam',a,b,P['merge_opening_height_m_assumed'],3.2)
    wall_part('MERGE_INFILL',a,b,0,P['merge_opening_height_m_assumed'],True)
    lc = collection('L1_10 Chinese plan labels')
    for x,j in zip([-4.725,-1.575,1.575,4.725],range(1,5)):
        label('BED_LABEL_'+str(j),'卧室 '+str(j),(x-.53,9.42,.375),lc,m['ink'],.23)
    for x,side in [(-3.5,'西户'),(3.5,'东户')]:
        label('Living label '+side,side+'客厅 / 备用卧室',(x-1.12,.52,.375),lc,m['ink'],.21)
    for sign in [-1,1]:
        label('Kitchen label','厨房',(sign*5.1-.36,5.14,.38),lc,m['ink'],.20)
        label('Bath label','卫生间',(sign*5.1-.49,7.38,.38),lc,m['ink'],.18)
        label('Dining label','餐区',(sign*2.2-.3,7.9,.38),lc,m['ink'],.22)
    label('Entry label','公共入口',(-.53,.23,.38),lc,m['ink'],.21)
    # Duplicate architecture, fittings and labels, but NOT stairs or whole slabs.
    skip_prefixes = ('Ground floor structural slab','west household floor','east household floor','Common entrance floor','Shared front double door')
    for c in list(s.collection.children):
        if not c.name.startswith('L1_') or c.name.startswith('L1_07'):
            continue
        d = collection(c.name.replace('L1_','L2_',1))
        d.hide_render, d.hide_viewport = c.hide_render, c.hide_viewport
        d['display_explode_m'] = EXPLODE
        for src in list(c.objects):
            if src.name.startswith(skip_prefixes):
                continue
            o = src.copy()
            o.data = src.data.copy() if src.data else None
            d.objects.link(o)
            o.name = 'L2_'+src.name
            o.location.z += FLOOR+EXPLODE
            o['floor'] = 2
            o['display_explode_m'] = EXPLODE
    l2floor = bpy.data.collections['L2_02 Floor finishes']
    offset = FLOOR+EXPLODE
    # Four slab zones leave a real opening X +-1.15, Y1.62..5.
    slabs = [(-3.725,6.5,5.15,13),(3.725,6.5,5.15,13),(0,9,2.3,8),(0,.81,2.3,1.62)]
    for i,(x,y,w,d) in enumerate(slabs):
        o=box('L2_slab_zone_'+str(i),(x,y,offset+.20),(w,d,.20),m['white'],l2floor)
        o['floor']=2;o['display_explode_m']=EXPLODE
        o=box('L2_finish_zone_'+str(i),(x,y,offset+.315),(w-.02,d-.02,.03),m['west'] if x<0 else m['east'],l2floor)
        o['floor']=2;o['display_explode_m']=EXPLODE
    # Second-floor south opening becomes a window, not a door to a nonexistent balcony.
    l2walls=bpy.data.collections['L2_03 Walls - cutaway']
    box('L2_public landing south window sill',(0,0,offset+.34+.525),(1.44,.24,1.05),m['wall'],l2walls)
    l2win=bpy.data.collections['L2_05 Doors & windows']
    for x in [-.72,0,.72]:
        box('L2_landing window jamb',(x,0,offset+.34+1.775),(.045,.07,1.45),m['ink'],l2win)
    for z in [1.05,2.5]:
        box('L2_landing window rail',(0,0,offset+.34+z),(1.44,.07,.045),m['ink'],l2win)
    box('L2 landing window glazing',(0,0,offset+.34+1.775),(1.39,.025,1.45),glazing,bpy.data.collections['L2_04 Upper walls - enable for full height'])
    # Guard to the left of the arriving flight, leaving the right arrival clear.
    guard=collection('L2_07 Arrival platform guard')
    guard['display_explode_m']=EXPLODE
    for x in [-1.05,-.55,-.05]:
        line('L2 platform guard post',(x,1.62,offset+.34),(x,1.62,offset+1.44),.023,m['ink'],guard)
    line('L2 platform guard rail',(-1.05,1.62,offset+1.44),(-.05,1.62,offset+1.44),.027,m['ink'],guard)
    # Explanatory notes in the derivative .blend.
    n = bpy.data.texts.new('R1 READ ME / 设计与施工状态')
    n.write('本版详细说明见 design/设计与施工准备说明.md。\n阶段02/03/05二层为展示上移5m；实际层间高暂定3.4m。\n卫生间向南扩0.45m；中部仅1.5×2.4m连接口填充可拆。\n楼梯净宽净高、完成面、侧窗合法性、标高与排水出口待复核。\n无结构配筋或基础设计；上部墙体可通过集合开关查看。\n')
    pc=collection('PRESENTATION_Stage labels')
    label('Stage title','02 两层分户 / 未来合户接口',(-6,-6.05,.3),pc,m['ink'],.44)
    label('Exploded note','二层展示上移5m；实际层间高暂定3.4m；不从图中量总高',(-6,-6.65,.3),pc,m['orange'],.23)
    label('Site access note','西侧主要入口 / 东南门通路待确认',(-6,-7.12,.3),pc,m['ink'],.23)
    label('Floor 2 note','二层：两户 / 地暖 / 厨卫上下对位',(-6.1,-.7,offset+.35),pc,m['ink'],.27)
    s['display_explode_m'] = EXPLODE
    s['floor_to_floor_m_assumed'] = FLOOR
    s['merge_opening_m'] = [P['merge_opening_width_m_assumed'], P['merge_opening_height_m_assumed']]
    s['bathroom_y_start_m'] = P['bathroom_south_y_m']
    setup_view(target=(0,4,4.5),loc=(24,-32,31),scale=31)
    # Asset checks concern model integrity only, not code/regulation compliance.
    beds=[o for o in s.objects if 'platform' in o.name and 'Bed ' in o.name]
    assert len(beds)==8, f'Expected eight beds, found {len(beds)}'
    assert not any(o.name.startswith('L2_Shared front double door') for o in s.objects)
    assert len([o for o in s.objects if o.name.startswith('L2_slab_zone_')])==4
    infills=[o for o in s.objects if o.get('merge_infill')]
    assert len(infills)==4
    return {'bed_count':len(beds),'merge_infill_parts':len(infills),'upper_floor_slab_opening':True,
            'no_second_floor_exterior_front_door':True,'bathroom_reference_depth_m':9.1-P['bathroom_south_y_m']}


def load_core():
    return load_scene_copy(MODELS/(STAGES[2]+'.blend'))


def build_services():
    s=load_core();m=palette()
    s.name='R1_03 Exposed service routes / schematic'
    c=collection('SERVICES_Legend')
    for i,(key,body) in enumerate([('blue','蓝 给水'),('brown','棕 污水'),('red','红 采暖'),('purple','紫 电气'),('teal','青 雨水')]):
        box('Legend swatch',(7.1,2+i*.9,.4),(.3,.6,.08),m[key],c)
        label('Legend '+key,body,(7.45,1.8+i*.9,.45),c,m['ink'],.27)
    for floor in [1,2]:
        off=0 if floor==1 else FLOOR+EXPLODE
        for sign,side in [(-1,'W'),(1,'E')]:
            co=collection(f'SERVICES_F{floor}_{side}')
            x=sign*3.82
            route(f'F{floor}-{side} water',[(x,5.1,off+.65),(x,8.8,off+.65),(sign*5.4,8.8,off+.65)],m['blue'],co)
            route(f'F{floor}-{side} waste',[(sign*4.9,8.65,off+.40),(sign*5.85,8.65,off+.40),(sign*5.85,5.2,off+.40)],m['brown'],co,.06)
            route(f'F{floor}-{side} electric',[(sign*1.4,.5,off+2.6),(sign*1.4,8.85,off+2.6),(sign*5.9,8.85,off+2.6)],m['purple'],co,.025)
            box(f'F{floor}-{side} distribution board',(sign*1.4,1.9,off+1.6),(.12,.45,.55),m['purple'],co)
            box(f'F{floor}-{side} isolation valve marker',(x,5.1,off+.65),(.17,.17,.17),m['blue'],co)
            if floor==1:
                for xx,y in [(sign*3.85,.33),(sign*4.72,12.66),(sign*1.57,12.66)]:
                    box('Radiator location allowance',(xx,y,.92),(1.05,.14,.65),m['white'],co)
                    for dx in [-.4,-.2,0,.2,.4]:
                        box('Radiator fin',(xx+dx,y-.08,.92),(.035,.045,.61),m['red'],co)
                route('Radiator supply',[(sign*3.82,.36,.51),(sign*3.82,8.9,.51),(sign*5.7,8.9,.51),(sign*5.7,12.64,.51),(sign*.8,12.64,.51)],m['red'],co,.028)
            else:
                box('UFH manifold - access required',(x,6.5,off+.95),(.16,.75,.5),m['red'],co)
                # Diagram paths, deliberately sparse and tagged as non-installation layout.
                for xx,cy in [(sign*3.9,2.5),(sign*4.725,11),(sign*1.575,11)]:
                    points=[]
                    for j in range(5):
                        yy=cy-.8+j*.4
                        row=[(xx-.8,yy,off+.375),(xx+.8,yy,off+.375)]
                        points.extend(row if j%2==0 else row[::-1])
                    route('UFH SCHEMATIC NOT PIPE SPACING',points,m['red'],co,.022)
    common=collection('SERVICES_Common separate interfaces')
    box('Heat source interface ONLY - equipment location TBD',(7.4,-.4,.8),(1.05,.8,1.2),m['orange'],common)
    label('Heat source note','热源接口 / 设备位置待定',(6.6,-1.5,.3),common,m['ink'],.22)
    for sign in [-1,1]:
        # Interrupted risers document the explosion rather than pretending 8.4m storeys.
        for z0,z1 in [(.4,3.45),(FLOOR+EXPLODE+.4,FLOOR+EXPLODE+3.5)]:
            route('Vertical waste riser schematic',[(sign*5.85,8.7,z0),(sign*5.85,8.7,z1)],m['brown'],common,.07)
        route('Rain route conditional',[(sign*6.08,12.9,.25),(sign*6.08,-4.6,.25),(5.7,-4.6,.25)],m['teal'],common,.045)
    title=bpy.data.objects['Stage title'];title.data.body='03 明装管线 / 分户与公共系统'
    bpy.data.objects['Exploded note'].data.body='路线为示意；管径、坡度、回路长度、热源及合法出口待设计'
    setup_view(target=(1,4,4.5),loc=(24,-32,31),scale=32)
    return {'service_households':4,'separate_common_interfaces':True,'installation_pipe_design':False}


def collapse_second_floor():
    moved=set()
    for c in bpy.context.scene.collection.children:
        if c.name.startswith('L2_'):
            for o in c.all_objects:
                if o.name not in moved:
                    o.location.z-=EXPLODE
                    o['display_explode_m']=0.0
                    moved.add(o.name)
            c['display_explode_m']=0.0
    o=bpy.data.objects.get('Floor 2 note')
    if o:
        o.location.z-=EXPLODE
        o.hide_render=True;o.hide_viewport=True
    bpy.context.scene['display_explode_m']=0.0


def build_envelope():
    s=load_core();m=palette();collapse_second_floor()
    s.name='R1_04 Envelope and simple roof / actual storey offsets'
    for c in s.collection.children:
        if c.name.startswith(('L1_04','L2_04')):
            c.hide_render=c.hide_viewport=False
    roof=collection('ENVELOPE_Roof concept - not structural design')
    # Eaves stay inside assumed site width; all legal offsets require confirmation.
    eave,ridge=7.05,8.65
    mesh('Simple gable roof - snow and structure TBD',
         [(-6.25,0,eave),(0,0,ridge),(6.25,0,eave),(-6.25,13,eave),(0,13,ridge),(6.25,13,eave)],
         [(0,3,4,1),(1,4,5,2)],m['roof'],roof)
    for yy in [0,13]:
        mesh('Gable infill concept',[(-6.25,yy,eave),(0,yy,ridge),(6.25,yy,eave)],[(0,1,2)],m['wall'],roof)
    box('Roof thermal boundary - thickness NOT specification',(0,6.5,6.97),(12.48,12.9,.12),m['insulation'],roof)
    for x in [-6.22,6.22]:
        box('Contained eaves gutter',(x,6.5,eave-.05),(.12,13,.15),m['ink'],roof)
        route('Roof downpipe inside boundary',[(x,.25,eave-.05),(x,.25,.35)],m['teal'],roof,.055)
    # Thin diagram band stands for a continuous envelope, not insulation sizing.
    thermal=collection('ENVELOPE_Thermal continuity diagram bands')
    for z in [.45,3.55,6.83]:
        for x in [-6.27,6.27]:
            box('Thermal bridge continuity marker',(x,6.5,z),(.035,12.9,.075),m['insulation'],thermal)
    bpy.data.objects['Stage title'].data.body='04 完整外维护 / 简单双坡屋面示意'
    bpy.data.objects['Exploded note'].data.body='已恢复实际层间关系；屋面坡度、雪荷载、结构与保温厚度待设计'
    setup_view(target=(0,4,2.8),loc=(23,-32,27),scale=28)
    return {'display_explode_m':0,'roof_structurally_designed':False,'roof_and_downpipes_inside_assumed_width':True}


def build_merge():
    s=load_core();m=palette()
    s.name='R1_05 Future merge - infill removed only'
    hidden=[]
    for o in s.objects:
        if o.get('merge_infill'):
            o.hide_render=o.hide_viewport=True
            hidden.append(o.name)
    c=collection('MERGE_Future passage markers')
    for floor,off in [(1,0),(2,FLOOR+EXPLODE)]:
        box('Future connection clear path',(0,7.3,off+.365),(1.7,1.4,.025),m['teal'],c)
        label('Future passage label','预留口打开',(-.64,7.28,off+.395),c,m['white'],.21)
    bpy.data.objects['Stage title'].data.body='05 未来合户 / 仅拆指定填充'
    bpy.data.objects['Exploded note'].data.body='每层1.5m参考连接口；其余墙、梁柱、分区阀表及公共楼梯保留'
    assert len(hidden)==4
    return {'hidden_infill_parts':hidden,'structural_members_removed':False,'existing_unit_services_retained':True}


def save_stage(stage, checks):
    s=bpy.context.scene
    name=STAGES[stage]
    s['stage']=name
    s['asset_checks']=json.dumps(checks,ensure_ascii=False)
    s.render.filepath=str(PREVIEWS/(name+'.png'))
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(MODELS/(name+'.blend')))
    bpy.ops.render.render(write_still=True)
    if stage==2:
        # Hide all second floor objects for a true first-floor plan preview.
        changed=[]
        for c in s.collection.children:
            if c.name.startswith('L2_'):
                changed.append((c,c.hide_render));c.hide_render=True
        floor_note=bpy.data.objects['Floor 2 note'];floor_note.hide_render=True
        old=s.camera
        s.camera=camera('R1_Ground floor true plan',(0,4,40),(0,4,0),24,collection('PRESENTATION_Cameras'))
        s.render.filepath=str(PREVIEWS/'02_ground_plan.png')
        bpy.ops.render.render(write_still=True)
        s.camera=old;floor_note.hide_render=False
        for c,state in changed:c.hide_render=state
        s.render.filepath=str(PREVIEWS/(name+'.png'))
        bpy.ops.wm.save_as_mainfile(filepath=str(MODELS/(name+'.blend')))
    report={'stage':name,'scene':s.name,'objects':len(s.objects),'checks':checks,
            'model':str(MODELS/(name+'.blend')),'preview':str(PREVIEWS/(name+'.png'))}
    (MODELS/(name+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


def main(stage=None):
    if P['house_depth_m']+P['north_setback_m']+P['south_court_m'] != P['total_depth_m']:
        raise ValueError('North-south dimensions do not close')
    if P['width_m'] != 12.6 or P['house_depth_m'] != 13:
        raise ValueError('Base model footprint changed: remodel base explicitly, do not silently scale')
    selected = [stage] if stage else range(1,6)
    if not globals().get('B2_BASE_LOADED'):
        # Separate processes make each file reproducible and preserve the live UI.
        for i in selected:
            source = ROOT/'b-2_model.blend' if i in [1,2] else MODELS/(STAGES[2]+'.blend')
            expression = "exec(compile(open(%r, encoding='utf-8').read(), 'build_stages.py', 'exec'), {'B2_STAGE': %d, 'B2_BASE_LOADED': True})" % (str(ROOT/'scripts/build_stages.py'),i)
            subprocess.run([bpy.app.binary_path,'--background',str(source),'--python-exit-code','1','--python-expr',expression],check=True)
        return
    for i in selected:
        fn={1:build_site,2:build_core,3:build_services,4:build_envelope,5:build_merge}[i]
        checks=fn()
        save_stage(i,checks)


main(globals().get('B2_STAGE'))
