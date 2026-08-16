const fs = require('fs');
const path = 'frontend/src/index.css';
let content = fs.readFileSync(path, 'utf8');

const replacements = [
  ['--surface-canvas: 8 12 30;', '--surface-canvas: 5 8 20;'],
  ['--surface-default: 15 22 44;', '--surface-default: 10 15 35;'],
  ['--surface-subtle: 22 30 55;', '--surface-subtle: 15 22 48;'],
  ['--surface-raised: 28 38 65;', '--surface-raised: 20 28 55;'],
  ['--surface-elevated: 35 48 78;', '--surface-elevated: 25 35 60;'],
];

for (const [old, neu] of replacements) {
  if (content.includes(old)) {
    content = content.split(old).join(neu);
    console.log('Updated dark mode colors');
  }
}

fs.writeFileSync(path, content);
console.log('Done');
