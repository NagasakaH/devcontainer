#!/usr/bin/env node
/**
 * setup-symlink.js
 * 
 * agents-docsディレクトリへのシンボリックリンクを設定するスクリプト
 * コピー方式の代わりにシンボリックリンクを使用することで、
 * リアルタイムの変更反映が可能になります
 */

const fs = require('fs');
const path = require('path');

const CONFIG = {
  // リンク元（agents-docs）
  sourcePath: path.resolve(__dirname, '../../agents-docs'),
  // リンク先（docs）
  linkPath: path.resolve(__dirname, '../docs')
};

/**
 * シンボリックリンクを作成
 */
function createSymlink() {
  console.log('=== シンボリックリンク設定 ===');
  console.log(`[設定] リンク元: ${CONFIG.sourcePath}`);
  console.log(`[設定] リンク先: ${CONFIG.linkPath}`);
  
  // リンク元の存在確認
  if (!fs.existsSync(CONFIG.sourcePath)) {
    console.error(`[エラー] リンク元が存在しません: ${CONFIG.sourcePath}`);
    process.exit(1);
  }
  
  // 既存のdocsディレクトリ/シンボリックリンクの処理
  if (fs.existsSync(CONFIG.linkPath)) {
    const stats = fs.lstatSync(CONFIG.linkPath);
    
    if (stats.isSymbolicLink()) {
      const existingTarget = fs.readlinkSync(CONFIG.linkPath);
      if (existingTarget === CONFIG.sourcePath || 
          path.resolve(path.dirname(CONFIG.linkPath), existingTarget) === CONFIG.sourcePath) {
        console.log('[情報] 正しいシンボリックリンクが既に存在します');
        return;
      }
      // 異なるリンク先の場合は削除
      console.log('[情報] 既存のシンボリックリンクを削除します');
      fs.unlinkSync(CONFIG.linkPath);
    } else if (stats.isDirectory()) {
      // 通常のディレクトリの場合
      console.log('[警告] docsディレクトリが既に存在します');
      console.log('[情報] シンボリックリンクに置き換えるには、docsディレクトリを削除してください');
      console.log(`       rm -rf "${CONFIG.linkPath}"`);
      console.log('[情報] または、コピー方式を使用してください（generate-sidebar.jsを直接実行）');
      return;
    }
  }
  
  // シンボリックリンクを作成
  try {
    // 相対パスでシンボリックリンクを作成
    const relativePath = path.relative(path.dirname(CONFIG.linkPath), CONFIG.sourcePath);
    fs.symlinkSync(relativePath, CONFIG.linkPath, 'dir');
    console.log('[成功] シンボリックリンクを作成しました');
    console.log(`       ${CONFIG.linkPath} -> ${relativePath}`);
  } catch (error) {
    console.error('[エラー] シンボリックリンクの作成に失敗しました:', error.message);
    console.log('[ヒント] 管理者権限が必要な場合があります（Windows）');
    process.exit(1);
  }
}

/**
 * シンボリックリンクを削除してコピー方式に戻す
 */
function removeSymlink() {
  console.log('=== シンボリックリンク削除 ===');
  
  if (fs.existsSync(CONFIG.linkPath)) {
    const stats = fs.lstatSync(CONFIG.linkPath);
    
    if (stats.isSymbolicLink()) {
      fs.unlinkSync(CONFIG.linkPath);
      console.log('[成功] シンボリックリンクを削除しました');
    } else {
      console.log('[情報] シンボリックリンクではありません');
    }
  } else {
    console.log('[情報] docsディレクトリが存在しません');
  }
}

// コマンドライン引数の処理
const args = process.argv.slice(2);
const command = args[0];

switch (command) {
  case 'create':
  case undefined:
    createSymlink();
    break;
  case 'remove':
    removeSymlink();
    break;
  case 'help':
    console.log(`
使用方法: node setup-symlink.js [command]

コマンド:
  create  シンボリックリンクを作成（デフォルト）
  remove  シンボリックリンクを削除
  help    このヘルプを表示
`);
    break;
  default:
    console.error(`不明なコマンド: ${command}`);
    console.log('ヘルプを表示するには: node setup-symlink.js help');
    process.exit(1);
}
