# Implémentation MCP pour les APIs Cresus

## Vue d'ensemble

MCP (Model Context Protocol) fournit une interface standardisée pour exposer les APIs aux modèles d'IA (Claude, etc.). Cette implémentation expose tous les endpoints REST via des outils et ressources MCP, permettant aux clients IA d'interagir directement avec Cresus.

## Principes de Design

### 1. **Deux Couches MCP**

**Ressources** (documentation) - URIs lisibles exposant la structure des APIs
- `portfolio://docs` - Docs portfolio management
- `screener://docs` - Docs screener DSL
- `strategies://docs` - Docs strategies
- `backtests://docs` - Docs backtesting

**Outils** (actions) - Fonctions appelables avec schémas JSON
- `list_portfolios()` → GET `/portfolios`
- `get_portfolio()` → GET `/portfolios/{name}`
- `run_screener()` → POST `/screener/screeners/{name}/run`

### 2. **Architecture Modulaire**

```
src/mcp/
├── server.py              # Orchestrateur principal (MCP Server)
├── registry.py            # Registry des domaines (Portfolio, Screener, etc.)
├── domains/               # Implémentation par domaine
│   ├── base.py           # Classe de base pour domaine
│   ├── portfolio.py       # PortfolioDomain
│   ├── screener.py       # ScreenerDomain
│   ├── strategies.py      # StrategiesDomain
│   ├── backtests.py       # BacktestsDomain
│   ├── watchlist.py       # WatchlistDomain
│   └── data.py            # DataDomain
└── transport.py           # Couche HTTP (httpx client)
```

Chaque **domaine** fournit:
- Une liste de **ressources** (documentation)
- Une liste d'**outils** (actions possibles)

## Structure Détaillée

### 1. Classe de Base Domaine (`domains/base.py`)

Chaque domaine hérite d'une classe de base qui définit l'interface:

```
BaseDomain:
  - get_resources() → Liste des ressources MCP pour ce domaine
  - get_tools() → Liste des outils MCP pour ce domaine
  - call_tool(name, args) → Exécute l'outil (appel API async)
  - api_base_url → L'URL de base des APIs REST
```

### 2. Domaine Portfolio (`domains/portfolio.py`)

**Ressources:**
- `portfolio://docs` - Documentation complète du domaine

**Outils (16 actions):**
- `list_portfolios` - GET /portfolios
- `get_portfolio` - GET /portfolios/{name}
- `create_portfolio` - POST /portfolios
- `update_portfolio` - PUT /portfolios/{name}
- `delete_portfolio` - DELETE /portfolios/{name}
- `get_portfolio_positions` - GET /portfolios/{name}/positions
- `get_portfolio_metrics` - GET /portfolios/{name}/metrics
- `get_portfolio_performance` - GET /portfolios/{name}/performance
- `get_portfolio_transactions` - GET /portfolios/{name}/transactions
- `get_portfolio_value` - GET /portfolios/{name}/value
- `get_portfolio_allocation` - GET /portfolios/{name}/allocation
- `get_portfolio_risk` - GET /portfolios/{name}/risk
- `add_position` - POST /portfolios/{name}/positions
- `close_position` - DELETE /portfolios/{name}/positions/{ticker}
- `rebalance_portfolio` - POST /portfolios/{name}/rebalance
- `compare_portfolios` - POST /portfolios/compare

### 3. Domaine Screener (`domains/screener.py`)

**Ressources:**
- `screener://docs` - Documentation du DSL et exemples
- `screener://formulas` - Formules pré-enregistrées

**Outils (9 actions):**
- `list_screeners` - GET /screener/screeners
- `get_screener` - GET /screener/screeners/{name}
- `create_screener` - POST /screener/screeners
- `update_screener` - PUT /screener/screeners/{name}
- `delete_screener` - DELETE /screener/screeners/{name}
- `run_screener` - POST /screener/screeners/{name}/run
- `validate_formula` - POST /screener/builder
- `get_screener_results` - GET /screener/screeners/{name}/results
- `get_screener_history` - GET /screener/screeners/{name}/history

### 4. Domaine Strategies (`domains/strategies.py`)

**Ressources:**
- `strategies://docs` - Documentation des stratégies
- `strategies://list` - Catalogue des stratégies pré-définies

**Outils (8 actions):**
- `list_strategies` - GET /strategies
- `get_strategy` - GET /strategies/{name}
- `create_strategy` - POST /strategies
- `update_strategy` - PUT /strategies/{name}
- `delete_strategy` - DELETE /strategies/{name}
- `execute_strategy` - POST /strategies/{name}/execute
- `get_strategy_results` - GET /strategies/{name}/results
- `compare_strategies` - POST /strategies/compare

