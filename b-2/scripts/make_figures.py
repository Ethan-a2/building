"""Generate editable Chinese SVG diagrams with only the Python standard library."""
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'design' / 'figures'
OUT.mkdir(parents=True, exist_ok=True)
INK, BLUE, TEAL, ORANGE, GRAY = '#193747', '#3977ae', '#268b87', '#cf7531', '#667780'


class Sheet:
    def __init__(self, title, subtitle, height=700):
        self.height = height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}">',
                      '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#193747"/></marker></defs>',
                      f'<rect width="1200" height="{height}" fill="#f5f7f7"/>',
                      '<style>text{font-family:"Noto Sans CJK SC","Microsoft YaHei",sans-serif;fill:#193747} .small{font-size:17px}</style>']
        self.text(40, 51, title, 29)
        self.text(40, 85, subtitle, 17, GRAY)

    def text(self, x, y, body, size=20, color=INK):
        for i, line in enumerate(body.split('\n')):
            self.parts.append(f'<text x="{x}" y="{y+i*(size+9)}" font-size="{size}" style="fill:{color}">{escape(line)}</text>')

    def rect(self, x, y, w, h, fill='#fff', stroke='#b5c5ca', r=8):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')

    def line(self, x1, y1, x2, y2, color=BLUE, width=3, arrow=False, dash=False):
        self.parts.append(f'<path d="M{x1} {y1}L{x2} {y2}" fill="none" stroke="{color}" stroke-width="{width}"' + (' marker-end="url(#arrow)"' if arrow else '') + (' stroke-dasharray="9 7"' if dash else '') + '/>')

    def box(self, x, y, w, h, title, lines='', fill='#fff'):
        self.rect(x, y, w, h, fill)
        self.text(x+16, y+31, title, 22)
        if lines:
            self.text(x+16, y+65, lines, 18, GRAY)

    def save(self, name):
        self.text(40, self.height-22, 'B-2 · R1 / 概念深化与施工交底准备 · 图示不替代测量、结构和专项设计', 15, GRAY)
        (OUT / (name+'.svg')).write_text('\n'.join(self.parts+['</svg>']), encoding='utf-8')


s=Sheet('01 / 场地与入口', '北朝上；东西面宽12.6m固定；南北1+13+5=19m暂定', 840)
s.rect(205,130,600,605,'#fff',INK)
s.rect(205,130,600,33,'#dfeadc');s.text(360,153,'北退让1m / 检修、排水',18)
s.rect(205,163,600,414,'#e5eef0');s.text(340,350,'两层主体 12.6 × 13m',27)
s.rect(205,577,600,158,'#eee8da');s.text(370,610,'南院5m',23)
s.rect(70,130,95,605,'#d1d9dc');s.text(84,200,'西侧\n道路\n\n北高\n↓\n南低',22)
s.line(160,650,300,650,TEAL,5,True);s.text(212,694,'主要人车入口',18)
s.rect(653,678,112,10,INK);s.text(650,667,'影壁可延期',17)
s.line(720,775,720,740,ORANGE,4,True,True);s.text(840,724,'东南门：\n先确认通路权属',20,ORANGE)
s.text(360,120,'北侧邻居',20);s.text(835,350,'东侧邻居',20);s.text(380,780,'南侧邻居：不能默认有路',20)
s.line(170,420,835,650,BLUE,4,True,True);s.text(841,470,'坡向示意\n西高东低\n约1m高差\n待实测标高',20,BLUE)
s.rect(787,708,28,28,'#3977ae');s.text(840,650,'东南集水点\n≠合法排放口',20,BLUE)
s.save('01_site')

