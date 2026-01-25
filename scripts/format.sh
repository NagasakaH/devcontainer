#!/bin/bash
# =============================================================================
# scripts/format.sh
# 統合フォーマッタースクリプト（スマートプロジェクト検出対応）
#
# 対応フォーマッター:
#   - prettier (Markdown, JSON, YAML, JavaScript, TypeScript)
#   - ruff (Python)
#   - shfmt (Shell scripts)
#   - CSharpier (C#)
#
# 機能:
#   - プロジェクト構造を自動検出
#   - 存在するファイルタイプに応じたフォーマッター実行
#   - 複数プロジェクトの一括処理
#
# Usage:
#   ./scripts/format.sh           # すべてのフォーマッターを実行
#   ./scripts/format.sh --check   # CIモード（変更なし、差分チェックのみ）
#   ./scripts/format.sh --verbose # 詳細出力
#   ./scripts/format.sh --help    # ヘルプ表示
#
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# =============================================================================
# 設定
# =============================================================================

# カラー出力の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# オプション
CHECK_MODE=false
VERBOSE=false
SPECIFIC_FORMATTER=""

# 結果追跡
declare -A FORMATTER_RESULTS

# 検出されたプロジェクト
declare -a PYTHON_PROJECTS=()
declare -a DOTNET_PROJECTS=()
declare -a NODE_PROJECTS=()

# =============================================================================
# ユーティリティ関数
# =============================================================================

