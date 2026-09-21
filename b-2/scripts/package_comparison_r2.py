"""Create a printable local HTML booklet, contact sheets and an editable quote CSV."""
from pathlib import Path
from html import escape
import csv
import json
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'design/comparison_r2'
IMAGES=ROOT/'previews/comparison_r2'
OPTIONS=json.loads((OUT/'options.json').read_text())['options']
QUANTITIES={o['id']:json.loads((ROOT/f'models/comparison_r2/{o["id"]}_quantities.json').read_text()) for o in OPTIONS}
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'


def contacts(kind):
    canvas=Image.new('RGB',(2400,2690),'#eef2f2');d=ImageDraw.Draw(canvas)
    big=ImageFont.truetype(FONT,43);small=ImageFont.truetype(FONT,25)
    names={'floor1':'一层平面对比','floor2':'二层平面对比','axon':'两层空间对比'}
    d.text((40,25),'B-2 / R2  '+names[kind],font=big,fill='#183642')
    d.text((40,90),'建筑外宽12.6m；每户南向客厅兼备用卧室；同尺度对比；非施工放样图',font=small,fill='#536873')
    for i,o in enumerate(OPTIONS):
        x=(i%2)*1200;y=145+(i//2)*1260
        im=Image.open(IMAGES/f'{o["id"]}_{kind}.png').convert('RGB');im.thumbnail((1160,1160))
        canvas.paste(im,(x+20,y+55))
        d.text((x+28,y),o['id']+' / '+o['name'],font=ImageFont.truetype(FONT,32),fill='#183642')
        q=QUANTITIES[o['id']]
        s=f'主体两层{q["body_projection_two_floors_m2"]}㎡｜南房开间 西/东 {q["south_living_reference_widths_W_E_m"][0]}/{q["south_living_reference_widths_W_E_m"][1]}m'
        d.text((x+28,y+1200),s,font=small,fill='#183642')
    canvas.save(IMAGES/f'compare_{kind}.png')


def quote_csv():
    rows=[
      ['主体两层投影（估算基数）','㎡',*[QUANTITIES[i]['body_projection_two_floors_m2'] for i in 'ABCD'],'','','','','','楼梯参考投影已包含；不是结构结算工程量'],
      ['楼梯参考范围（不另加主体面积）','㎡/层',14.04,14.04,14.04,14.04,'','','','','','用于核对公共面积；楼梯本体按专项图报价'],
      ['二层南公共连廊参考投影','㎡',0,9.3125,9.3125,0,'','','','','','含不含支承基础连接排水另列，实际净宽待复核'],
      ['连廊屋盖参考投影','㎡',0,10.64,10.64,0,'','','','','','按模型屋盖7.60×1.40估算，正式构造后复核'],
      ['北侧到达雨棚条件项','㎡',0,0,0,11.475,'','','','','','D参考7.65×1.50，须确认边界和雨雪处理'],
      ['南院地面参考面积','㎡',63,63,63,63,'','','','','','实际铺装按分期及沟井扣减'],
      ['北侧退让带参考面积','㎡',12.6,12.6,12.6,18.9,'','','','','','D包含公共到达路线，不能全按花池报价'],
      ['北侧独立客卧','间/层',4,4,4,2,'','','','','','采光需复核；南起居睡眠房另各2间/层'],
      ['窗洞参考面积（非成品下单量）','㎡',*[QUANTITIES[i]['window_reference_area_two_floors_m2'] for i in 'ABCD'],'','','','','','统一性能报价，安装密封纱窗配件范围写清'],
      ['合户填充（两层）','㎡',7.2,7.2,7.2,7.2,'','','','','','两层各1.5×2.4；结构洞口及饰面另协调'],
    ]
    for item,note in [
        ('测量与设计','建筑结构楼梯排水专项范围'),('土方回填挡土','须现场测量；高差不可从平面模型估算'),
        ('基础与主体结构','正式结构图后计算；不得按概念板厚配筋报价'),('楼梯及公共栏杆','净宽净高扶手平台防滑'),
        ('连廊完整支承系统','B/C注明材料基础梁柱连接和安装'),('屋面完整系统','保温防水找坡雨水收口和防雪'),
        ('外墙保温与门窗收口','统一系统性能和梁柱窗边节点'),('分户给水与污水','四户及公共分区检修通气'),
        ('室外雨水与合法接驳','重力或提升按实测出口条件分别暂列'),('电气与公共照明','四户容量公共通道及室外防护'),
        ('一层散热器','按房间热负荷和分户控制'),('二层地暖','分集水器回路保温试验和养护'),
        ('供暖热源','能源条件与设备位置待定'),('湿区防水及基础洁具','每层两户标准统一'),
        ('基础装修与明装线槽','统一墙地面标准不要用装修差价掩盖布局差价'),('北通道雨雪与安防','D排水防滑照明及必要围护'),
        ('暂列与未包含项','逐项列明，避免重复计价'),('合计与工期','填各方案合计，附计算方式和有效期')]:
        rows.append([item,'项','','','','','','','','','',note])
    headers=['分项','单位','A数量','B数量','C数量','D数量','统一单价或差异说明','A金额','B金额','C金额','D金额','计量与范围备注']
    with (OUT/'四方案分项报价表.csv').open('w',encoding='utf-8-sig',newline='') as f:
        wr=csv.writer(f,lineterminator='\n');wr.writerow(headers);wr.writerows(rows)


def booklet():
    css='''@page{size:A3 landscape;margin:10mm}*{box-sizing:border-box}body{margin:0;background:#e6ebed;color:#183642;font-family:"Noto Sans CJK SC","Microsoft YaHei",sans-serif}section{width:400mm;min-height:275mm;margin:8mm auto;padding:10mm;background:white;page-break-after:always}section:last-child{page-break-after:auto}h1{font-size:28px;margin:0 0 12px}h2{font-size:24px;margin:0 0 12px}.muted{color:#5a707b;font-size:14px}table{width:100%;border-collapse:collapse;font-size:15px}td,th{border:1px solid #b9c7cc;padding:9px;text-align:left}th{background:#e4eeef}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.plan{width:100%;height:205mm;object-fit:contain}.hero{width:100%;height:210mm;object-fit:contain}.callout{padding:14px;background:#edf4f3;border-left:5px solid #248c87;line-height:1.8}.warn{background:#fff1de;padding:12px;line-height:1.7}li{margin:10px 0;line-height:1.6}p{line-height:1.7}footer{margin-top:12px;font-size:12px;color:#607681}@media print{body{background:white}section{margin:0;padding:0;min-height:0;height:275mm;overflow:hidden}}'''
    html=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>B-2 R2 四方案报价比选册</title><style>'+css+'</style><body>']
    html.append('<section><h1>B-2 农村两层住宅｜四方案比选与询价</h1><p class="muted">R2 · 2026-09-20 · 建筑外宽12.6m固定 · 退让在建筑外 · 每户南向客厅兼备用卧室</p>')
    html.append('<div class="callout"><b>建议优先比较 A 与 D。</b> A作为公共交通集中、施工较简单的基线；D释放南向空间，但必须解决北侧到达及雨雪防护。B/C把角部楼梯所需的二层连廊完整画出，方便核算真实差价。</div><br><table><tr><th>比较项</th>'+''.join('<th>'+o['id']+' '+escape(o['name'])+'</th>' for o in OPTIONS)+'</tr>')
    data=[('主体进深 / 北带',['13 / 1m','13 / 1m','13 / 1m','12.5 / 1.5m']),('两层主体投影',['327.6㎡','327.6㎡','327.6㎡','315㎡']),('每层南向房参考开间 西/东',['4.95 / 4.95m','3.6 / 6.3m','6.3 / 3.6m','6.3 / 6.3m']),('北侧独立客卧 / 每层',['4间','4间','4间','2间']),('二层南公共连廊',['无','约9.31㎡','约9.31㎡','无']),('主要代价',['楼梯仍占南向','西户南房缩小、连廊费用','东户南房缩小、连廊费用','北侧通行、防雨雪、客卧减少'])]
    for name,values in data:html.append('<tr><th>'+name+'</th>'+''.join('<td>'+v+'</td>' for v in values)+'</tr>')
    html.append('</table><h2 style="margin-top:24px">统一报价口径</h2><ul><li>主体投影内已经包含楼梯范围，不再重复加面积；连廊单列。</li><li>同样的屋面、保温、门窗和基础装修标准；一层散热器、二层地暖，四户独立控制。</li><li>土方、基础、结构、排水出口和设备容量待现场及专项图确定，未知项明确暂列。</li><li>所有尺寸为概念参考，非放样尺寸；图中二层展开上移5m只是展示。</li></ul><div class="warn">西北三角地约3×2m仅作尺度提示，真实轮廓和权属未测定；不能认定可放常规双跑楼梯。东南楼梯从自家南院进入，不以南邻提供通路为前提。</div><footer>配套：方案对比与报价说明.md、四方案分项报价表.csv、4个可编辑.blend及每方案一层/二层/轴测PNG。</footer></section>')
    for o in OPTIONS:
        id=o['id'];q=QUANTITIES[id]
        html.append('<section><h1>'+id+' / '+escape(o['name'])+'｜一层与二层</h1><p class="muted">南在下、北在上。橙色为合户填充或新增公共路线；南房显示夜间床展开状态。宽度为参考范围，净宽另扣墙、扶手和饰面。</p><div class="grid">')
        for floor in [1,2]:html.append(f'<div><h2>{floor}F / {"一层" if floor==1 else "二层"}</h2><img class="plan" src="../../previews/comparison_r2/{id}_floor{floor}.png"></div>')
        html.append('</div><footer>'+escape(o['note'])+'</footer></section>')
        html.append('<section><h1>'+id+' / '+escape(o['name'])+'｜空间关系与新增项目</h1><div class="grid"><div><img class="hero" src="../../previews/comparison_r2/'+id+'_axon.png"></div><div>')
        html.append('<h2>报价核对卡</h2><table>')
        for key,val in [('两层主体投影',str(q['body_projection_two_floors_m2'])+'㎡'),('楼梯参考范围','2.7×5.2m / 层；已计入主体'),('二层南连廊',str(round(q['upper_gallery_reference_area_m2'],2))+'㎡'),('北侧到达雨棚条件项',str(round(q['north_approach_cover_option_m2'],2))+'㎡'),('每层南向房','2间，日间客厅 / 夜间床位'),('每层北侧独立客卧',str(q['north_guest_rooms_per_floor'])+'间'),('两层合户封堵填充','2处 × 1.5×2.4m')]:html.append('<tr><th>'+key+'</th><td>'+val+'</td></tr>')
        html.append('</table><p>'+escape(o['note'])+'</p><h2>请施工方填写</h2><p>方案总估价：____________________</p><p>主体及基础：____________________</p><p>新增公共交通及防护：____________</p><p>防水保温、门窗：________________</p><p>水电采暖及基础装修：____________</p><p>不含项目 / 暂列项：______________</p><p>工期与报价有效期：______________</p><div class="warn">连廊及北通道屋盖在剖切图中默认隐藏，报价不得遗漏适当防雨雪、排水、防滑和防护。图中梁板、柱、栏杆只表达位置，不代表结构规格。</div></div></div><footer>Blender文件：models/comparison_r2/'+id+'_comparison.blend。上部墙、日夜家具、屋盖均为独立可切换集合。</footer></section>')
    html.append('</body></html>')
    (OUT/'报价比选册.html').write_text('\n'.join(html),encoding='utf-8')


for kind in ['floor1','floor2','axon']:contacts(kind)
quote_csv();booklet()
# Canonical line endings keep checked-in CSV bytes consistent with SHA-256 manifests.
for path in (ROOT/'models/comparison_r2').glob('*.csv'):
    with path.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.reader(f))
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        csv.writer(f,lineterminator='\n').writerows(rows)
print('R2 package: three contact sheets, quote CSV and A3 landscape printable HTML (9 pages).')
