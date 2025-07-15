#!/usr/bin/env python3

"""
Claude API X投稿生成システム

このスクリプトは、Claude APIを使用してブログ記事を分析し、
3パターンのX投稿文を自動生成します。

主な機能:
- ブログ記事の技術的分析（5段階評価）
- 3パターンのX投稿文生成（効果重視・課題共感・学習促進）
- Claude API使用量記録
- 詳細なコスト・トークン使用量記録
- Markdownファイルへの自動保存

使用方法:
    export ANTHROPIC_API_KEY="your-api-key"
    export HTML_FILE="path/to/html/file.html"
    export FILENAME="posts/output.md"
    python claude_api_x_post_generator.py

ファイル依存関係:
    - prompts/system_prompt.md: システムプロンプト定義
    - HTML_FILEで指定されたHTMLファイル

Author: Claude API X Posts Generator
Version: 1.0.0
License: MIT
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from anthropic import Anthropic
except ImportError:
    print("❌ anthropic パッケージがインストールされていません")
    print("pip install anthropic でインストールしてください")
    exit(1)


class ClaudeAPIXPostGenerator:
    """
    Claude APIを使用したX投稿生成クラス
    """

    def __init__(self):
        """
        初期化処理
        """
        # 環境変数の取得
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY環境変数が設定されていません")

        self.debug_mode = os.environ.get("DEBUG_MODE", "false").lower() == "true"
        self.html_file_path = os.environ.get("HTML_FILE")

        # Claude APIクライアントの初期化
        self.client = Anthropic(api_key=self.api_key)

        # 使用するモデル
        self.model = "claude-3-5-sonnet-20241022"

        # 料金設定（2025年7月時点の公式料金）
        self.pricing = {
            "input_per_million": 3.00,
            "output_per_million": 15.00,
            "cache_write_per_million": 3.75,
            "cache_read_per_million": 0.30,
        }

        # デバッグ情報の出力
        if self.debug_mode:
            print("🐛 デバッグモード: 有効")
            print("🔑 APIキー設定: 設定済み")
            print(f"📄 HTMLファイルパス: {self.html_file_path or '未指定'}")
            print(f"🤖 使用モデル: {self.model}")

        # HTMLファイルコンテンツの読み込み
        if not self.html_file_path:
            raise ValueError("HTML_FILE環境変数が設定されていません")

        try:
            self.html_content = self._load_html_content()
            print("✅ HTMLファイル読み込み完了")
        except Exception as e:
            print(f"❌ HTMLファイル読み込みエラー: {e}")
            raise

        # システムプロンプトの読み込み
        try:
            self.system_prompt_content = self._load_system_prompt_from_file()
            print("✅ システムプロンプト読み込み完了")
        except Exception as e:
            print(f"❌ システムプロンプト読み込みエラー: {e}")
            raise

    def _load_html_content(self) -> str:
        """HTMLファイルからコンテンツを読み込み"""
        html_file_path = Path(self.html_file_path)
        print(f"📄 HTMLファイル読み込み: {html_file_path}")

        if not html_file_path.exists():
            raise FileNotFoundError(f"HTMLファイルが見つかりません: {html_file_path}")

        try:
            with open(html_file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                raise ValueError(f"HTMLファイルが空です: {html_file_path}")

            file_size = len(content.encode("utf-8"))
            line_count = len(content.splitlines())

            print("📊 HTMLコンテンツ情報:")
            print(f"   - ファイルサイズ: {file_size:,} bytes")
            print(f"   - 行数: {line_count:,} 行")
            print(f"   - 文字数: {len(content):,} 文字")

            return content

        except Exception as e:
            raise ValueError(f"HTMLファイル読み込みエラー: {e}")

    def _load_system_prompt_from_file(self) -> str:
        """外部ファイルからシステムプロンプトを読み込み"""
        prompt_file_path = Path("prompts/system_prompt.md")
        print(f"📁 システムプロンプト読み込み: {prompt_file_path}")

        if not prompt_file_path.exists():
            raise FileNotFoundError(f"システムプロンプトファイルが見つかりません: {prompt_file_path}")

        try:
            with open(prompt_file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

            if not content:
                raise ValueError(f"システムプロンプトファイルが空です: {prompt_file_path}")

            file_size = len(content.encode("utf-8"))
            line_count = len(content.splitlines())

            print("📊 システムプロンプト情報:")
            print(f"   - ファイルサイズ: {file_size:,} bytes")
            print(f"   - 行数: {line_count:,} 行")
            print(f"   - 文字数: {len(content):,} 文字")

            return content

        except Exception as e:
            raise ValueError(f"システムプロンプト読み込みエラー: {e}")

    def generate_posts_from_html(self) -> Dict[str, Any]:
        """
        HTMLファイルからX投稿パターンを生成
        """
        print("🚀 X投稿パターン生成開始...")
        print("=" * 60)

        # 生成設定の表示
        print(f"📄 HTMLファイル: {self.html_file_path}")
        print(f"🤖 使用モデル: {self.model}")
        print(f"🔧 デバッグモード: {'有効' if self.debug_mode else '無効'}")

        # 開始時刻の記録
        start_time = time.time()

        try:
            # Claude APIコール
            result = self._call_claude_api()

            # 処理時間の計算
            processing_time = time.time() - start_time
            result["processing_time_seconds"] = processing_time

            # コスト・トークン使用量の詳細出力
            self._print_usage_details(result)

            return result

        except Exception as e:
            error_msg = f"生成処理中にエラーが発生しました: {e}"
            print(f"❌ {error_msg}")
            return {
                "content": None,
                "error": str(e),
                "error_type": type(e).__name__,
                "processing_time_seconds": time.time() - start_time,
            }

    def _call_claude_api(self) -> Dict[str, Any]:
        """Claude APIを呼び出し"""
        print("🔄 Claude API呼び出し開始...")

        # プロンプトの構成
        user_prompt = f"""
        以下のHTMLコンテンツを分析して、技術記事のX投稿パターンを生成してください：

        <html_content>
        {self.html_content}
        </html_content>

        上記のHTMLコンテンツを分析し、システムプロンプトに従って3パターンのX投稿文を生成してください。
        """

        try:
            # プロンプトキャッシュを使用してAPIコール
            if self.cache_enabled:
                print("📦 プロンプトキャッシュを使用してAPIコール...")
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    system=[
                        {
                            "type": "text",
                            "text": self.system_prompt_content,
                            "cache_control": {"type": "ephemeral"}
                        }
                    ],
                    messages=[
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ]
                )
            else:
                print("🚫 プロンプトキャッシュを使用しないAPIコール...")
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4000,
                    system=self.system_prompt_content,
                    messages=[
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ]
                )

            # レスポンスの処理
            content = response.content[0].text
            metadata = self._extract_metadata(response)

            print("✅ Claude API呼び出し完了")

            return {
                "content": content,
                "metadata": metadata,
                "success": True,
                "api_call_real": True,
                "cache_used": self.cache_enabled,
            }

        except Exception as e:
            print(f"❌ Claude API呼び出しエラー: {e}")
            raise

    def _extract_metadata(self, response) -> Dict[str, Any]:
        """レスポンスからメタデータを抽出"""
        metadata = {
            "response_id": response.id,
            "model": response.model,
            "stop_reason": response.stop_reason,
            "stop_sequence": response.stop_sequence,
            "usage": {},
            "costs": {}
        }

        # 使用量情報の抽出
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            usage_data = {
                "input_tokens": getattr(usage, 'input_tokens', 0),
                "output_tokens": getattr(usage, 'output_tokens', 0),
                "cache_creation_input_tokens": getattr(usage, 'cache_creation_input_tokens', 0),
                "cache_read_input_tokens": getattr(usage, 'cache_read_input_tokens', 0),
            }
            metadata["usage"] = usage_data

            # 料金計算
            costs = self._calculate_costs(usage_data)
            metadata["costs"] = costs

        return metadata

    def _calculate_costs(self, usage: Dict[str, int]) -> Dict[str, float]:
        """料金計算"""
        # 基本コスト計算
        if self.cache_enabled:
            # プロンプトキャッシュ使用時のコスト計算
            cache_cost = usage["cache_read_input_tokens"] * \
                self.pricing["cache_read_per_million"] / 1000000
            cache_write_cost = usage["cache_creation_input_tokens"] * \
                self.pricing["cache_write_per_million"] / 1000000
            input_cost = usage["input_tokens"] * \
                self.pricing["input_per_million"] / 1000000
        else:
            # プロンプトキャッシュ未使用時のコスト計算
            cache_cost = 0
            cache_write_cost = 0
            total_input_tokens = (
                usage["input_tokens"] +
                usage["cache_creation_input_tokens"] +
                usage["cache_read_input_tokens"]
            )
            input_cost = total_input_tokens * \
                self.pricing["input_per_million"] / 1000000

        # 出力トークンのコスト（プロンプトキャッシュ使用有無に関わらず同じ）
        output_cost = usage["output_tokens"] * \
            self.pricing["output_per_million"] / 1000000

        # 総コスト
        total_cost = cache_cost + cache_write_cost + input_cost + output_cost

        # 削減効果の計算（キャッシュなしとの比較）
        total_input_tokens_without_cache = (
            usage["input_tokens"] +
            usage["cache_creation_input_tokens"] +
            usage["cache_read_input_tokens"]
        )
        cost_without_cache = (
            total_input_tokens_without_cache *
            self.pricing["input_per_million"] / 1000000
            + output_cost
        )
        cost_reduction = cost_without_cache - total_cost if self.cache_enabled else 0
        cost_reduction_percent = (
            (cost_reduction / cost_without_cache * 100) if cost_without_cache > 0 else 0
        )

        # 月間・年間での削減効果試算（月50回実行想定）
        monthly_savings = cost_reduction * 50  # 月50回実行
        yearly_savings = monthly_savings * 12  # 年間

        return {
            # 基本コスト情報（USD）
            "cache_cost": cache_cost,
            "cache_write_cost": cache_write_cost,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            # 円換算（1USD=150JPY想定）
            "total_cost_jpy": total_cost * 150,
            # 削減効果
            "cost_without_cache": cost_without_cache,
            "cost_reduction": cost_reduction,
            "cost_reduction_percent": cost_reduction_percent,
            # 長期的な削減効果
            "monthly_savings_usd": monthly_savings,
            "yearly_savings_usd": yearly_savings,
            "monthly_savings_jpy": monthly_savings * 150,
            "yearly_savings_jpy": yearly_savings * 150,
        }

    def _print_usage_details(self, result: Dict[str, Any]):
        """使用量の詳細を出力"""
        if not result.get("success") or "metadata" not in result:
            return

        metadata = result["metadata"]
        usage = metadata.get("usage", {})
        costs = metadata.get("costs", {})

        print("\n💰 コスト詳細レポート:")
        print(f"   - キャッシュ読み取り: ${costs.get('cache_cost', 0):.6f}")
        print(f"   - キャッシュ書き込み: ${costs.get('cache_write_cost', 0):.6f}")
        print(f"   - 入力処理: ${costs.get('input_cost', 0):.6f}")
        print(f"   - 出力生成: ${costs.get('output_cost', 0):.6f}")
        print(
            f"   - 合計: ${costs.get('total_cost', 0):.6f} (約{costs.get('total_cost_jpy', 0):.1f}円)")

        if self.cache_enabled:
            print("\n📊 コスト削減効果:")
            print(f"   - キャッシュなしの場合: ${costs.get('cost_without_cache', 0):.6f}")
            print(f"   - 削減金額: ${costs.get('cost_reduction', 0):.6f}")
            print(f"   - 削減率: {costs.get('cost_reduction_percent', 0):.1f}%")
            print(
                f"   - 月間削減効果: ${costs.get('monthly_savings_usd', 0):.2f} (約{costs.get('monthly_savings_jpy', 0):.0f}円)")
            print(
                f"   - 年間削減効果: ${costs.get('yearly_savings_usd', 0):.2f} (約{costs.get('yearly_savings_jpy', 0):.0f}円)")

        print("\n📊 トークン使用量詳細:")
        print(f"   - キャッシュ済み: {usage.get('cache_read_input_tokens', 0):,}")
        print(f"   - キャッシュ作成: {usage.get('cache_creation_input_tokens', 0):,}")
        print(f"   - 入力トークン: {usage.get('input_tokens', 0):,}")
        print(f"   - 出力トークン: {usage.get('output_tokens', 0):,}")
        total_input = (
            usage.get('input_tokens', 0) +
            usage.get('cache_creation_input_tokens', 0) +
            usage.get('cache_read_input_tokens', 0)
        )
        print(f"   - 総入力: {total_input:,}")

        # プロンプトキャッシュ効率の表示
        if self.cache_enabled and usage.get('cache_read_input_tokens', 0) > 0:
            cache_efficiency = (
                usage.get('cache_read_input_tokens', 0) /
                self.estimated_cache_tokens * 100
            )
            print(f"   - キャッシュ効率: {cache_efficiency:.1f}%")

        # 処理パフォーマンス情報
        processing_time = result.get("processing_time_seconds", 0)
        total_tokens = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)

        print("\n⏱️  処理パフォーマンス:")
        print(f"   - 処理時間: {processing_time:.2f}秒")
        if processing_time > 0:
            print(f"   - トークン/秒: {total_tokens / processing_time:.0f}")

    def save_to_file(
        self,
        content: str,
        filename: str,
        html_file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """生成されたコンテンツをMarkdownファイルとして保存"""
        if not content:
            raise ValueError("保存するコンテンツが空です")
        if not filename:
            raise ValueError("ファイル名が指定されていません")
        if not html_file_path:
            raise ValueError("HTMLファイルパスが指定されていません")

        print(f"💾 ファイル保存開始: {filename}")

        # ディレクトリ作成
        file_path = Path(filename)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # メタデータの準備
        if metadata is None:
            metadata = {}

        usage = metadata.get("usage", {})
        costs = metadata.get("costs", {})

        # YAML Frontmatterの生成
        frontmatter = f"""
