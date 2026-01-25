#!/usr/bin/env node
/**
 * watch-docs.js
 *
 * agents-docsの変更を監視し、自動的にサイドバーを再生成するスクリプト
 * chokidarを使用してファイル変更を検知
 */

const chokidar = require("chokidar");
const path = require("path");
const { exec } = require("child_process");
const debounce = require("./utils/debounce");

// 設定
const CONFIG = {
  // 監視対象のディレクトリ
  watchPath: path.resolve(__dirname, "../../agents-docs"),
  // generate-sidebar.jsのパス
  generateScript: path.resolve(__dirname, "generate-sidebar.js"),
  // 監視対象の拡張子
  watchExtensions: [".md", ".mdx"],
  // 除外パターン
  ignorePatterns: [
    /(^|[\/\\])\../, // dotfiles
    /node_modules/,
    /\.git/,
    /\.gitkeep$/,
  ],
  // デバウンス間隔（ミリ秒）
  debounceInterval: 500,
};

/**
 * サイドバー生成スクリプトを実行
 */
function runGenerateSidebar() {
  console.log("\n[watch] 変更を検知しました。サイドバーを再生成します...");

  exec(`node "${CONFIG.generateScript}"`, (error, stdout, stderr) => {
    if (error) {
      console.error("[watch] エラー:", error.message);
      return;
    }
    if (stderr) {
      console.error("[watch] stderr:", stderr);
    }
    if (stdout) {
      console.log(stdout);
    }
    console.log("[watch] 監視を継続中...\n");
  });
}

// デバウンス処理されたサイドバー生成関数
const debouncedGenerate = debounce(runGenerateSidebar, CONFIG.debounceInterval);

/**
 * ファイル監視を開始
 */
function startWatching() {
  console.log("=== agents-docs 監視開始 ===");
  console.log(`[watch] 監視対象: ${CONFIG.watchPath}`);
  console.log(`[watch] 拡張子: ${CONFIG.watchExtensions.join(", ")}`);
  console.log("[watch] Ctrl+C で終了\n");

  // 初回のサイドバー生成
  runGenerateSidebar();

  // ファイル監視の設定
  const watcher = chokidar.watch(CONFIG.watchPath, {
    ignored: CONFIG.ignorePatterns,
    persistent: true,
    ignoreInitial: true,
    awaitWriteFinish: {
      stabilityThreshold: 300,
      pollInterval: 100,
    },
  });

  // イベントハンドラ
  watcher
    .on("add", (filePath) => {
      if (isWatchedFile(filePath)) {
        console.log(`[watch] ファイル追加: ${path.relative(CONFIG.watchPath, filePath)}`);
        debouncedGenerate();
      }
    })
    .on("change", (filePath) => {
      if (isWatchedFile(filePath)) {
        console.log(`[watch] ファイル変更: ${path.relative(CONFIG.watchPath, filePath)}`);
        debouncedGenerate();
      }
    })
    .on("unlink", (filePath) => {
      if (isWatchedFile(filePath)) {
        console.log(`[watch] ファイル削除: ${path.relative(CONFIG.watchPath, filePath)}`);
        debouncedGenerate();
      }
    })
    .on("addDir", (dirPath) => {
      console.log(`[watch] ディレクトリ追加: ${path.relative(CONFIG.watchPath, dirPath)}`);
      debouncedGenerate();
    })
    .on("unlinkDir", (dirPath) => {
      console.log(`[watch] ディレクトリ削除: ${path.relative(CONFIG.watchPath, dirPath)}`);
      debouncedGenerate();
    })
    .on("error", (error) => {
      console.error("[watch] エラー:", error);
    })
    .on("ready", () => {
      console.log("[watch] 初期スキャン完了。監視中...\n");
    });

  // プロセス終了時のクリーンアップ
  process.on("SIGINT", () => {
    console.log("\n[watch] 監視を終了します...");
    watcher.close().then(() => {
      console.log("[watch] 終了しました");
      process.exit(0);
    });
  });

  return watcher;
}

/**
 * 監視対象のファイルかどうかを判定
 * @param {string} filePath - ファイルパス
 * @returns {boolean}
 */
function isWatchedFile(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  return CONFIG.watchExtensions.includes(ext);
}

// メイン実行
if (require.main === module) {
  startWatching();
}

module.exports = { startWatching, CONFIG };