### 5. Domaine Backtests (`domains/backtests.py`)

**Ressources:**
- `backtests://docs` - Documentation backtesting

**Outils (7 actions):**
- `list_backtests` - GET /backtests
- `get_backtest` - GET /backtests/{id}
- `create_backtest` - POST /backtests
- `get_backtest_results` - GET /backtests/{id}/results
- `get_backtest_metrics` - GET /backtests/{id}/metrics
- `get_backtest_trades` - GET /backtests/{id}/trades
- `compare_backtests` - POST /backtests/compare

### 6. Domaine Watchlist (`domains/watchlist.py`)

**Outils (6 actions):**
- `list_watchlists` - GET /watchlist
- `get_watchlist` - GET /watchlist/{name}
- `create_watchlist` - POST /watchlist
- `add_to_watchlist` - POST /watchlist/{name}/items
- `remove_from_watchlist` - DELETE /watchlist/{name}/items/{ticker}
- `delete_watchlist` - DELETE /watchlist/{name}

### 7. Domaine Data (`domains/data.py`)

**Outils (6 actions):**
- `get_ticker_data` - GET /data/tickers/{ticker}
- `get_historical_prices` - GET /data/prices
- `get_indicators` - GET /data/indicators
- `search_tickers` - GET /data/search
- `get_market_data` - GET /data/markets
- `get_fundamental_data` - GET /data/fundamental

## Mapping Endpoints → Outils MCP

### Couche de Transport (`transport.py`)

Couche unique responsable d'appeler les APIs:

**Interface:**
```
async call_api(method, path, params=None, json_body=None) → JSON response
```

Gère:
- Connexion à `CRESUS_API_URL` (env var)
- Authentification optionnelle (Bearer token)
- Timeouts et retry logic
- Erreur handling
- Logging

### Routage Outils → APIs

| Outil MCP | Méthode HTTP | Endpoint | Domaine |
|-----------|-------------|----------|---------|
| list_portfolios | GET | /portfolios | Portfolio |
| create_portfolio | POST | /portfolios | Portfolio |
| get_portfolio | GET | /portfolios/{name} | Portfolio |
| get_portfolio_positions | GET | /portfolios/{name}/positions | Portfolio |
| run_screener | POST | /screener/screeners/{name}/run | Screener |
| validate_formula | POST | /screener/builder | Screener |
| list_strategies | GET | /strategies | Strategies |
| create_backtest | POST | /backtests | Backtests |

## Fluxe de Données

### Architecturalement

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Desktop Client                                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Claude AI (via claude.ai)                            │   │
│  │ Utilise les outils MCP pour appeler Cresus         │   │
│  └─────────────────────┬────────────────────────────────┘   │
│                        │ Appels MCP                          │
│                        │ (stdio)                             │
└────────────────────────┼────────────────────────────────────┘
                         │
                    ┌────▼──────────────────────────────────┐
                    │  Serveur MCP Cresus                  │
                    │  (src/mcp/server.py)                 │
                    │  ┌──────────────────────────────┐    │
                    │  │ CresusMCPServer              │    │
                    │  │ - Registry des domaines      │    │
                    │  │ - Handler des outils         │    │
                    │  │ - Gestionnaire des erreurs   │    │
                    │  └──────────────────────────────┘    │
                    │  ┌──────────────────────────────┐    │
                    │  │ 7 Domaines                   │    │
                    │  │ - Portfolio Domain           │    │
                    │  │ - Screener Domain            │    │
                    │  │ - Strategies Domain          │    │
                    │  │ - Backtests Domain           │    │
                    │  │ - Watchlist Domain           │    │
                    │  │ - Data Domain                │    │
                    │  │ - Conversations Domain       │    │
                    │  └──────────────────────────────┘    │
                    │  ┌──────────────────────────────┐    │
                    │  │ Transport Layer (httpx)      │    │
                    │  │ - Async HTTP client          │    │
                    │  │ - Retry logic                │    │
                    │  │ - Error handling             │    │
                    │  └──────────────────────────────┘    │
                    └────────┬──────────────────────────────┘
                             │ Appels HTTP
                             │
                    ┌────────▼──────────────────────────────┐
                    │  Cresus API (FastAPI)                 │
                    │  /api/v1/portfolios                   │
                    │  /api/v1/screener                     │
                    │  /api/v1/strategies                   │
                    │  /api/v1/backtests                    │
                    │  /api/v1/watchlist                    │
                    │  /api/v1/data                         │
                    │  /api/v1/conversations                │
                    └────────┬──────────────────────────────┘
                             │
                    ┌────────▼──────────────────────────────┐
                    │  Services internes                    │
                    │  (PortfolioManager, ScreenerManager)  │
                    │  & Base de données                    │
                    └───────────────────────────────────────┘