<!--
---
# =================================================================
# Claude API X投稿自動生成システム - 生成ファイルメタデータ
# =================================================================

# 生成基本情報
html_file: "{html_file_path}"
generated_at: "{datetime.now().isoformat()}"
generator: "Claude API X Posts Generator"
generator_version: "v1.0.0"
system_prompt_source: "prompts/system_prompt.md"

# Claude API情報
api_info:
  model: "{metadata.get('model', 'unknown')}"
  response_id: "{metadata.get('response_id', 'unknown')}"
  stop_reason: "{metadata.get('stop_reason', 'unknown')}"
  api_call_real: true

# プロンプトキャッシュ情報
prompt_cache:
  enabled: {str(self.cache_enabled).lower()}
  cached_tokens: {usage.get('cache_read_input_tokens', 0)}
  estimated_cache_size: {self.estimated_cache_tokens}
  cache_efficiency: {(
      usage.get('cache_read_input_tokens', 0) /
      self.estimated_cache_tokens * 100
      if self.estimated_cache_tokens > 0 else 0
  ):.1f}%

# コスト情報（USD）
costs_usd:
  cache_cost: {costs.get('cache_cost', 0):.6f}
  cache_write_cost: {costs.get('cache_write_cost', 0):.6f}
  input_cost: {costs.get('input_cost', 0):.6f}
  output_cost: {costs.get('output_cost', 0):.6f}
  total_cost: {costs.get('total_cost', 0):.6f}
  cost_without_cache: {costs.get('cost_without_cache', 0):.6f}
  cost_reduction: {costs.get('cost_reduction', 0):.6f}

