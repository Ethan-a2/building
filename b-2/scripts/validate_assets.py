"""Validate deliverable links, dimensions, readable headers and model reports.

Does not certify engineering correctness. Emits a reproducible SHA-256 inventory.
"""
from pathlib import Path
import hashlib
import json
import re
import struct
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
    (ROOT/'asset_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest['checks'],ensure_ascii=False,indent=2))
    print(f'PASS: {len(files)} assets inventoried with SHA-256')


if __name__ == '__main__':
    main()
