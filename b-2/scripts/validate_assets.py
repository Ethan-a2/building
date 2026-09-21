"""Validate deliverable links, dimensions, readable headers and model reports.

Does not certify engineering correctness. Emits a reproducible SHA-256 inventory.
"""
from pathlib import Path
import hashlib
import json
import re
import struct
import csv
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = ['01_site_drainage','02_two_households','03_exposed_services',
            '04_envelope_roof','05_future_merge']


def main():
    p = json.loads((ROOT/'design/parameters.json').read_text())
    assert p['width_m'] == 12.6
    assert abs(p['house_depth_m']+p['north_setback_m']+p['south_court_m']-19) < 1e-6
    checked_links = 0
    for doc in [ROOT/'README.md', *sorted((ROOT/'design').rglob('*.md'))]:
        text = doc.read_text(encoding='utf-8')
        for ref in re.findall(r'\]\(([^)]+)\)', text):
            if ref.startswith(('http:','https:','#')):
                continue
            destination = (doc.parent/ref.split('#')[0]).resolve()
            assert destination.exists(), f'Broken link in {doc}: {ref}'
            checked_links += 1
    figures = sorted((ROOT/'design/figures').glob('*.svg'))
    assert len(figures) == 14
    for fig in figures:
        assert ET.parse(fig).getroot().tag.endswith('svg')
    reports = []
    for name in EXPECTED:
        model = ROOT/'models'/(name+'.blend')
        with model.open('rb') as f:
            assert f.read(7) == b'BLENDER', f'Unexpected .blend header: {model}'
        report = json.loads((ROOT/'models'/(name+'.json')).read_text())
        assert report['stage'] == name and report['objects'] > 20
        image = ROOT/'previews'/(name+'.png')
        with image.open('rb') as f:
            header=f.read(24)
        assert header[:8] == b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>II',header[16:24]) == (1500,1500)
        reports.append(report)
    assert (ROOT/'previews/02_ground_plan.png').exists()
    assert reports[1]['checks']['bed_count'] == 8
    assert reports[1]['checks']['merge_infill_parts'] == 4
    assert reports[3]['checks']['display_explode_m'] == 0
    assert len(reports[4]['checks']['hidden_infill_parts']) == 4
    r2_checks = None
    if (ROOT/'design/comparison_r2/options.json').exists():
        r2=json.loads((ROOT/'design/comparison_r2/options.json').read_text())
        assert r2['confirmed']['setbacks_outside_building'] is True
        totals={}
        for option in r2['options']:
            ident=option['id']
            with (ROOT/f'models/comparison_r2/{ident}_comparison.blend').open('rb') as f:
                assert f.read(7)==b'BLENDER'
            q=json.loads((ROOT/f'models/comparison_r2/{ident}_quantities.json').read_text())
            assert abs(q['dimension_chain_m']-19)<1e-6
            assert q['south_convertible_rooms_per_floor']==2
            totals[ident]=q['body_projection_two_floors_m2']
            for kind in ['floor1','floor2','axon']:
                with (ROOT/f'previews/comparison_r2/{ident}_{kind}.png').open('rb') as f:
                    h=f.read(24)
                assert h[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',h[16:24])==(1600,1600)
            openings=list(csv.DictReader((ROOT/f'models/comparison_r2/{ident}_openings_reference.csv').open(encoding='utf-8-sig')))
            south_upper_doors=[r for r in openings if r['floor']=='2' and r['wall']=='South facade' and r['type']=='door']
            assert len(south_upper_doors)==(3 if ident in 'BC' else 0), 'Upper facade doors must have a public gallery'
        assert totals=={'A':327.6,'B':327.6,'C':327.6,'D':315.0}
        for kind in ['floor1','floor2','axon']:
            assert (ROOT/f'previews/comparison_r2/compare_{kind}.png').exists()
        quote=ROOT/'design/comparison_r2/四方案分项报价表.csv'
        rows=list(csv.reader(quote.open(encoding='utf-8-sig')))
        assert all(len(r)==12 for r in rows)
        with (ROOT/'design/comparison_r2/报价比选册.pdf').open('rb') as f:
            assert f.read(5)==b'%PDF-'
        html=ROOT/'design/comparison_r2/报价比选册.html'
        for ref in re.findall(r'src="([^"]+)"',html.read_text()):
            assert (html.parent/ref).resolve().is_file()
        r2_checks={'editable_options':4,'renders':12,'contact_sheets':3,'quote_rows':len(rows)-1,'upper_south_doors_have_gallery':True,'setbacks_outside_12_6m_building':True}
    files = []
    for file in sorted(ROOT.rglob('*')):
        if not file.is_file() or file.name == 'asset_manifest.json':
            continue
        if '__pycache__' in file.parts or re.search(r'\.blend\d+$',file.name) or file.suffix == '.pyc':
            continue
        if '.git' in file.parts:
            continue
        data = file.read_bytes()
        files.append({'path':str(file.relative_to(ROOT)), 'bytes':len(data),
                      'sha256':hashlib.sha256(data).hexdigest()})
    manifest = {'revision':p['revision'],'validation_scope':'asset integrity, local links and model-stage invariants; not engineering approval',
                'checks':{'dimension_chain_m':19,'markdown_local_links':checked_links,
                          'svg_diagrams':len(figures),'blender_stages':len(reports),
                          'stage_previews':6,'bed_count_two_floors':8},
                'files':files}
    if r2_checks:
        manifest['revision']='R2-2026-09-20'
        manifest['checks']['comparison_r2']=r2_checks
    (ROOT/'asset_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest['checks'],ensure_ascii=False,indent=2))
    print(f'PASS: {len(files)} assets inventoried with SHA-256')


if __name__ == '__main__':
    main()