# コスト情報（JPY、1USD=150JPY想定）
costs_jpy:
  total_cost: {costs.get('total_cost_jpy', 0):.1f}
  cost_reduction: {costs.get('cost_reduction', 0) * 150:.1f}
  monthly_savings: {costs.get('monthly_savings_jpy', 0):.0f}
  yearly_savings: {costs.get('yearly_savings_jpy', 0):.0f}

# コスト削減効果
cost_efficiency:
  reduction_percent: {costs.get('cost_reduction_percent', 0):.1f}%
  monthly_usage_assumption: 50  # 月間実行回数想定
  yearly_usage_assumption: 600  # 年間実行回数想定

# トークン使用量詳細
token_usage:
  input:
    cached: {usage.get('cache_read_input_tokens', 0)}
    cache_creation: {usage.get('cache_creation_input_tokens', 0)}
    regular: {usage.get('input_tokens', 0)}
    total: {usage.get('input_tokens', 0) + usage.get('cache_creation_input_tokens', 0) + usage.get('cache_read_input_tokens', 0)}
  output: {usage.get('output_tokens', 0)}
  processing_efficiency: {(
      usage.get('output_tokens', 0) /
      max(usage.get('input_tokens', 0) + usage.get('cache_creation_input_tokens', 0) + usage.get('cache_read_input_tokens', 0), 1)
  ):.4f}  # 出力/入力比率

