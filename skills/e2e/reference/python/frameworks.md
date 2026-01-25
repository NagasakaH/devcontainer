---
sidebar_position: 1769331671
date: 2026-01-25T09:01:11+00:00
---

# Python E2Eテストフレームワーク

Pythonでエンドツーエンドテストを実践するためのフレームワークとツールガイド。

## テストフレームワーク

### Playwright for Python（推奨）

Microsoftが開発したモダンなブラウザ自動化ツール。複数ブラウザをサポートし、高速で信頼性が高い。

```python
# tests/e2e/test_market_search.py
from playwright.sync_api import Page, expect
import pytest

class TestMarketSearch:
    def test_user_can_search_and_filter_markets(self, page: Page):
        """ユーザーは市場を検索してフィルタリングできる"""
        # 1. ホームページに移動
        page.goto('/')
        
        # 2. 市場ページに移動
        page.click('a[href="/markets"]')
        
        # 3. 検索を実行
        page.fill('input[placeholder="検索"]', 'election')
        page.wait_for_timeout(600)  # デバウンス待機
        
        # 4. 結果を検証
        results = page.locator('[data-testid="market-card"]')
        expect(results).to_have_count(5, timeout=5000)
    
    def test_user_can_view_market_details(self, page: Page):
        """ユーザーは市場の詳細を表示できる"""
        page.goto('/markets')
        
        # 最初の市場カードをクリック
        page.locator('[data-testid="market-card"]').first.click()
        
        # 詳細ページが表示されることを確認
        expect(page.locator('h1')).to_be_visible()
        expect(page.locator('[data-testid="market-chart"]')).to_be_visible()

# conftest.py
import pytest
from playwright.sync_api import Playwright

@pytest.fixture(scope="session")
def browser_context_args():
    return {
        "viewport": {"width": 1280, "height": 720},
        "locale": "ja-JP",
    }

@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    yield page
    context.close()
```

### Selenium

最も広く使用されているブラウザ自動化ツール。多くのブラウザとプログラミング言語をサポート。

```python
# tests/e2e/test_market_search.py
import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TestMarketSearch:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
        yield
        self.driver.quit()
    
    def test_user_can_search_and_filter_markets(self):
        """ユーザーは市場を検索してフィルタリングできる"""
        self.driver.get('http://localhost:3000/')
        
        # 市場ページに移動
        self.driver.find_element(By.CSS_SELECTOR, 'a[href="/markets"]').click()
        
        # 検索を実行
        search_input = self.driver.find_element(By.CSS_SELECTOR, 'input[placeholder="検索"]')
        search_input.send_keys('election')
        
        # 結果を待機
        WebDriverWait(self.driver, 5).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '[data-testid="market-card"]'))
        )
        
        # 結果を検証
        results = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="market-card"]')
        assert len(results) == 5
    
    def test_user_can_view_market_details(self):
        """ユーザーは市場の詳細を表示できる"""
        self.driver.get('http://localhost:3000/markets')
        
        # 最初の市場カードをクリック
        cards = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="market-card"]')
        cards[0].click()
        
        # 詳細ページが表示されることを確認
        WebDriverWait(self.driver, 5).until(
            EC.visibility_of_element_located((By.TAG_NAME, 'h1'))
        )
        assert self.driver.find_element(By.CSS_SELECTOR, '[data-testid="market-chart"]').is_displayed()
```

### pytest-bdd（BDDスタイル）

Gherkin構文でテストシナリオを記述するBDDフレームワーク。

```gherkin
# features/market_search.feature
Feature: 市場検索
  ユーザーとして
  市場を検索してフィルタリングしたい
  投資対象を見つけるために

  Scenario: 市場を検索する
    Given ホームページにアクセスする
    When 市場ページに移動する
    And 検索フィールドに "election" と入力する
    Then 5件の市場カードが表示される
```

```python
# tests/e2e/test_market_search.py
from pytest_bdd import scenario, given, when, then
from playwright.sync_api import Page, expect

@scenario('market_search.feature', '市場を検索する')
def test_search_markets():
    pass

@given('ホームページにアクセスする')
def go_to_home(page: Page):
    page.goto('/')

@when('市場ページに移動する')
def go_to_markets(page: Page):
    page.click('a[href="/markets"]')

@when('検索フィールドに "<keyword>" と入力する')
def search_keyword(page: Page, keyword: str):
    page.fill('input[placeholder="検索"]', keyword)
    page.wait_for_timeout(600)

@then('<count>件の市場カードが表示される')
def verify_results(page: Page, count: int):
    results = page.locator('[data-testid="market-card"]')
    expect(results).to_have_count(int(count))
```

## Page Object パターン

