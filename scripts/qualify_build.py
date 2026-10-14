#!/usr/bin/env python3
"""Fail closed on fitter, all-corner timing, resource and constraint evidence."""
import argparse
import hashlib
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--report', default='evidence/qualification.json')
args = parser.parse_args()
out = ROOT / 'core/projects/output_files'
issues = []
fit = (out / 'moomesa_pocket.fit.summary').read_text()
sta = (out / 'moomesa_pocket.sta.summary').read_text()
fit_rpt = (out / 'moomesa_pocket.fit.rpt').read_text(errors='replace')
sta_rpt = (out / 'moomesa_pocket.sta.rpt').read_text(errors='replace')
if not re.search(r'^Fitter Status : Successful', fit, re.M):
    issues.append('Fitter did not succeed')
timing = [{'type': kind, 'slack_ns': float(slack)} for kind, slack in
          re.findall(r'Type\s*:\s*([^\n]+)\nSlack\s*:\s*([-\d.]+)', sta)]
for corner in ['Slow 1100mV 85C', 'Slow 1100mV 0C',
               'Fast 1100mV 85C', 'Fast 1100mV 0C']:
    for check in ['Setup', 'Hold', 'Recovery', 'Removal', 'Minimum Pulse Width']:
        if not any(f'{corner} Model {check} ' in x['type'] for x in timing):
            issues.append(f'Missing {corner} {check} timing')
failures = [entry for entry in timing if entry['slack_ns'] < 0]
if failures:
    issues.append('Negative timing slack')
ram = re.search(r'Total RAM Blocks : (\d+) / (\d+)', fit)
if not ram:
    issues.append('Missing M10K resource count')
    used = capacity = 0
else:
    used, capacity = map(int, ram.groups())
    if used >= capacity:
        issues.append('No M10K headroom')
ignored = sorted(set(line for line in (fit_rpt+'\n'+sta_rpt).splitlines()
                     if re.search(r'Warning \(332(?:049|174)\)', line)))
# Upstream BSP requests dram_clk output delay before it creates that clock;
# the later core SDC supplies the actual SDRAM I/O constraints. Nothing else
# is accepted silently, especially unmatched game multicycle filters.
unexpected_ignored = [line for line in ignored if not (
    'sys_constr.sdc(47)' in line or 'sys_constr.sdc(49)' in line)]
if unexpected_ignored:
    issues.append('Unexpected ignored timing constraints')
unconstrained = dict(re.findall(
    r';\s*(Unconstrained (?:Clocks|Input Ports|Input Port Paths|Output Ports|Output Port Paths))\s*;\s*(\d+)',
    sta_rpt))
if len(unconstrained) != 5 or any(int(n) for n in unconstrained.values()):
    issues.append('Missing or nonzero unconstrained path summary')
raw = out / 'moomesa_pocket.rbf'
fit_time = (out / 'moomesa_pocket.fit.summary').stat().st_mtime
map_time = (out / 'moomesa_pocket.map.summary').stat().st_mtime
if fit_time < map_time:
    issues.append('Fitter summary is older than synthesis')
if (out / 'moomesa_pocket.sta.summary').stat().st_mtime < fit_time:
    issues.append('Timing summary is older than final fit')
source_hashes = {}
for directory in ['rtl', 'target', 'platform', 'modules']:
    for source in sorted((ROOT/'core'/directory).rglob('*')):
        if source.is_file() and source.suffix in {'.v', '.sv', '.svh', '.mem', '.mif', '.qip'}:
            name = str(source.relative_to(ROOT))
            source_hashes[name] = hashlib.sha256(source.read_bytes()).hexdigest()
            if source.stat().st_mtime > map_time:
                issues.append(f'RTL/init source newer than synthesis: {name}')
for name in ['moomesa_pocket.qsf', 'moomesa_pocket.sdc']:
    source = ROOT/'core/projects'/name
    source_hashes[str(source.relative_to(ROOT))] = hashlib.sha256(source.read_bytes()).hexdigest()
    if source.stat().st_mtime > fit_time:
        issues.append(f'Project settings newer than fit: {name}')
if not raw.is_file():
    issues.append('Missing assembled RBF')
elif raw.stat().st_mtime < fit_time:
    issues.append('RBF is older than final fit')
result = {
    'qualified': not issues, 'issues': issues,
    'm10k_used': used, 'm10k_capacity': capacity, 'm10k_free': capacity-used,
    'timing_entries': len(timing),
    'worst_slack_ns': min((x['slack_ns'] for x in timing), default=None),
    'negative_timing': failures, 'timing': timing,
    'ignored_constraints': ignored, 'unexpected_ignored': unexpected_ignored,
    'unconstrained': unconstrained,
    'source_hashes': source_hashes,
    'rbf_sha256': hashlib.sha256(raw.read_bytes()).hexdigest() if raw.is_file() else None,
    'scope': 'All reported internal/SDRAM timing; APF and unused/SRAM interfaces retain documented false paths. Physical gameplay pending.',
}
report = ROOT / args.report
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in
                  ['timing','ignored_constraints','negative_timing','source_hashes']}, indent=2))
raise SystemExit(0 if result['qualified'] else 1)
