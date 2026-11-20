// Configuracion de lint-staged (hook pre-commit). lint-staged pasa las rutas
// absolutas de los archivos en staging como argumentos finales de cada comando.
module.exports = {
  // Backend: ruff corre dentro de backend/ (su propio proyecto/venv via uv).
  "backend/**/*.py": [
    "uv run --directory backend ruff check --fix",
    "uv run --directory backend ruff format",
  ],
  // Frontend: prettier del propio frontend, invocado con node (sin npx ni .cmd),
  // respetando las exclusiones de frontend/.prettierignore.
  "frontend/**/*.{ts,tsx,js,jsx,css,json}":
    "node frontend/node_modules/prettier/bin/prettier.cjs --write --ignore-path frontend/.prettierignore",
};