```python
# tests/pages/markets_page.py
from playwright.sync_api import Page, Locator

class MarketsPage:
    def __init__(self, page: Page):
        self.page = page
        self.search_input = page.locator('input[placeholder="検索"]')
        self.market_cards = page.locator('[data-testid="market-card"]')
        self.filter_buttons = page.locator('[data-testid="filter-button"]')
    
    def goto(self):
        self.page.goto('/markets')
    
    def search(self, keyword: str):
        self.search_input.fill(keyword)
        self.page.wait_for_timeout(600)  # デバウンス待機
    
    def apply_filter(self, filter_name: str):
        self.filter_buttons.filter(has_text=filter_name).click()
    
    def get_market_count(self) -> int:
        return self.market_cards.count()
    
    def click_first_market(self):
        self.market_cards.first.click()

# 使用例
def test_search_markets(page: Page):
    markets_page = MarketsPage(page)
    markets_page.goto()
    markets_page.search('election')
    
    assert markets_page.get_market_count() == 5
```

## アサーション

### Playwright expect

```python
from playwright.sync_api import expect

# 要素の可視性
expect(page.locator('h1')).to_be_visible()
expect(page.locator('.modal')).to_be_hidden()

# テキスト
expect(page.locator('h1')).to_have_text('市場一覧')
expect(page.locator('h1')).to_contain_text('市場')

# 属性
expect(page.locator('input')).to_have_value('election')
expect(page.locator('button')).to_be_enabled()
expect(page.locator('input')).to_be_disabled()

# 数
expect(page.locator('.item')).to_have_count(5)

# URL
expect(page).to_have_url('/markets')
expect(page).to_have_title('市場 | MyApp')
```

### Selenium + pytest

```python
# 基本的なアサーション
assert driver.title == "市場 | MyApp"
assert "市場" in driver.find_element(By.TAG_NAME, 'h1').text
assert driver.find_element(By.CSS_SELECTOR, '.modal').is_displayed()

# WebDriverWait でのアサーション
from selenium.webdriver.support import expected_conditions as EC

WebDriverWait(driver, 10).until(
    EC.text_to_be_present_in_element((By.TAG_NAME, 'h1'), '市場')
)
```

## 実行コマンド

```bash
# Playwright
pytest tests/e2e/                           # E2Eテスト実行
pytest tests/e2e/ --headed                  # ブラウザ表示
pytest tests/e2e/ --browser chromium        # 特定ブラウザ
pytest tests/e2e/ --browser-channel chrome  # Chrome安定版
pytest tests/e2e/ --slowmo 500              # スローモーション
pytest tests/e2e/ --tracing on              # トレース記録

# Selenium
pytest tests/e2e/                           # E2Eテスト実行
pytest tests/e2e/ -v                        # 詳細出力
pytest tests/e2e/ -k "search"               # 名前でフィルタ

# レポート生成
pytest tests/e2e/ --html=report.html
pytest tests/e2e/ --junitxml=results.xml

# 並列実行（pytest-xdist）
pytest tests/e2e/ -n auto
```

## テストアーティファクト

### Playwright トレース

```python
# conftest.py
import pytest
from playwright.sync_api import Playwright

@pytest.fixture
def context(browser):
    context = browser.new_context()
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    yield context
    context.tracing.stop(path="artifacts/trace.zip")
    context.close()

# トレース表示
# playwright show-trace artifacts/trace.zip
```

### スクリーンショット

```python
# 手動取得
page.screenshot(path="artifacts/screenshot.png")
page.screenshot(path="artifacts/full-page.png", full_page=True)

# 失敗時に自動取得（conftest.py）
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    
    if rep.when == "call" and rep.failed:
        page = item.funcargs.get("page")
        if page:
            page.screenshot(path=f"artifacts/failure-{item.name}.png")
```

## CI/CD統合

### GitHub Actions

```yaml
# .github/workflows/e2e.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pytest playwright pytest-playwright
          playwright install --with-deps
      
      - name: Run E2E tests
        run: pytest tests/e2e/ --tracing retain-on-failure
      
      - name: Upload artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-artifacts
          path: artifacts/
```

## 設定ファイル

### pytest.ini

```ini
[pytest]
testpaths = tests/e2e
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short
markers =
    slow: marks tests as slow
    smoke: marks tests as smoke tests
```

### pyproject.toml

```toml
[tool.pytest.ini_options]
testpaths = ["tests/e2e"]
addopts = "-v --tb=short"

[tool.playwright]
browser = "chromium"
headless = true
```

## ベストプラクティス

### 推奨事項

- `Playwright for Python` を使用（モダン、高速、信頼性が高い）
- Page Object パターンで保守性を向上
- `data-testid` 属性をセレクタに使用
- テストデータはフィクスチャで管理
- 重要なユーザーフローのみをE2Eでテスト
- トレースとスクリーンショットを活用

### 避けるべきこと

- 脆いセレクタ（CSS クラス、XPath の深いパス）
- 任意の `time.sleep()` 待機
- 本番環境でのテスト実行
- 全てのエッジケースをE2Eでテスト
- テスト間でのデータ依存

## 関連ツール

| ツール | 用途 |
|--------|------|
| `playwright` | ブラウザ自動化（推奨） |
| `selenium` | ブラウザ自動化（レガシー） |
| `pytest-playwright` | Playwright + pytest統合 |
| `pytest-bdd` | BDDスタイルテスト |
| `pytest-html` | HTMLレポート生成 |
| `pytest-xdist` | 並列実行 |
| `allure-pytest` | 高度なレポート生成 |
