t = require('./tarot_interpretations.json')

const mine = []

for (const int of t.tarot_interpretations) {
  mine.push({
    type: 'TEMP_TAROT',
    title: int.name,
    // telling: int.fortune_telling,
    keywords: int.keywords,
    light: int.meanings.light,
    shadow: int.meanings.shadow
  })
}

console.log(JSON.stringify({ fortunes: mine }, null, 2))