s=Sheet('02 / 高差、地坪与入口', '只表达关系；±0.000、回填高度、挡土尺寸必须由现场测量与设计确定')
s.line(70,430,1120,550,GRAY,5);s.text(70,400,'西侧道路（较高）');s.text(880,595,'东南低点（约低1m）')
s.rect(300,260,500,160,'#e7eef0');s.line(300,420,800,420,TEAL,8);s.text(350,330,'主体室内完成面：保持水平',24)
s.text(352,390,'基础与地基另设计；不以松填土承载',18)
s.line(130,425,290,425,ORANGE,5);s.text(90,470,'优先平顺接入',19,ORANGE)
s.line(800,435,950,450,BLUE,4,True);s.line(950,450,950,500,GRAY,5);s.line(950,500,1100,525,BLUE,4,True)
s.text(815,205,'院地可分级；围墙不默认挡土',21)
s.box(50,120,225,165,'先测量','道路面 / 沟底\n宅地四角 / 邻墙脚\n合法接入口管底')
s.box(55,545,660,90,'轮椅几何校核','1m高差 × 12 = 约12m坡段，尚未计平台；5m院深不够直接消化。','#fff0de')
s.save('02_levels')

s=Sheet('03 / 雨污排放决策', '东南最低不代表允许向邻居排水；重力、提升方案以出口条件为前提', 760)
s.box(45,130,300,120,'雨水收集','屋面 / 院子 / 北检修带','#e8f2f7')
s.box(45,280,300,110,'沉砂、清掏节点','道路侧防倒灌；防冻维护')
s.box(45,430,300,110,'东南可检修集水点','容量、溢流后果待核算','#e8f2f7')
s.line(190,250,190,280,BLUE,3,True);s.line(190,390,190,430,BLUE,3,True)
s.line(345,475,430,475,BLUE,3,True)
s.box(430,140,350,130,'A 合法低位出口存在','重力排水\n管底、坡度、回水条件核算','#e2f0e9')
s.box(430,330,350,150,'B 合法出口需要提升','集水坑 + 泵 + 报警\n考虑停电、冻堵和应急蓄水','#fff0de')
s.box(430,545,350,115,'C 无合法出口','先协调出口与权属\n不擅排邻地、不默认渗井','#f7e7e2')
s.line(402,475,402,205,BLUE,2);s.line(402,205,430,205,BLUE,2,True)
s.line(402,405,430,405,BLUE,2,True);s.line(402,475,402,600,BLUE,2);s.line(402,600,430,600,BLUE,2,True)
s.box(825,170,325,360,'污水独立系统','厨卫 → 立管 → 检查井\n\n市政污水或合规处理设施\n\n化粪池需清掏通路\n尾水去向另行确定\n\n严禁与雨水随意混接','#eee8e3')
s.save('03_drainage')

s=Sheet('04 / 推荐平面分区', '墙参考线尺寸；家具、门净宽、楼梯净高和轮椅实际回转另复核', 890)
x0,y0,k=240,145,40
def plan_rect(x,y,w,h,fill):s.rect(x0+x*k,y0+(13-y-h)*k,w*k,h*k,fill,INK,0)
plan_rect(0,0,12.6,13,'#edf3f2')
for x in [0,3.15,6.3,9.45]:
    plan_rect(x,9.1,3.15,3.9,'#e6d8bd');s.text(x0+(x+.45)*k,y0+70,'卧室',22)
for x in [0,10.35]:
    plan_rect(x,5,2.25,2.15,'#d5e8ee');plan_rect(x,7.15,2.25,1.95,'#c7dee8')
    s.text(x0+(x+.4)*k,y0+208,'卫生间',17);s.text(x0+(x+.55)*k,y0+285,'厨房',18)