# Claude API料金設定
pricing_info:
  input_per_million: {self.pricing['input_per_million']}
  output_per_million: {self.pricing['output_per_million']}
  cache_write_per_million: {self.pricing['cache_write_per_million']}
  cache_read_per_million: {self.pricing['cache_read_per_million']}
  pricing_date: "2025-07-15"

# 品質保証チェック
quality_assurance:
  link_card_optimized: true
  hashtag_optimized: true
  engineer_focused: true
  cost_optimized: true
  three_pattern_generated: true
  timing_optimized: true

# システム情報
system_info:
  debug_mode: {str(self.debug_mode).lower()}
  html_file_path: "{html_file_path}"
  content_language: "ja"
  target_platform: "X (Twitter)"
  target_audience: "Japanese Engineers"

# 更新履歴
revision_history:
  - version: "1.0.0"
    date: "{datetime.now().strftime('%Y-%m-%d')}"
    changes: "初回生成（Claude API使用）"
---
-->

"""

        # コンテンツとメタデータを結合
        full_content = frontmatter + content

        try:
            # ファイルに書き込み
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_content)

            # 保存完了レポート
            file_size = len(full_content.encode("utf-8"))
            content_lines = len(content.splitlines())
            total_lines = len(full_content.splitlines())

            print("✅ ファイル保存完了!")
            print(f"📁 保存先: {file_path.absolute()}")
            print("📊 ファイル統計:")
            print(f"   - ファイルサイズ: {file_size:,} bytes")
            print(f"   - 総行数: {total_lines:,} 行")
            print(f"   - コンテンツ行数: {content_lines:,} 行")
            print(f"   - 文字数: {len(full_content):,} 文字")

        except Exception as e:
            error_msg = f"ファイル保存エラー: {e}"
            print(f"❌ {error_msg}")
            raise OSError(error_msg)


def main():
    """メイン実行関数"""
    print("🤖 Claude API X投稿自動生成システム")
    print("=" * 70)
    print("📅 Version: 1.0.0")
    print("🔧 Mode: Claude API使用")
    print("💡 Feature: プロンプトキャッシュによるコスト削減")

    # 実行開始時刻の記録
    execution_start_time = time.time()

    try:
        # 環境変数からパラメータ取得
        html_file = os.environ.get("HTML_FILE")
        filename = os.environ.get("FILENAME")
        debug_mode = os.environ.get("DEBUG_MODE", "false").lower() == "true"

        # HTML_FILE必須チェック
        if not html_file:
            print("❌ HTML_FILE環境変数が設定されていません")
            return 1

        # ファイル名が未指定の場合はデフォルト生成
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"posts/claude-api-output-{timestamp}.md"
            print(f"⚠️  ファイル名未指定のため、デフォルト名を使用: {filename}")

        print("\n📋 実行パラメータ:")
        print(f"   - HTMLファイル: {html_file}")
        print(f"   - 出力ファイル: {filename}")
        print(f"   - デバッグモード: {'有効' if debug_mode else '無効'}")
        print(f"   - 作業ディレクトリ: {os.getcwd()}")

        # 生成システムの初期化
        print("\n🔄 システム初期化中...")
        try:
            generator = ClaudeAPIXPostGenerator()
            print("✅ システム初期化完了")
        except Exception as e:
            print(f"❌ システム初期化エラー: {e}")
            return 1

        # X投稿パターン生成
        print("\n🚀 生成処理開始...")
        result = generator.generate_posts_from_html()

        # エラーチェック
        if not result.get("success"):
            print(f"❌ 生成エラー: {result.get('error', 'Unknown error')}")
            return 1

        # ファイル保存
        print("\n💾 ファイル保存処理...")
        generator.save_to_file(
            result["content"],
            filename,
            html_file,
            result.get("metadata", {})
        )

        # 実行完了レポート
        total_execution_time = time.time() - execution_start_time
        metadata = result.get("metadata", {})
        costs = metadata.get("costs", {})

        print("\n🎉 全処理完了!")
        print(f"⏱️  総実行時間: {total_execution_time:.2f}秒")
        print(f"📁 出力ファイル: {filename}")
        print(
            f"💰 実際のコスト: ${costs.get('total_cost', 0):.6f} (約{costs.get('total_cost_jpy', 0):.1f}円)")

        if result.get("cache_used"):
            print(
                f"📊 コスト削減: {costs.get('cost_reduction_percent', 0):.1f}% (${costs.get('cost_reduction', 0):.6f})")

        print("\n✅ 処理が正常に完了しました!")
        return 0

    except KeyboardInterrupt:
        print("\n⚠️  ユーザーによる処理中断")
        return 130

    except Exception as e:
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        print(f"🔍 エラータイプ: {type(e).__name__}")

        if os.environ.get("DEBUG_MODE", "false").lower() == "true":
            import traceback
            print("\n🐛 詳細なエラー情報:")
            traceback.print_exc()

        return 99


if __name__ == "__main__":
    """
    スクリプトのエントリーポイント
    """
    try:
        exit_code = main()
        print(f"\n🏁 プロセス終了 (exit code: {exit_code})")
        exit(exit_code)
    except Exception as e:
        print(f"\n💥 致命的エラー: {e}")
        exit(99)

# =================================================================
# スクリプト実行時の注意事項とトラブルシューティング
# =================================================================

"""
【必要な環境設定】

