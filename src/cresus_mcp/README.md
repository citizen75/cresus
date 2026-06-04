# MCP Server for Cresus APIs

Implémentation du protocol MCP (Model Context Protocol) pour exposer les APIs Cresus aux modèles d'IA (Claude, etc.).

## Architecture

```
CresusMCPServer
├── PortfolioDomain (16 outils)
│   ├── list_portfolios
│   ├── get_portfolio
│   ├── create_portfolio
│   ├── update_portfolio
│   ├── delete_portfolio
│   ├── get_portfolio_positions
│   ├── get_portfolio_metrics
│   ├── get_portfolio_performance
│   ├── get_portfolio_transactions
│   ├── get_portfolio_value
│   ├── get_portfolio_allocation
│   ├── get_portfolio_risk
│   ├── add_position
│   ├── close_position
│   ├── compare_portfolios
│   └── rebalance_portfolio
├── ScreenerDomain (à venir)
├── StrategiesDomain (à venir)
└── ... autres domaines
```

## Configuration

### Variables d'Environnement

```bash
# URL de l'API Cresus
export CRESUS_API_URL=http://localhost:8000/api/v1

# Optionnel: Bearer token pour authentification
export CRESUS_API_KEY=your_api_key

# Niveau de log
export CRESUS_LOG_LEVEL=INFO

# Chemin du projet
export CRESUS_PROJECT_ROOT=/path/to/cresus
```

### Configuration Claude Desktop

Ajouter à `~/.claude/config.json` (MacOS/Linux) ou `%APPDATA%\Claude\config.json` (Windows):

```json
{
  "mcpServers": {
    "cresus-api": {
      "command": "python",
      "args": ["-m", "src.mcp.main"],
      "env": {
        "CRESUS_API_URL": "http://localhost:8000/api/v1",
        "CRESUS_PROJECT_ROOT": "/path/to/cresus"
      }
    }
  }
}
```

## Lancement

### Standalone
```bash
python -m src.mcp.main
```

### Avec logs détaillés
```bash
CRESUS_LOG_LEVEL=DEBUG python -m src.mcp.main
```

### Via Claude Desktop
Une fois configuré, le serveur MCP lance automatiquement au démarrage de Claude.

## Utilisation

### Découverte des Outils

Claude découvre automatiquement tous les outils disponibles:

```
Claude: "Quels outils as-tu?"
→ Claude voit 16 outils Portfolio disponibles
```

### Exemples

#### Lister les portfolios
```
Claude: "Liste mes portfolios"
→ Appelle: list_portfolios()
→ GET /portfolios
```

#### Créer un portfolio
```
Claude: "Crée un portfolio appelé 'Mon Portefeuille' avec 50000€"
→ Appelle: create_portfolio(name="Mon Portefeuille", initial_capital=50000, currency="EUR")
→ POST /portfolios
```

#### Analyser les performances
```
Claude: "Affiche le Sharpe ratio de mon portfolio 'Principal'"
→ Appelle: get_portfolio_metrics(portfolio_name="Principal")
→ GET /portfolios/Principal/metrics
```

#### Comparer des portfolios
```
Claude: "Compare la performance de 'Principal' et 'Secondaire'"
→ Appelle: compare_portfolios(portfolio_names=["Principal", "Secondaire"])
→ POST /portfolios/compare
```

## Structure des Domaines

### BaseDomain

Classe de base pour tous les domaines:

```python
class BaseDomain(ABC):
    async def get_resources() -> List[Resource]  # Documentation
    async def get_tools() -> List[Tool]          # Liste des outils
    async def call_tool(name, args) -> Dict      # Exécuter un outil
```

### PortfolioDomain

Implémente les 16 outils de gestion de portfolios:

- **Lecture** (3): list, get, positions
- **Analyse** (6): metrics, performance, value, allocation, risk, transactions
- **Modification** (4): create, update, delete, add_position
- **Comparaison** (2): compare, rebalance

Chaque outil:
1. Valide les arguments via JSON-Schema
2. Appelle l'API REST correspondante
3. Retourne le résultat en JSON

## Erreurs et Gestion

Tous les outils retournent JSON:

### Succès
```json
{
  "status": "success",
  "data": { ... }
}
```

### Erreur
```json
{
  "error": "Portfolio not found",
  "details": "..."
}
```

Claude traduit automatiquement les erreurs en langage naturel pour l'utilisateur.

## Logs

Les logs sont stockés dans:
- **Console** - logs INFO et supérieurs
- **logs/mcp.log** - tous les logs (rotation automatique)

Activer les logs DEBUG:
```bash
CRESUS_LOG_LEVEL=DEBUG python -m src.mcp.main
```

## Dépendances

Requises dans `pyproject.toml`:
```toml
mcp = "^0.1.0"
httpx = "^0.24.0"
```

## Prochaines Étapes

1. ✅ **PortfolioDomain** - Implémenté
2. ⏳ **ScreenerDomain** - À faire
3. ⏳ **StrategiesDomain** - À faire
4. ⏳ **BacktestsDomain** - À faire
5. ⏳ **WatchlistDomain** - À faire
6. ⏳ **DataDomain** - À faire

## Debugging

### Vérifier la connexion à l'API
```bash
curl http://localhost:8000/api/v1/health
```

### Vérifier le serveur MCP
```bash
python -m src.mcp.main
# Devrait afficher: "Connected to Cresus API at ..."
```

### Vérifier dans Claude Desktop
```
Settings → MCP Servers → "cresus-api" doit être vert
```

## Support

Pour des problèmes:
1. Vérifier que l'API Cresus tourne: `curl http://localhost:8000/api/v1/health`
2. Vérifier les logs: `cat logs/mcp.log`
3. Augmenter le log level: `CRESUS_LOG_LEVEL=DEBUG`
