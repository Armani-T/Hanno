# How EOL Inference Works

An (invisible) EOL token is automatically inserted after a line ends with one of the following:

- `}`
- `]`
- `)`
- `end`
- a name or literal

AND the next line starts with one of the following:

- `~`
- `[`
- `(`
- `\`
- `end`
- `let`
- `if`
- a name or literal