1. パッケージのインストール:
   pip install anthropic

2. 依存ファイル:
   - prompts/system_prompt.md: システムプロンプト定義ファイル
   - html_cache/*.html: 分析対象のHTMLファイル

3. 環境変数:
   - ANTHROPIC_API_KEY: Claude APIキー（必須）
   - HTML_FILE: 分析対象のHTMLファイルパス（必須）
   - FILENAME: 出力ファイルパス（オプション、デフォルト自動生成）
   - DEBUG_MODE: デバッグモード（"true"で詳細ログ出力）

4. ディレクトリ構造:
   project/
   ├── claude_api_x_post_generator.py  # このファイル
   ├── prompts/
   │   └── system_prompt.md           # システムプロンプト
   ├── html_cache/                    # HTMLファイル保存先
   └── posts/                         # 出力先（自動作成）

【ローカルでのテスト実行】

# 1. APIキーの設定
export ANTHROPIC_API_KEY="your-api-key-here"

# 2. 基本実行
export HTML_FILE="html_cache/sample.html"
export FILENAME="posts/test-output.md"
python claude_api_x_post_generator.py

# 3. デバッグモード
export DEBUG_MODE="true"
python claude_api_x_post_generator.py

【トラブルシューティング】

1. "ANTHROPIC_API_KEY環境変数が設定されていません"
   → Claude APIキーを取得して環境変数に設定してください

2. "HTML_FILE環境変数が設定されていません"
   → 分析対象のHTMLファイルパスを指定してください

3. "HTMLファイルが見つかりません"
   → HTML_FILEパスが正しいか確認してください

4. "システムプロンプトファイルが見つかりません"
   → prompts/system_prompt.md を作成してください

5. "anthropic パッケージがインストールされていません"
   → pip install anthropic を実行してください

6. "Claude API呼び出しエラー"
   → APIキーの有効性、レート制限、アカウント残高を確認してください

【パフォーマンス・コスト最適化】

- プロンプトキャッシュ: システムプロンプトをキャッシュして2回目以降のコスト削減
- 処理時間: 実際のAPI通信時間（通常10-30秒）
- コスト: 入力/出力トークン数により変動（通常$0.01-0.10程度）

【セキュリティ注意事項】

- APIキーは環境変数で管理し、コードに直接記載しない
- 生成されたファイルには機密情報が含まれていないか確認
- HTMLファイルの内容は信頼できるソースからのみ取得する
"""
