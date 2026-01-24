#!/usr/bin/env node
/**
 * generate-sidebar.js
 *
 * agents-docs配下のディレクトリ構造を走査し、
 * Docusaurusのサイドバー設定を自動生成するスクリプト
 */

const fs = require("fs");
const path = require("path");

// 設定
const CONFIG = {
  // agents-docsのパス（agents-docs-previewからの相対パス）
  docsSourcePath: path.resolve(__dirname, "../../agents-docs"),
  // Docusaurus docsディレクトリのパス
  docsDestPath: path.resolve(__dirname, "../docs"),
  // サイドバー設定の出力パス
  sidebarOutputPath: path.resolve(__dirname, "../sidebars.auto.js"),
  // 除外するファイル/ディレクトリ
  excludePatterns: [
    ".gitkeep",
    ".git",
    ".DS_Store",
    "node_modules",
    ".obsidian",
  ],
  // サポートするファイル拡張子
  supportedExtensions: [".md", ".mdx"],
};

/**
 * ファイル/ディレクトリを除外するかどうかを判定
 * @param {string} name - ファイル/ディレクトリ名
 * @returns {boolean}
 */
function shouldExclude(name) {
  return CONFIG.excludePatterns.some((pattern) => {
    if (pattern.includes("*")) {
      const regex = new RegExp("^" + pattern.replace(/\*/g, ".*") + "$");
      return regex.test(name);
    }
    return name === pattern;
  });
}

/**
 * ファイル名からドキュメントIDを生成
 * @param {string} filePath - ファイルパス
 * @returns {string}
 */
function generateDocId(filePath) {
  const relativePath = path.relative(CONFIG.docsDestPath, filePath);
  // 拡張子を除去してIDを生成
  return relativePath.replace(/\.(md|mdx)$/, "").replace(/\\/g, "/");
}

/**
 * ディレクトリ名からラベルを生成（見やすい形式に変換）
 * @param {string} dirName - ディレクトリ名
 * @returns {string}
 */
function generateLabel(dirName) {
  // ハイフン/アンダースコアをスペースに変換し、各単語の先頭を大文字に
  return dirName
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

/**
 * ディレクトリを再帰的に走査してサイドバー構造を生成
 * @param {string} dirPath - 走査するディレクトリのパス
 * @param {number} depth - 現在の深さ
 * @returns {Array}
 */
function scanDirectory(dirPath, depth = 0) {
  const items = [];

  if (!fs.existsSync(dirPath)) {
    console.warn(`[警告] ディレクトリが存在しません: ${dirPath}`);
    return items;
  }

  const entries = fs.readdirSync(dirPath, { withFileTypes: true });

  // ファイルとディレクトリを分類
  const files = [];
  const directories = [];

  for (const entry of entries) {
    if (shouldExclude(entry.name)) {
      continue;
    }

    if (entry.isDirectory()) {
      directories.push(entry);
    } else if (entry.isFile()) {
      const ext = path.extname(entry.name).toLowerCase();
      if (CONFIG.supportedExtensions.includes(ext)) {
        files.push(entry);
      }
    }
  }

  // ファイルをソートして追加（降順）
  files.sort((a, b) => b.name.localeCompare(a.name, "ja"));
  for (const file of files) {
    const filePath = path.join(dirPath, file.name);
    const docId = generateDocId(filePath);
    items.push(docId);
  }

  // ディレクトリをソートして再帰的に処理（降順）
  directories.sort((a, b) => b.name.localeCompare(a.name, "ja"));
  for (const dir of directories) {
    const subDirPath = path.join(dirPath, dir.name);
    const subItems = scanDirectory(subDirPath, depth + 1);

    if (subItems.length > 0) {
      items.push({
        type: "category",
        label: generateLabel(dir.name),
        collapsed: depth > 0, // トップレベル以外は折りたたむ
        items: subItems,
      });
    }
  }

  return items;
}

/**
 * agents-docsからdocsディレクトリへシンボリックリンクまたはコピーを作成
 */
function syncDocs() {
  const sourcePath = CONFIG.docsSourcePath;
  const destPath = CONFIG.docsDestPath;

  // 既存のdocsディレクトリを確認
  if (fs.existsSync(destPath)) {
    const stats = fs.lstatSync(destPath);
    if (stats.isSymbolicLink()) {
      // 既存のシンボリックリンクがある場合は何もしない
      console.log("[情報] 既存のシンボリックリンクを使用: docs -> agents-docs");
      return;
    }
  }

  // docsディレクトリが存在しない場合は作成
  if (!fs.existsSync(destPath)) {
    fs.mkdirSync(destPath, { recursive: true });
    console.log("[情報] docsディレクトリを作成しました");
  }

  // agents-docsの内容をdocsにマージ（既存ファイルは上書きしない）
  mergeDirectory(sourcePath, destPath);
  console.log("[情報] agents-docsの内容をdocsにマージしました");
}

/**
 * ディレクトリを再帰的にマージ（既存ファイルは上書きしない）
 * @param {string} src - コピー元
 * @param {string} dest - コピー先
 */
function mergeDirectory(src, dest) {
  if (!fs.existsSync(src)) {
    console.warn(`[警告] コピー元が存在しません: ${src}`);
    return;
  }

  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }

  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (const entry of entries) {
    if (shouldExclude(entry.name)) {
      continue;
    }

    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      mergeDirectory(srcPath, destPath);
    } else {
      // 既存ファイルがある場合は上書きしない（agents-docsの内容を優先）
      if (!fs.existsSync(destPath)) {
        fs.copyFileSync(srcPath, destPath);
      } else {
        // agents-docsに同名ファイルがある場合は上書き
        fs.copyFileSync(srcPath, destPath);
      }
    }
  }
}

