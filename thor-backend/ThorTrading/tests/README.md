# FutureTrading Tests

Comprehensive test suite for market metrics and intraday supervisor functionality.

## Test Files

- `test_market_metrics.py` - Core metric tests (open, high, low, close, range) + edge cases
- `test_intraday_supervisor.py` - Supervisor metric flow validation

## Running Tests Locally

### Quick Test Run (Recommended)

Use test settings to skip problematic migrations:

```powershell
cd A:\Thor\thor-backend
$env:DJANGO_SETTINGS_MODULE='thor_project.test_settings'
& C:/Python313/python.exe manage.py test ThorTrading.tests
```

### Individual Test Modules

```powershell
# Market metrics tests (10 tests)
$env:DJANGO_SETTINGS_MODULE='thor_project.test_settings'
& C:/Python313/python.exe manage.py test ThorTrading.tests.test_market_metrics

# Supervisor tests (1 test)
$env:DJANGO_SETTINGS_MODULE='thor_project.test_settings'
& C:/Python313/python.exe manage.py test ThorTrading.tests.test_intraday_supervisor
```

### With Coverage

```powershell
# Install coverage (first time only)
& C:/Python313/python.exe -m pip install coverage

# Run tests with coverage
$env:DJANGO_SETTINGS_MODULE='thor_project.test_settings'
& C:/Python313/python.exe -m coverage run --source='FutureTrading' manage.py test ThorTrading.tests

# Generate report
& C:/Python313/python.exe -m coverage report

# Generate HTML report
& C:/Python313/python.exe -m coverage html
# Open htmlcov/index.html in browser
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Django Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: thor_db
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.13'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install djangorestframework-simplejwt coverage
    
    - name: Run tests with coverage
      env:
        DJANGO_SETTINGS_MODULE: thor_project.test_settings
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/thor_db
      run: |
        cd thor-backend
        python -m coverage run --source='FutureTrading' manage.py test ThorTrading.tests
        python -m coverage report
        python -m coverage xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./thor-backend/coverage.xml
        fail_ci_if_error: false
```

### GitLab CI Example

```yaml
test:
  image: python:3.13
  
  services:
    - postgres:15
  
  variables:
    POSTGRES_DB: thor_db
    POSTGRES_USER: postgres
    POSTGRES_PASSWORD: postgres
    DATABASE_URL: postgresql://postgres:postgres@postgres:5432/thor_db
    DJANGO_SETTINGS_MODULE: thor_project.test_settings
  
  before_script:
    - cd thor-backend
    - pip install -r requirements.txt
    - pip install djangorestframework-simplejwt coverage
  
  script:
    - python -m coverage run --source='FutureTrading' manage.py test ThorTrading.tests
    - python -m coverage report
    - python -m coverage xml
  
  coverage: '/TOTAL.*\s+(\d+%)$/'
  
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### Azure Pipelines Example

```yaml
trigger:
  - Dev-3
  - master

pool:
  vmImage: 'ubuntu-latest'

variables:
  DJANGO_SETTINGS_MODULE: 'thor_project.test_settings'

steps:
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.13'
  displayName: 'Use Python 3.13'

- script: |
    python -m pip install --upgrade pip
    pip install -r thor-backend/requirements.txt
    pip install djangorestframework-simplejwt coverage
  displayName: 'Install dependencies'

- task: PostgreSQL@1
  inputs:
    connectionString: 'postgresql://postgres:postgres@localhost:5432/thor_db'
  displayName: 'Set up PostgreSQL'

- script: |
    cd thor-backend
    python -m coverage run --source='FutureTrading' manage.py test ThorTrading.tests
    python -m coverage report
    python -m coverage xml
  displayName: 'Run tests with coverage'
  env:
    DATABASE_URL: 'postgresql://postgres:postgres@localhost:5432/thor_db'

- task: PublishCodeCoverageResults@1
  inputs:
    codeCoverageTool: 'Cobertura'
    summaryFileLocation: '$(System.DefaultWorkingDirectory)/thor-backend/coverage.xml'
```

## Test Settings

The `thor_project/test_settings.py` file disables migrations for `FutureTrading` app to:
- Speed up test database creation
- Avoid legacy migration conflicts
- Use Django's syncdb-style table creation

**Note:** This means test DB schema is generated from current models, not via migrations.

## Dependencies

Required packages for testing:
- `djangorestframework-simplejwt` - JWT authentication (already in production requirements)
- `coverage` (optional) - Code coverage reporting

Install missing dependencies:
```powershell
& C:/Python313/python.exe -m pip install djangorestframework-simplejwt coverage
```

## Test Coverage

Current test coverage includes:

**Market Metrics (`test_market_metrics.py`)**
- ✅ MarketOpenMetric - populates market_open from last_price
- ✅ MarketHighMetric - tracks intraday highs and drawdown percentages
- ✅ MarketLowMetric - tracks intraday lows and run-up percentages
- ✅ MarketCloseMetric - captures close prices and percentage moves
- ✅ MarketRangeMetric - computes intraday range from high/low
- ✅ Edge cases - missing data, zero baselines, null percentage conditions

**Intraday Supervisor (`test_intraday_supervisor.py`)**
- ✅ Deterministic metric flow - high/low updates through multiple ticks
- ✅ Close/range aggregation - final metrics computed on market close

## Troubleshooting

### Database teardown errors
If you see `database "test_thor_db" is being accessed by other users`, answer `yes` to delete the old test database when prompted.

### Import errors
Ensure all dependencies are installed:
```powershell
& C:/Python313/python.exe -m pip install -r requirements.txt
& C:/Python313/python.exe -m pip install djangorestframework-simplejwt
```

### Migration conflicts
Use `DJANGO_SETTINGS_MODULE=thor_project.test_settings` to bypass migrations for FutureTrading app.

## Future Enhancements

- [ ] Thread lifecycle tests for supervisor (marked @skip for manual verification)
- [ ] Integration tests with live quote mocks
- [ ] Performance benchmarks for bulk metric updates
- [ ] Stress tests for concurrent session updates

