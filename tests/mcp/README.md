# Tests pour MCP

Suite complète de tests pour l'implémentation MCP (Model Context Protocol) de Cresus.

## Structure

```
tests/mcp/
├── conftest.py                  # Fixtures pytest
├── test_portfolio_domain.py      # Tests du domaine Portfolio
├── test_mcp_server.py            # Tests du serveur MCP
├── test_mcp_integration.py       # Tests d'intégration avec API réelle
└── README.md                     # Documentation
```

## Tests Inclus

### 1. `test_portfolio_domain.py` - Tests du Domaine Portfolio

**TestPortfolioDomainResources**
- ✅ `test_get_resources` - Récupération des ressources MCP
- ✅ `test_resource_content` - Structure du contenu

**TestPortfolioDomainTools**
- ✅ `test_get_tools` - Récupération de la liste des outils
- ✅ `test_tool_has_schema` - Schémas JSON-Schema validés
- ✅ `test_create_portfolio_schema` - Validation du schéma create
- ✅ `test_get_portfolio_metrics_schema` - Validation du schéma metrics

**TestPortfolioDomainCallTool** (12 outils testés)
- ✅ `test_list_portfolios` - Lister les portfolios
- ✅ `test_get_portfolio` - Récupérer un portfolio
- ✅ `test_create_portfolio` - Créer un portfolio
- ✅ `test_get_portfolio_positions` - Récupérer les positions
- ✅ `test_get_portfolio_metrics` - Récupérer les métriques
- ✅ `test_get_portfolio_transactions` - Récupérer les transactions
- ✅ `test_update_portfolio` - Mettre à jour un portfolio
- ✅ `test_delete_portfolio` - Supprimer un portfolio
- ✅ `test_compare_portfolios` - Comparer les portfolios
- ✅ `test_add_position` - Ajouter une position
- ✅ `test_close_position` - Fermer une position
- ✅ `test_unknown_tool_error` - Gestion des erreurs
- ✅ `test_api_error_handling` - Gestion des erreurs API

**TestPortfolioDomainValidation**
- ✅ `test_missing_required_parameter` - Paramètres obligatoires
- ✅ `test_invalid_parameter_type` - Validation des types

**TestPortfolioDomainIntegration**
- ✅ `test_full_workflow` - Workflow complet
- ✅ `test_metrics_analysis_workflow` - Analyse des métriques

### 2. `test_mcp_server.py` - Tests du Serveur MCP

**TestCresusMCPServer**
- ✅ `test_server_initialization` - Initialisation du serveur
- ✅ `test_server_initialization_with_env_var` - Variables d'environnement
- ✅ `test_server_initialization_with_api_key` - API key
- ✅ `test_client_initialization` - Initialisation du client HTTP
- ✅ `test_domains_registration` - Enregistrement des domaines
- ✅ `test_list_resources` - Listing des ressources
- ✅ `test_list_tools` - Listing des outils
- ✅ `test_call_tool_portfolio` - Appel des outils
- ✅ `test_call_unknown_tool` - Erreur outils inconnus

**TestCresusMCPServerIntegration**
- ✅ `test_server_workflow` - Workflow complet du serveur
- ✅ `test_multiple_domains_support` - Support multi-domaines

**TestMCPServerErrorHandling**
- ✅ `test_api_connection_error` - Erreurs de connexion
- ✅ `test_malformed_response` - Réponses malformées

### 3. `test_mcp_integration.py` - Tests d'Intégration

Tests avec l'API réelle (skippés si API pas disponible)

**TestMCPWithRealAPI**
- ✅ `test_api_health_check` - Vérification de l'API
- ✅ `test_list_portfolios_real_api` - Listing réel
- ✅ `test_portfolio_domain_with_real_api` - Domain avec API réelle

**TestMCPServerWithRealAPI**
- ✅ `test_server_with_real_api` - Serveur avec API réelle

## Lancer les Tests

### Tous les tests
```bash
pytest tests/mcp/
```