/**
 * サイドバー設定をファイルに出力
 * @param {Array} sidebarItems - サイドバーのアイテム
 */
function writeSidebarConfig(sidebarItems) {
  const content = `// このファイルはgenerate-sidebar.jsによって自動生成されています
// 手動で編集しないでください

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: ${JSON.stringify(sidebarItems, null, 2)}
};

module.exports = sidebars;
`;

  fs.writeFileSync(CONFIG.sidebarOutputPath, content, "utf-8");
  console.log(
    `[成功] サイドバー設定を出力しました: ${CONFIG.sidebarOutputPath}`,
  );
}

/**
 * intro.mdが存在しない場合に作成
 */
function ensureIntroDoc() {
  const introPath = path.join(CONFIG.docsDestPath, "intro.md");

  if (!fs.existsSync(introPath)) {
    // docsディレクトリに.mdファイルがあるか確認
    if (fs.existsSync(CONFIG.docsDestPath)) {
      const files = fs.readdirSync(CONFIG.docsDestPath);
      const hasMarkdown = files.some(
        (f) => f.endsWith(".md") || f.endsWith(".mdx"),
      );

      if (!hasMarkdown) {
        // イントロドキュメントを作成
        const introContent = `---
sidebar_position: 1
---

# agents-docs へようこそ

このサイトは **agents-docs** のドキュメントを閲覧するためのプレビューサイトです。

## 始め方

左側のサイドバーからドキュメントを選択してください。

## ドキュメントの追加方法

\`agents-docs\` ディレクトリにMarkdownファイルを追加すると、自動的にこのサイトに反映されます。

### ディレクトリ構造

\`\`\`
agents-docs/
├── category-name/
│   ├── doc1.md
│   └── doc2.md
└── another-category/
    └── doc3.md
\`\`\`

各ディレクトリはサイドバーのカテゴリとして表示されます。
`;

        fs.writeFileSync(introPath, introContent, "utf-8");
        console.log("[情報] イントロドキュメントを作成しました: intro.md");
      }
    }
  }
}

/**
 * メイン処理
 */
function main() {
  console.log("=== サイドバー自動生成開始 ===");
  console.log(`[設定] agents-docs: ${CONFIG.docsSourcePath}`);
  console.log(`[設定] docs: ${CONFIG.docsDestPath}`);

  // ドキュメントを同期
  syncDocs();

  // イントロドキュメントを確保
  ensureIntroDoc();

  // サイドバー構造を生成
  const sidebarItems = scanDirectory(CONFIG.docsDestPath);

  // サイドバー設定を出力
  if (sidebarItems.length === 0) {
    console.log(
      "[情報] ドキュメントが見つかりませんでした。デフォルトのサイドバーを生成します。",
    );
    writeSidebarConfig(["intro"]);
  } else {
    writeSidebarConfig(sidebarItems);
  }

  console.log("=== サイドバー自動生成完了 ===");
}

// スクリプト実行
main();

// モジュールとしてエクスポート（テスト用）
module.exports = {
  scanDirectory,
  generateDocId,
  generateLabel,
  shouldExclude,
  syncDocs,
  CONFIG,
};