```

### Exemple d'Interaction

1. **Utilisateur** dans Claude: "Crée un screener SHA + RSI et exécute-le"

2. **Claude** appelle `create_screener(name="sha_rsi_test", formula="sha_14_green and rsi_14 > 50", ...)`

3. **Serveur MCP**:
   - Route vers `ScreenerDomain.call_tool("create_screener", {...})`
   - Appelle `Transport.call_api("POST", "/screener/screeners", json=payload)`
   - Retourne résultat à Claude

4. **Claude** appelle `validate_formula(formula="sha_14_green and rsi_14 > 50", source="cac40")`

5. **Claude** appelle `run_screener(name="sha_rsi_test")`

6. **Affiche résultats** à l'utilisateur

## Configuration et Déploiement

### 1. Variables d'Environnement

```
CRESUS_API_URL=http://localhost:8000/api/v1    # URL API
CRESUS_API_KEY=<optional_bearer_token>          # Authentification
CRESUS_LOG_LEVEL=INFO                            # Niveau de log
MCP_DEBUG=false                                  # Debug MCP protocol
CRESUS_PROJECT_ROOT=/path/to/cresus             # Path repo
```

### 2. Configuration Client (claude_desktop_config.json)

Pour configurer Claude Desktop d'utiliser le MCP Cresus:

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

### 3. Lancement du Serveur MCP

```bash
# Standalone (développement)
python -m src.mcp.main

# Avec logs détaillés
CRESUS_LOG_LEVEL=DEBUG python -m src.mcp.main

# Ou intégré avec le serveur API
jtrade --mcp  # Lance API + serveur MCP
```

### 4. Vérification

```bash
# 1. Serveur MCP démarre sans erreur
python -m src.mcp.main &

# 2. Cresus API tourne
curl http://localhost:8000/api/v1/health