### Tests spécifiques
```bash
# Tests du domaine Portfolio uniquement
pytest tests/mcp/test_portfolio_domain.py

# Tests du serveur MCP uniquement
pytest tests/mcp/test_mcp_server.py

# Tests d'intégration (skippés si API pas disponible)
pytest tests/mcp/test_mcp_integration.py
```

### Avec verbose
```bash
pytest tests/mcp/ -v
```

### Avec coverage
```bash
pytest tests/mcp/ --cov=src/mcp --cov-report=html
```

### Tests asynchrones
```bash
pytest tests/mcp/ -v -s  # -s affiche les prints
```

### Filtrer par nom
```bash
# Tests du portfolio domain uniquement
pytest tests/mcp/test_portfolio_domain.py -v

# Tests spécifiques
pytest tests/mcp/test_portfolio_domain.py::TestPortfolioDomainTools -v
pytest tests/mcp/test_portfolio_domain.py::TestPortfolioDomainTools::test_get_tools -v
```

## Coverage Attendu

- **Portfolio Domain**: 100% couverture
  - Ressources
  - Outils (16)
  - Validation d'entrée
  - Gestion des erreurs

- **MCP Server**: >95% couverture
  - Initialisation
  - Enregistrement des domaines
  - Listing des ressources/outils
  - Appel des outils
  - Gestion des erreurs

## Fixtures Disponibles

### `conftest.py`

**Fixtures de Mock:**
```python
@pytest.fixture
def mock_client()          # Mock httpx.AsyncClient

@pytest.fixture
def portfolio_domain()      # PortfolioDomain avec mock client
```

**Fixtures de Données:**
```python
@pytest.fixture
def sample_portfolio()      # Portfolio sample data

@pytest.fixture
def sample_positions()      # Positions sample data

@pytest.fixture
def sample_metrics()        # Metrics sample data

@pytest.fixture
def sample_transactions()   # Transactions sample data
```

## Exemple d'Utilisation des Fixtures

```python
@pytest.mark.asyncio
async def test_example(portfolio_domain, sample_portfolio):
    """Test example."""
    portfolio_domain.mock_client.get.return_value.json.return_value = sample_portfolio
    
    result = await portfolio_domain.call_tool("get_portfolio", {"name": "Main"})
    
    assert result["portfolio"]["name"] == "Main"
```

## Erreurs et Debugging

### ImportError: No module named 'mcp'
```bash
pip install mcp
```

### RuntimeError: Event loop is closed
Utiliser `@pytest.mark.asyncio` sur les tests async

### Tests timeout
Les tests async peuvent être lents, augmenter le timeout:
```bash
pytest tests/mcp/ --timeout=10
```

## Intégration avec CI/CD

### GitHub Actions
```yaml
- name: Run MCP tests
  run: |
    pip install -e ".[dev]"
    pytest tests/mcp/ --cov=src/mcp
```

### Pre-commit hook
```bash
# Avant de commit, lancer les tests
pytest tests/mcp/ -x
```

## Bonnes Pratiques

1. **Isolation** - Chaque test est indépendant
2. **Mocking** - Pas d'appels API réels sauf tests intégration
3. **Nommage** - Format `test_<action>_<scenario>`
4. **Documentation** - Chaque test a une docstring
5. **Assertions** - Messages d'erreur explicites

## Ajouter des Tests

Pour ajouter un test pour un nouvel outil:

```python
async def test_new_tool(self, portfolio_domain, mock_client):
    """Test new_tool."""
    # Arrange
    mock_client.get.return_value.json.return_value = {"status": "success"}
    
    # Act
    result = await portfolio_domain.call_tool("new_tool", {"param": "value"})
    
    # Assert
    mock_client.get.assert_called_once()
    assert result["status"] == "success"
```

## Statistiques de Tests

| Catégorie | Nombre | Status |
|-----------|--------|--------|
| Portfolio Domain | 17 | ✅ |
| MCP Server | 12 | ✅ |
| Intégration | 4 | ⏳ |
| **Total** | **33** | **✅** |

## Maintenance

- Mettre à jour les tests quand l'API change
- Ajouter des tests pour les nouveaux outils
- Vérifier la couverture régulièrement
- Maintenir les fixtures synchronisées avec les API réelles