plan_rect(5.15,0,2.3,5,'#d7dce0')
s.text(260,585,'西户客厅\n兼备用卧室',21);s.text(565,585,'东户客厅\n兼备用卧室',21)
s.text(450,548,'共用\n楼梯',22)
s.text(365,377,'餐区',21);s.text(568,377,'餐区',21)
s.line(x0+6.3*k,y0+3.9*k,x0+6.3*k,y0+8*k,INK,5)
s.line(x0+6.3*k,y0+(13-8.05)*k,x0+6.3*k,y0+(13-6.55)*k,ORANGE,9)
s.text(795,345,'中部预留连接口\n1.50m × 2.40m\n其余墙保留',22,ORANGE)
s.line(750,365,505,373,ORANGE,2,True)
s.text(55,220,'北卧室\n3.90m',21);s.text(55,365,'中部厨卫餐区\n4.10m',21);s.text(55,570,'南起居区\n5.00m',21)
s.text(400,125,'面宽 12.60m',24)
s.line(485,725,485,667,TEAL,4,True);s.text(380,766,'南院 → 共用入口 → 左右分户',21)
s.text(790,485,'每层两户\n两层厨卫对位\n北侧各户两卧室',22)
s.text(790,635,'卫生间借厨房0.45m\n仍需按实际洁具复核\n不是完整轮椅卫生间',20,GRAY)
s.save('04_plan')

s=Sheet('05 / 两层叠合与公共楼梯', '层间高3.4m暂定；完成面厚度影响首末级；爆炸模型不是实际建筑高度')
for yy,title,heat in [(140,'二层 / 两户','地暖：每户分集水器'),(390,'一层 / 两户','散热器：每户支路')]:
    s.box(60,yy,420,180,title+' 西户','厨卫叠合 / 独立入口\n'+heat,'#e3eff0')
    s.box(720,yy,420,180,title+' 东户','厨卫叠合 / 独立入口\n'+heat,'#f0e8d9')
    s.rect(500,yy,200,180,'#dce1e3');s.text(540,yy+45,'公共平台',22)
    s.line(540,yy+90,475,yy+90,TEAL,3,True);s.line(660,yy+90,725,yy+90,TEAL,3,True)
s.line(600,480,600,320,ORANGE,7,True);s.text(605,365,'楼梯',21,ORANGE)
s.text(70,625,'上下对位：结构 / 厨卫 / 立管；合户时两层各开中部预留口，楼梯继续使用。',22)
s.save('05_stack')

s=Sheet('06 / 低成本合户接口', '仅拆指定非承重填充；梁柱及洞口边构件须先做结构设计')
for xx,title,closed in [(70,'分户阶段',True),(665,'未来合户',False)]:
    s.text(xx,150,title,26)
    s.rect(xx,210,440,260,'#dce1e0',INK,0)
    s.rect(xx+120,280,200,190,'#f5f7f7',INK,0)
    s.rect(xx+95,245,250,35,'#839da5',INK,0)
    if closed:s.rect(xx+125,285,190,185,'#e9ae7b',ORANGE,0)
    s.text(xx+112,510,'参考净连接宽1.50m',20)
    s.text(xx+10,565,'管线绕开填充区\n上下层洞口对应；不临时凿梁柱',19)
s.line(530,370,640,370,ORANGE,5,True)
s.text(190,330,'非承重\n隔声填充',23);s.text(800,350,'拆填充\n修饰面',23)
s.save('06_merge')

s=Sheet('07 / 四户与公共设备分开', '明装在线管/线槽内；管道在保温边界内；路线可检修、可隔离', 730)
s.box(40,140,235,430,'总接口','总进水 / 总供电\n\n雨污分开\n\n热源待定\n\n网络接入\n\n最终容量按四户核算','#e2eaed')
for yy,label in [(140,'F2-W 二层西'),(250,'F2-E 二层东'),(360,'F1-W 一层西'),(470,'F1-E 一层东')]:
    s.box(375,yy,350,85,label,'户阀 / 计量条件 / 配电 / 温控')
    s.line(280,yy+40,375,yy+40,TEAL,3,True)
s.box(790,140,365,185,'公共单独回路','楼梯与院灯 / 院门\n排水泵（如采用）\n公共用水','#fff0de')
s.box(790,365,365,195,'明装路径','服务侧墙 / 顶角\n避开门窗和未来连接口\n不混槽、不裸露电线\n阀门与清扫口可触及')
s.text(65,638,'独立分户 ≠ 必须四套外部表；正式开户条件由供水供电方确认，户内分表可另设计。',20)
s.save('07_services')