print_help() {
    cat << EOF
統合フォーマッタースクリプト（スマートプロジェクト検出対応）

Usage:
  $(basename "$0") [OPTIONS] [FORMATTER]

Options:
  --check, -c       チェックモード（変更なし、差分があればエラー）
  --verbose, -v     詳細出力
  --help, -h        このヘルプを表示

Formatters:
  prettier          Markdown, JSON, YAML, JS/TS をフォーマット
  ruff              Python をフォーマット
  shfmt             Shell scripts をフォーマット
  csharpier         C# をフォーマット

  引数なしの場合はすべてのフォーマッターを実行します。

Features:
  - プロジェクト構造を自動検出（pyproject.toml, package.json, *.csproj等）
  - 検出されたプロジェクトディレクトリを起点にフォーマット実行
  - 複数プロジェクトの一括処理

Examples:
  $(basename "$0")                    # すべてフォーマット
  $(basename "$0") --check            # CI用チェック
  $(basename "$0") prettier           # prettierのみ実行
  $(basename "$0") --check ruff       # ruffのチェックのみ

EOF
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_verbose() {
    if $VERBOSE; then
        echo -e "${CYAN}[VERBOSE]${NC} $1"
    fi
}

log_project() {
    echo -e "${CYAN}[PROJECT]${NC} $1"
}

# ツールの存在確認
check_command() {
    local cmd="$1"
    if command -v "$cmd" &> /dev/null; then
        return 0
    fi
    return 1
}

# =============================================================================
# プロジェクト検出関数
# =============================================================================

# Pythonプロジェクトを検出
detect_python_projects() {
    log_verbose "Detecting Python projects..."
    
    # pyproject.toml, setup.py, requirements.txt を含むディレクトリを検索
    while IFS= read -r -d '' file; do
        local dir
        dir=$(dirname "$file")
        # 重複を避けるためチェック
        local already_found=false
        for existing in "${PYTHON_PROJECTS[@]:-}"; do
            if [[ "$existing" == "$dir" ]]; then
                already_found=true
                break
            fi
        done
        if ! $already_found; then
            PYTHON_PROJECTS+=("$dir")
            log_verbose "  Found Python project: $dir"
        fi
    done < <(find "${PROJECT_ROOT}" \
        \( -name "pyproject.toml" -o -name "setup.py" -o -name "requirements.txt" \) \
        -type f \
        ! -path "*/node_modules/*" \
        ! -path "*/.git/*" \
        ! -path "*/venv/*" \
        ! -path "*/.venv/*" \
        -print0 2>/dev/null || true)
    
    log_verbose "  Total Python projects found: ${#PYTHON_PROJECTS[@]}"
}

# .NETプロジェクトを検出
detect_dotnet_projects() {
    log_verbose "Detecting .NET projects..."
    
    # *.csproj, *.sln を含むディレクトリを検索
    while IFS= read -r -d '' file; do
        local dir
        dir=$(dirname "$file")
        local already_found=false
        for existing in "${DOTNET_PROJECTS[@]:-}"; do
            if [[ "$existing" == "$dir" ]]; then
                already_found=true
                break
            fi
        done
        if ! $already_found; then
            DOTNET_PROJECTS+=("$dir")
            log_verbose "  Found .NET project: $dir"
        fi
    done < <(find "${PROJECT_ROOT}" \
        \( -name "*.csproj" -o -name "*.sln" \) \
        -type f \
        ! -path "*/node_modules/*" \
        ! -path "*/.git/*" \
        ! -path "*/bin/*" \
        ! -path "*/obj/*" \
        -print0 2>/dev/null || true)
    
    log_verbose "  Total .NET projects found: ${#DOTNET_PROJECTS[@]}"
}

# Node.jsプロジェクトを検出
detect_node_projects() {
    log_verbose "Detecting Node.js projects..."
    
    # package.json を含むディレクトリを検索
    while IFS= read -r -d '' file; do
        local dir
        dir=$(dirname "$file")
        local already_found=false
        for existing in "${NODE_PROJECTS[@]:-}"; do
            if [[ "$existing" == "$dir" ]]; then
                already_found=true
                break
            fi
        done
        if ! $already_found; then
            NODE_PROJECTS+=("$dir")
            log_verbose "  Found Node.js project: $dir"
        fi
    done < <(find "${PROJECT_ROOT}" \
        -name "package.json" \
        -type f \
        ! -path "*/node_modules/*" \
        ! -path "*/.git/*" \
        -print0 2>/dev/null || true)
    
    log_verbose "  Total Node.js projects found: ${#NODE_PROJECTS[@]}"
}

# すべてのプロジェクトを検出
detect_all_projects() {
    log_info "Detecting project structures..."
    detect_python_projects
    detect_dotnet_projects
    detect_node_projects
    echo ""
}

# =============================================================================
# ファイル存在チェック関数
# =============================================================================

# 指定ディレクトリにPythonファイルが存在するか確認
has_python_files() {
    local dir="${1:-.}"
    find "$dir" -name "*.py" -type f \
        ! -path "*/node_modules/*" \
        ! -path "*/.git/*" \
        ! -path "*/venv/*" \
        ! -path "*/.venv/*" \
        -print -quit 2>/dev/null | grep -q .
}

# 指定ディレクトリにC#ファイルが存在するか確認
has_csharp_files() {
    local dir="${1:-.}"
    find "$dir" -name "*.cs" -type f \
        ! -path "*/node_modules/*" \
        ! -path "*/.git/*" \
        ! -path "*/bin/*" \
        ! -path "*/obj/*" \
        -print -quit 2>/dev/null | grep -q .
}

# 指定ディレクトリにJS/TSファイルが存在するか確認
has_js_ts_files() {
    local dir="${1:-.}"
    find "$dir" \( -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" \) -type f \
        ! -path "*/node_modules/*" \
        ! -path "*/.git/*" \
        ! -path "*/dist/*" \
        ! -path "*/build/*" \
        -print -quit 2>/dev/null | grep -q .
}

# 指定ディレクトリにShellスクリプトが存在するか確認
has_shell_files() {
    local dir="${1:-.}"
    find "$dir" \( -name "*.sh" -o -name "*.bash" \) -type f \
        ! -path "*/node_modules/*" \
        ! -path "*/.git/*" \
        -print -quit 2>/dev/null | grep -q .
}

# =============================================================================
# フォーマッター関数
# =============================================================================

format_with_prettier() {
    local name="prettier"
    log_info "Running prettier..."

    # prettier が利用可能か確認
    if ! check_command npx; then
        log_warning "npx not found, skipping prettier"
        FORMATTER_RESULTS[$name]="skipped"
        return 0
    fi

    # prettier がインストールされているか確認
    if ! npx --yes prettier --version &> /dev/null; then
        log_warning "prettier not available, skipping"
        FORMATTER_RESULTS[$name]="skipped"
        return 0
    fi

    local prettier_args=()
    local target_files="**/*.{md,json,yaml,yml,js,ts,jsx,tsx,css,html}"

    if $CHECK_MODE; then
        prettier_args+=("--check")
    else
        prettier_args+=("--write")
    fi

    # .prettierignore があれば使用
    if [[ -f "${PROJECT_ROOT}/.prettierignore" ]]; then
        log_verbose "Using .prettierignore"
    fi

    log_verbose "prettier ${prettier_args[*]} \"$target_files\""

    if npx --yes prettier "${prettier_args[@]}" "$target_files" 2>/dev/null; then
        log_success "prettier: passed"
        FORMATTER_RESULTS[$name]="passed"
        return 0
    else
        if $CHECK_MODE; then
            log_error "prettier: formatting required"
        else
            log_error "prettier: failed"
        fi
        FORMATTER_RESULTS[$name]="failed"
        return 1
    fi
}

format_with_ruff() {
    local name="ruff"
    log_info "Running ruff..."

    # ruff が利用可能か確認
    if ! check_command ruff; then
        log_warning "ruff not found, skipping"
        FORMATTER_RESULTS[$name]="skipped"
        return 0
    fi

    # Pythonファイルが存在するか確認
    if ! has_python_files "${PROJECT_ROOT}"; then
        log_info "No Python files found, skipping ruff"
        FORMATTER_RESULTS[$name]="skipped"
        return 0
    fi

    local failed=false

    # プロジェクトが検出されている場合はプロジェクト単位で実行
    if [[ ${#PYTHON_PROJECTS[@]} -gt 0 ]]; then
        for project_dir in "${PYTHON_PROJECTS[@]}"; do
            if has_python_files "$project_dir"; then
                log_project "Formatting Python in: $project_dir"
                
                local ruff_args=("format")
                if $CHECK_MODE; then
                    ruff_args+=("--check" "--diff")
                fi
                
                log_verbose "ruff ${ruff_args[*]} $project_dir"
                
                if ! ruff "${ruff_args[@]}" "$project_dir"; then
                    failed=true
                fi
            fi
        done
    else
        # プロジェクトが検出されない場合はルートから実行
        local ruff_args=("format")
        if $CHECK_MODE; then
            ruff_args+=("--check" "--diff")
        fi
        
        log_verbose "ruff ${ruff_args[*]} ."
        
        if ! ruff "${ruff_args[@]}" .; then
            failed=true
        fi
    fi

    if $failed; then
        if $CHECK_MODE; then
            log_error "ruff: formatting required"
        else
            log_error "ruff: failed"
        fi
        FORMATTER_RESULTS[$name]="failed"
        return 1
    else
        log_success "ruff: passed"
        FORMATTER_RESULTS[$name]="passed"
        return 0
    fi
}

format_with_shfmt() {
    local name="shfmt"
    log_info "Running shfmt..."

    # shfmt が利用可能か確認
    if ! check_command shfmt; then
        log_warning "shfmt not found, skipping"
        FORMATTER_RESULTS[$name]="skipped"
        return 0
    fi

    # Shell ファイルを検索
    local shell_files
    shell_files=$(find "${PROJECT_ROOT}" \
        -type f \
        \( -name "*.sh" -o -name "*.bash" \) \
        ! -path "*/node_modules/*" \
        ! -path "*/.git/*" \
        ! -path "*/vendor/*" \
        2>/dev/null || true)

    if [[ -z "$shell_files" ]]; then
        log_info "No shell scripts found, skipping shfmt"
        FORMATTER_RESULTS[$name]="skipped"
        return 0
    fi

    local shfmt_args=("-i" "4" "-ci" "-bn")
    if $CHECK_MODE; then
        shfmt_args+=("-d")
    else
        shfmt_args+=("-w")
    fi

    log_verbose "shfmt ${shfmt_args[*]} [files]"

    local failed=false
    while IFS= read -r file; do
        if [[ -n "$file" ]]; then
            if ! shfmt "${shfmt_args[@]}" "$file" 2>&1; then
                failed=true
            fi
        fi
    done <<< "$shell_files"

    if $failed; then
        if $CHECK_MODE; then
            log_error "shfmt: formatting required"
        else
            log_error "shfmt: failed"
        fi
        FORMATTER_RESULTS[$name]="failed"
        return 1
    else
        log_success "shfmt: passed"
        FORMATTER_RESULTS[$name]="passed"
        return 0
    fi
}

format_with_csharpier() {
    local name="csharpier"
    log_info "Running CSharpier..."

    # dotnet が利用可能か確認
    if ! check_command dotnet; then
        log_warning "dotnet not found, skipping CSharpier"
        FORMATTER_RESULTS[$name]="skipped"
        return 0
    fi

    # C# ファイルが存在するか確認
    if ! has_csharp_files "${PROJECT_ROOT}"; then
        log_info "No C# files found, skipping CSharpier"
        FORMATTER_RESULTS[$name]="skipped"
        return 0
    fi

    # CSharpier がインストールされているか確認
    local csharpier_cmd=""
    if dotnet tool list 2>/dev/null | grep -q csharpier; then
        csharpier_cmd="dotnet csharpier"
    elif dotnet tool list -g 2>/dev/null | grep -q csharpier; then
        csharpier_cmd="dotnet csharpier"
    elif check_command csharpier; then
        csharpier_cmd="csharpier"
    else
        log_warning "CSharpier not installed, skipping"
        log_info "Install with: dotnet tool install -g csharpier"
        FORMATTER_RESULTS[$name]="skipped"
        return 0
    fi

    local failed=false

    # プロジェクトが検出されている場合はプロジェクト単位で実行
    if [[ ${#DOTNET_PROJECTS[@]} -gt 0 ]]; then
        for project_dir in "${DOTNET_PROJECTS[@]}"; do
            if has_csharp_files "$project_dir"; then
                log_project "Formatting C# in: $project_dir"
                
                local csharpier_args=()
                if $CHECK_MODE; then
                    csharpier_args+=("check" "$project_dir")
                else
                    csharpier_args+=("format" "$project_dir")
                fi
                
                log_verbose "$csharpier_cmd ${csharpier_args[*]}"
                
                if ! $csharpier_cmd "${csharpier_args[@]}"; then
                    failed=true
                fi
            fi
        done
    else
        # プロジェクトが検出されない場合はルートから実行
        local csharpier_args=()
        if $CHECK_MODE; then
            csharpier_args+=("check" ".")
        else
            csharpier_args+=("format" ".")
        fi

        log_verbose "$csharpier_cmd ${csharpier_args[*]}"

        if ! $csharpier_cmd "${csharpier_args[@]}"; then
            failed=true
        fi
    fi

    if $failed; then
        if $CHECK_MODE; then
            log_error "CSharpier: formatting required"
        else
            log_error "CSharpier: failed"
        fi
        FORMATTER_RESULTS[$name]="failed"
        return 1
    else
        log_success "CSharpier: passed"
        FORMATTER_RESULTS[$name]="passed"
        return 0
    fi
}

# =============================================================================
# メイン処理
# =============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --check|-c)
                CHECK_MODE=true
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                print_help
                exit 0
                ;;
            prettier|ruff|shfmt|csharpier)
                SPECIFIC_FORMATTER="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                print_help
                exit 1
                ;;
        esac
    done
}

print_summary() {
    echo ""
    echo "========================================"
    echo "Format Summary"
    echo "========================================"

    local all_passed=true
    local any_failed=false

    for formatter in "${!FORMATTER_RESULTS[@]}"; do
        local result="${FORMATTER_RESULTS[$formatter]}"
        case "$result" in
            passed)
                echo -e "  ${GREEN}✓${NC} $formatter"
                ;;
            skipped)
                echo -e "  ${YELLOW}○${NC} $formatter (skipped)"
                ;;
            failed)
                echo -e "  ${RED}✗${NC} $formatter"
                any_failed=true
                all_passed=false
                ;;
        esac
    done

    echo "========================================"

    if $any_failed; then
        if $CHECK_MODE; then
            log_error "Some files need formatting. Run './scripts/format.sh' to fix."
        else
            log_error "Some formatters failed."
        fi
        return 1
    elif $all_passed; then
        log_success "All formatters passed!"
        return 0
    else
        log_info "Formatting complete (some tools were skipped)."
        return 0
    fi
}

main() {
    parse_args "$@"

    cd "$PROJECT_ROOT"

    if $CHECK_MODE; then
        log_info "Running in CHECK mode (no modifications)"
    else
        log_info "Running in FORMAT mode"
    fi

    echo ""

    # プロジェクト検出
    detect_all_projects

    local exit_code=0

    # 特定のフォーマッターのみ実行
    if [[ -n "$SPECIFIC_FORMATTER" ]]; then
        case "$SPECIFIC_FORMATTER" in
            prettier)
                format_with_prettier || exit_code=1
                ;;
            ruff)
                format_with_ruff || exit_code=1
                ;;
            shfmt)
                format_with_shfmt || exit_code=1
                ;;
            csharpier)
                format_with_csharpier || exit_code=1
                ;;
        esac
    else
        # すべてのフォーマッターを実行
        format_with_prettier || exit_code=1
        format_with_ruff || exit_code=1
        format_with_shfmt || exit_code=1
        format_with_csharpier || exit_code=1
    fi

    print_summary || exit_code=1

    return $exit_code
}

main "$@"
