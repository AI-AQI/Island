// npm install --no-save gltf-validator, then: node scripts/validate_glb.cjs
const fs = require('fs');
const path = require('path');
const validator = require(process.env.GLTF_VALIDATOR_MODULE || 'gltf-validator');
const root = path.resolve(__dirname, '..');
(async () => {
  const files = ['island_dusk.glb', ...fs.readdirSync(path.join(root, 'assets/glb')).filter(f => f.endsWith('.glb')).sort().map(f => `assets/glb/${f}`)];
  const summary = [];
  for (const name of files) {
    const report = await validator.validateBytes(new Uint8Array(fs.readFileSync(path.join(root, name))), { uri: name, maxIssues: 100 });
    summary.push({ file: name, errors: report.issues.numErrors, warnings: report.issues.numWarnings, infos: report.issues.numInfos });
    if (name === 'island_dusk.glb') fs.writeFileSync(path.join(root, 'reports/gltf_validation.json'), JSON.stringify(report, null, 2));
    if (report.issues.numErrors || report.issues.numWarnings) console.log(name, JSON.stringify(report.issues));
  }
  fs.writeFileSync(path.join(root, 'reports/all_glb_validation.json'), JSON.stringify(summary, null, 2));
  console.log(JSON.stringify({ files: summary.length, errors: summary.reduce((a,b)=>a+b.errors,0), warnings: summary.reduce((a,b)=>a+b.warnings,0) }));
})();