s=Sheet('08 / 一层暖气、二层地暖', '先计算热负荷，再定热源、末端、流量、管径与水力平衡')
s.box(40,250,250,160,'热源接口','能源与设备位置待定\n不默认放在楼梯间','#e5ecef')
s.box(400,125,325,180,'一层两户散热器','分户支路与房间调节\n明装供回水\n按选定温度确定散热量','#f8e8da')
s.box(400,380,325,180,'二层两户地暖','分户分集水器\n回路、间距、流量待设计\n试压、养护、逐步升温','#f8e8da')
s.line(290,300,400,215,ORANGE,5,True);s.line(290,360,400,460,ORANGE,5,True)
s.box(790,145,360,355,'温度协调比较','方案1\n末端均按低温供水选型\n\n方案2\n地暖混水及独立控制\n\n由热源、负荷、末端决定\n不是两种末端直接乱并联')
s.text(60,625,'空置户需要防冻策略；明装水管仍在室内保温边界内；地暖厚度纳入楼梯标高。',20)
s.save('08_heating')

s=Sheet('09 / 屋面、保温和雨雪', '阶段04只示意简单双坡；坡度、结构、雪荷载、材料与节点未定')
s.rect(180,310,760,200,'#e6eef0',INK,0)
s.line(145,305,560,140,INK,10);s.line(560,140,975,305,INK,10)
s.line(180,325,940,325,ORANGE,12);s.text(340,366,'冷屋顶示意：顶层水平保温边界',22,ORANGE)
s.line(175,335,175,508,ORANGE,8);s.line(945,335,945,508,ORANGE,8)
s.line(300,250,155,310,BLUE,4,True);s.line(820,250,965,310,BLUE,4,True)
s.line(155,315,155,545,BLUE,5,True);s.line(965,315,965,545,BLUE,5,True)
s.text(25,590,'天沟和落水管在自家范围内 → 合法雨水系统；不向邻居或入口落水、落雪。',23)
s.text(380,445,'结构构件、保温厚度另设计\n屋面检修与防风固定一起考虑',23)
s.text(810,130,'另比价：简单低坡屋面\n比较完整系统，不只比瓦或卷材',18)
s.save('09_roof')

s=Sheet('10 / 地面防潮与墙脚', '构造功能示意；具体层次、材料和厚度由地基、地坪和热工设计确定')
for y,h,c,t in [(230,48,'#ddc39e','地面饰面与基层'),(278,55,'#ece1bd','按设计设置地面保温/设备层'),(333,20,'#5b9eac','连续防潮构造'),(353,75,'#bdcbd0','结构地坪/稳定基层'),(428,65,'#b5aa90','毛细水阻断与分层压实基层')]:
    s.rect(90,y,650,h,c,INK,0);s.text(115,y+h*.65,t,20)
s.rect(740,140,130,353,'#dae0dd',INK,0)
s.line(90,340,805,340,BLUE,7);s.line(750,340,750,290,BLUE,7)
s.line(870,380,1100,420,TEAL,5,True)
s.text(875,460,'室外找坡排水\n不得覆盖墙脚防潮层',20)
s.text(860,215,'墙身防潮连续\n管根与门口收头',20,BLUE)
s.text(70,570,'地下水条件异常时：普通防潮层不能替代设计防水、地基处理及必要的抗浮措施。',21)
s.save('10_ground')

s=Sheet('11 / 改善型卫生间与适老预留', '参考净尺寸约2.05×1.79m；不是已满足轮椅回转与侧向移位的无障碍卫生间')
s.rect(80,145,500,400,'#e4eff1',INK,0)
s.rect(95,160,185,190,'#c5dfe6');s.text(117,225,'淋浴区\n座椅及扶手\n可靠基层',22)
s.rect(410,170,130,160,'#fff');s.text(430,245,'坐便器',21)
s.rect(380,400,165,105,'#e4d1b1');s.text(404,460,'洗手台',21)
s.line(280,546,375,600,ORANGE,5);s.text(150,627,'外开/可紧急开启门；目标净宽需实际复核',20)
s.line(315,365,225,380,BLUE,4,True);s.line(320,420,230,389,BLUE,4,True)
s.text(95,410,'缓坡排水',20,BLUE)
s.box(650,160,490,355,'低成本现在预留','防滑地面 / 可靠扶手基层\n无凸起挡水条需配合截水和找坡\n门外不积水 / 湿区防水连续\n冷热水易调 / 照明无明显暗区\n\n未来确有轮椅需求时：\n可再借厨房面积，按实际器具重排。')
s.save('11_bath')

