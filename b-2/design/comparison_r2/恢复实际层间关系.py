"""Run in Blender's Text Editor on an R2 comparison; save a copy first."""
import bpy

scene=bpy.context.scene
assert scene.get('option') in ['A','B','C','D'], '请在R2对比模型中执行'
seen=set()
for collection in scene.collection.children:
    if collection.name.startswith('F2_'):
        for obj in collection.all_objects:
            if obj.name in seen:
                continue
            seen.add(obj.name)
            dz=float(obj.get('display_explode_m',0))
            obj.location.z-=dz
            obj['display_explode_m']=0.0
scene['display_explode_m']=0.0
print('已恢复实际层间关系，可另存文件；层间高仍为暂定3.4m。')