# 3. Claude Desktop reconnaît le serveur MCP
# → Aller dans Settings → MCP Servers
# → "cresus-api" doit être listé et vert
```

## Avantages de cette Architecture

### 1. **Découverte Progressive**
- Claude découvre les ressources via `list_resources()`
- Peut consulter la documentation (portfolio://docs, screener://docs)
- Connaît tous les outils disponibles

### 2. **Sémantique Claire**
- Outils groupés par domaine (Portfolio, Screener, etc.)
- Noms explicites: `list_portfolios`, `run_screener`, `get_portfolio_metrics`
- Schémas JSON-Schema pour validation d'entrée

### 3. **Intégration Transparente**
- Claude utilise les outils naturellement en conversation
- Pas besoin de connaître l'URL ou l'implémentation HTTP
- Les erreurs API sont traduites en langage naturel

### 4. **Extensibilité**
- Ajouter un domaine = créer une classe qui hérite de `BaseDomain`
- Ajouter un outil = déclarer dans `get_tools()` et implémenter `call_tool()`
- Server orchestre automatiquement

### 5. **Maintenabilité**
- Code isolé par domaine (pas de monolithe)
- Transport layer centralisé
- Tests possibles sans MCP

## Étapes d'Implémentation

### Phase 1: Infrastructure (1-2 jours)
1. **CresusMCPServer** qui orchestre les domaines
2. **BaseDomain** classe abstraite avec interface commune
3. **Transport** couche HTTP async vers les APIs
4. Tests unitaires du routing

### Phase 2: Domaines Critiques (2-3 jours)
1. **PortfolioDomain** (16 outils)
2. **ScreenerDomain** (9 outils)
3. **StrategiesDomain** (8 outils)
4. Tests intégration API → MCP

### Phase 3: Domaines Secondaires (1-2 jours)
1. **BacktestsDomain** (7 outils)
2. **WatchlistDomain** (6 outils)
3. **DataDomain** (6 outils)

### Phase 4: Optimisations (1-2 jours)
1. Cache des ressources
2. Pagination pour listes volumineuses
3. Streaming pour résultats gros
4. Rate limiting client-side
5. Logging et monitoring

### Phase 5: Intégration (1 jour)
1. Configuration claude_desktop_config.json
2. Tests end-to-end avec Claude
3. Documentation utilisateur

## Cas d'Usage Activés

### Avant (sans MCP)
```
Utilisateur → Web UI → API Cresus
Claude → Claude API (pas d'accès à Cresus)
```

### Après (avec MCP)
```
Utilisateur ↔ Claude (via MCP) → API Cresus
Claude peut:
- Analyser portfolios existants
- Créer screeners
- Lancer backtests
- Donner recommandations basées sur vraies données
- Itérer: "crée un screener qui..." → valide → run
```

## Points d'Attention Architecturaux

### 1. **Sécurité**
- Bearer token optionnel (CRESUS_API_KEY)
- Pas d'exposition de secrets dans les ressources
- Validation d'entrée côté client et serveur

### 2. **Performance**
- Timeouts court par défaut (5s), long pour backtests (60s)
- Pagination par défaut (limit=50)
- Cache des ressources (ne changent pas souvent)

### 3. **Résilience**
- Retry automatique sur erreur réseau
- Fallback lisible si API down
- Logs détaillés pour debug

### 4. **Évolution**
- Versioning: v1, v2 dans BaseDomain
- Deprecation warnings pour outils oldies
- Migration guide pour API changes

## Dépendances Requises

```toml
mcp = "^0.1.0"           # MCP protocol library
httpx = "^0.24.0"        # Async HTTP client
pydantic = "^2.0"        # Data validation
loguru = "^0.7.0"        # Logging (déjà utilisé)
python = "^3.10"
```

## Design des Domaines

### Domaine Portfolio: 4 Catégories d'Outils

1. **Lecture** (3 outils) - Pas d'effets de bord
   - `list_portfolios()` → GET /portfolios
   - `get_portfolio()` → GET /portfolios/{name}
   - `get_portfolio_positions()` → GET /portfolios/{name}/positions

2. **Analyse** (6 outils) - Calculs et rapports
   - `get_portfolio_metrics()` → GET /portfolios/{name}/metrics
   - `get_portfolio_performance()` → GET /portfolios/{name}/performance
   - `get_portfolio_value()` → GET /portfolios/{name}/value
   - `get_portfolio_allocation()` → GET /portfolios/{name}/allocation
   - `get_portfolio_risk()` → GET /portfolios/{name}/risk
   - `get_portfolio_transactions()` → GET /portfolios/{name}/transactions

3. **Modification** (4 outils) - Écriture de data
   - `create_portfolio()` → POST /portfolios
   - `update_portfolio()` → PUT /portfolios/{name}
   - `delete_portfolio()` → DELETE /portfolios/{name}
   - `add_position()` → POST /portfolios/{name}/positions

4. **Analyse Comparée** (2 outils)
   - `compare_portfolios()` → POST /portfolios/compare
   - `rebalance_portfolio()` → POST /portfolios/{name}/rebalance

### Domaine Screener: Le Cœur de l'Analyse

1. **Gestion des Screeners** (4 outils)
   - Cycle complet: create → update → run → delete

2. **Validation de Formules** (2 outils)
   - Avant exécution: `validate_formula()` retourne erreurs
   - Pendant: `run_screener()` exécute réellement

3. **Résultats** (3 outils)
   - Historique, résultats courants, tendances

### Domaine Strategies: Orchestration

Actions stratégiques dont les résultats peuvent être stockés dans Portfolio:

- Define strategy avec logique
- Execute → crée des positions dans un portfolio
- Compare performance

## Résumé Fonctionnalités

| Capacité | Sans MCP | Avec MCP |
|----------|----------|----------|
| Claude peut créer portfolios | ❌ | ✅ |
| Claude peut créer screeners | ❌ | ✅ |
| Claude peut analyser positions | ❌ | ✅ |
| Claude peut valider formules | ❌ | ✅ |
| Claude peut lancer backtests | ❌ | ✅ |
| Claude peut faire recommandations données-réelles | ❌ | ✅ |
| Claude peut itérer: créer → tester → améliorer | ❌ | ✅ |

## Tests de Validation

Pour valider l'implémentation:

1. **Lancements MCP**
   ```bash
   python -m src.mcp.main  # Doit démarrer sans erreur
   ```

2. **Découverte des ressources**
   - Claude peut lister 7+ domaines
   - Chaque domaine a une ressource `://docs`

3. **Appel d'outils simples**
   - `list_portfolios()` retourne liste
   - `list_screeners()` retourne liste

4. **Cas d'usage end-to-end**
   ```
   Claude: "Crée un screener qui teste le SHA et le RSI"
   - Crée screener (create_screener)
   - Valide formula (validate_formula)
   - Exécute (run_screener)
   - Affiche résultats
   ```