s=Sheet('12 / 窗边防雨、气密与保温', '窗型尽量少而重复；整窗性能和安装节点一起采购')
s.rect(320,155,180,355,'#dce1df',INK,0)
s.rect(500,155,38,355,'#e9b477',ORANGE,0)
s.rect(320,290,220,45,'#466979',INK,0)
s.line(535,340,620,360,BLUE,8);s.line(620,360,620,385,BLUE,5)
s.text(70,170,'室内',25);s.text(850,170,'室外',25)
s.line(210,240,335,290,TEAL,3,True);s.text(55,225,'内侧气密\n安装缝连续填充',21,TEAL)
s.line(820,245,538,298,BLUE,3,True);s.text(825,240,'外侧防雨收口',21,BLUE)
s.line(820,440,538,420,ORANGE,3,True);s.text(825,435,'窗边保温连续\n不留下明显热桥',21,ORANGE)
s.text(590,550,'外窗台向外排水并设滴水\n不得向室内或保温背后渗水',23)
s.save('12_window')

s=Sheet('13 / 先能住，再逐户完善', '屋面、外壳、防水保温和公共安全先完成；减少返工比晚买家具更值钱', 780)
items=[('P0 现场与设计','测量 / 出口 / 两层结构 / 完成面标高'),('P1 一次完成外壳','基础主体 / 屋面 / 门窗 / 保温 / 公共防护'),('P2 首户入住','水电污水 / 厕所厨房 / 采暖 / 照明 / 基本饰面'),('P3 其余户逐户装修','同型号设备 / 独立阀表 / 分区调试'),('P4 多年后合户','拆指定填充 / 修饰面 / 保留分区设备')]
for i,(title,body) in enumerate(items):
    y=125+i*110;s.box(85,y,990,85,title,body,'#e4efed' if i<3 else '#eee9df')
    if i<4:s.line(1100,y+40,1100,y+145,TEAL,3,True)
s.text(90,710,'可延期：影壁装饰、全院精铺、高档橱柜、景观；不可延期：入住区排水、防冻、扶手和电气保护。',18)
s.save('13_phasing')

s=Sheet('14 / 施工与隐蔽记录', '下一工序前，把看不见的质量检查好；用楼层、户号、标尺和日期记录', 780)
items=[('01 测量与方案','边界 / BM / 出口'),('02 基础与预埋','验槽 / 配筋 / 套管'),('03 两层结构','轴线 / 楼梯 / 合户口'),('04 屋面与外维护','收口 / 排水 / 保温'),('05 管线与湿区','试压 / 通水 / 电测'),('06 饰面与安装','净宽 / 防滑 / 扶手'),('07 分户调试','阀表 / 温控 / 串味'),('08 雨雪季回访','倒灌 / 冻堵 / 结露')]
for i,(title,body) in enumerate(items):
    row,col=divmod(i,4);x=45+col*290;y=155+row*235
    s.box(x,y,255,145,title,body,'#e9f0f1')
    if col<3:s.line(x+255,y+70,x+282,y+70,TEAL,3,True)
s.text(60,635,'归档：隐蔽照片 + 试验数据 + 竣工尺寸 + 回路/阀门表 + 设备说明 + 可拆区标记。',22)
s.text(60,680,'现场变更同步图纸、参数和模型；结构、电气、供暖等专项数据由相应设计与检测确定。',20)
s.save('14_sequence')
print(f'Generated {len(list(OUT.glob("*.svg")))} diagrams in {OUT}')
